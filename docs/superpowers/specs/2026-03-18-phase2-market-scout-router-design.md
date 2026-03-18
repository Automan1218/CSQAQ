# Phase 2 设计：Market Agent + Scout Agent + Router + Main Graph

**日期**: 2026-03-18
**范围**: Market Agent、Scout Agent、Router、Router Flow（主图）、Market Flow、Scout Flow
**前置**: Phase 1 已完成（Item Agent + Advisor + Infrastructure）

## 决策记录

| 问题 | 决策 | 理由 |
|------|------|------|
| Market Agent 数据深度 | 标准（首页+指数详情） | K线技术分析后续再加，先跑通核心 |
| Scout Agent 维度 | 涨跌幅+成交量+在售数量变化 | 量价配合是投资核心，其余为进阶 |
| Router 实现 | 关键词+LLM兜底 | 大部分查询可秒分类，边缘情况交LLM |
| Main Graph 编排 | 串行（A方案） | 先跑通，并行列入TODO |
| 整体架构 | 沿用Phase1四层+方案A | 改动最小，结构一致 |
| Advisor 集成方式 | 统一嵌入子 flow 内部 | 见下文"Advisor 集成模式"说明 |

## 架构：4 层不变

```
API 层 (cli.py)
  → Flows 层 (router_flow → market_flow / scout_flow / item_flow)
    → Components 层 (router, market_agent, scout_agent, item_agent, advisor)
      → Infrastructure 层 (CSQAQClient, MarketAPI, RankAPI, ItemAPI, indicators, DB)
```

## 端到端示例

```
用户输入: "今天大盘怎么样"
  → cli.py chat() → run_query(app, "今天大盘怎么样")
    → router_flow.ainvoke({query: "今天大盘怎么样", ...})
      → router_node: 关键词匹配 "大盘" → intent="market_query"
      → 条件边 → market_subflow
        → fetch_market_data: MarketAPI.get_home_data() + get_sub_data()
        → analyze_market: LLM 分析 → market_context
        → advisor_node: 基于 market_context 生成建议
      → result = "📊 分析: ...\n💡 建议: ..."
    → CLI 展示 Panel
```

## 1. Infrastructure 层 — 新增

### MarketAPI (`infrastructure/csqaq_client/market.py`)

| 方法 | API路径 | 说明 |
|------|---------|------|
| `get_home_data()` | POST (路径待确认) | 首页指数数据 |
| `get_sub_data(sub_id)` | POST (路径待确认) | 指数详情 |

> **注意**: API 路径需要通过实际调用确认。CSQAQ 文档使用客户端渲染无法爬取，实现时第一步先用真实 token 探测端点路径和响应格式。参考已有 ItemAPI 路径模式（`/info/good`、`/info/chart`）。

### RankAPI (`infrastructure/csqaq_client/rank.py`)

| 方法 | API路径 | 说明 |
|------|---------|------|
| `get_rank_list(rank_type, period, page, size)` | POST (路径待确认) | 排行榜 |
| `get_page_list(filters, page, size)` | POST (路径待确认) | 饰品列表筛选 |

> rank_type 枚举值和 period 格式需实际调用确认后定义为常量。

### 新增 Schemas

Schema 字段需通过实际 API 调用确认后定义。预期结构：

**IndexData**:
```python
class IndexData(BaseModel):
    index_value: float          # 当前指数值
    index_change: float         # 涨跌幅 (%)
    rise_count: int             # 上涨家数
    fall_count: int             # 下跌家数
    flat_count: int             # 持平家数
    online_count: int | None    # 在线人数
    # ... 实际字段以 API 响应为准，使用 Field(alias=...) 映射驼峰命名
```

**SubIndexDetail**:
```python
class SubIndexDetail(BaseModel):
    sub_id: str
    name: str                   # 指数名称
    today_change: float         # 今日涨跌
    chart_points: list[dict]    # 图表数据点
```

**RankItem**:
```python
class RankItem(BaseModel):
    good_id: int
    good_name: str
    image_url: str
    rank_value: float           # 排行指标值（涨跌幅/成交量/在售数量）
    change_rate: float          # 变化率 (%)
```

**PageListItem**:
```python
class PageListItem(BaseModel):
    good_id: int
    good_name: str
    buff_sell_price: float
    daily_change_rate: float
    volume: int
    sell_num: int
```

## 2. Components 层 — 新增

### Router (`components/router.py`)

```
用户查询 → 关键词匹配 → 命中? → IntentResult
                          ↓ 未命中
                     LLM(GPT-4o-mini) → IntentResult
```

**IntentResult** (定义在 `components/router.py` 中的 dataclass):
```python
@dataclass
class IntentResult:
    intent: str         # "item_query" | "market_query" | "scout_query"
    confidence: float   # 关键词匹配=1.0, LLM兜底固定=0.8
    item_name: str | None  # 仅 item_query 时提取
```

**关键词规则表 + 优先级**:
1. `market_query`: 大盘、指数、行情、市场、涨跌分布（优先级最高）
2. `scout_query`: 排行、推荐、值得买、机会、捡漏、热门
3. `item_query`: 默认兜底
- 多关键词冲突时，按上述优先级判定（market > scout > item）
- item_name 提取方式：去掉匹配到的关键词后，剩余文本作为饰品名传给 search_suggest

**LLM 兜底 prompt**:
```
system: 你是一个查询意图分类器。将用户查询分为三类:
- item_query: 询问某个具体饰品的价格、走势、是否值得入手
- market_query: 询问大盘、市场整体行情、指数
- scout_query: 询问推荐、排行、值得关注的饰品

输出严格 JSON: {"intent": "...", "item_name": "饰品名或null"}

user: {query}
```

### Market Agent (`components/agents/market.py`)

- 调用 MarketAPI 获取首页数据 + 指数详情
- LLM (analyst) 分析大盘方向
- 输出: `market_context`（方向判断 + 关键数据摘要）

### Scout Agent (`components/agents/scout.py`)

- 调用 RankAPI 获取 3 维度排行（涨跌幅 top20、成交量 top20、在售数量变化 top20）
- **交叉筛选算法**：
  1. 取三个排行各 top 20 的 good_id
  2. 统计每个 good_id 出现次数
  3. 出现 ≥2 次 = 高关注度（量价/量售配合）
  4. 按出现次数降序排列，取 top 10
  5. 如果交叉结果不足 5 个，补充涨跌幅 top 的剩余饰品
- LLM (analyst) 对筛选结果做总结
- 输出: `scout_context`（推荐列表 + 理由）

## 3. Flows 层 — 新增

### Advisor 集成模式（Phase 2 变更）

Phase 1 中 Item Flow 和 Advisor Flow 是两个独立的 compiled graph，在 `run_item_query` 中顺序调用。

**Phase 2 改为**：Advisor 节点统一嵌入每个子 flow 内部。原因：
1. Router Flow 作为主图，子 flow 需要自包含（输入 query，输出 result）
2. 避免 Router Flow 还需要根据 intent 决定如何组装 Advisor 参数
3. 每个子 flow 的 Advisor 接收的 context 字段不同（item_context vs market_context vs scout_context）

**Item Flow 需配合重构**：在末尾增加 advisor_node，使其也自包含输出 result。

### Router Flow (`flows/router_flow.py`) — 主入口图

```
START → router_node → 条件边
  ├─ "item_query"   → item_subflow → END
  ├─ "market_query" → market_subflow → END
  └─ "scout_query"  → scout_subflow → END
```

**RouterFlowState (TypedDict)**:
```python
class RouterFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str                    # 用户原始查询
    intent: str | None            # 路由结果
    item_name: str | None         # 提取的饰品名（item_query 用）
    result: str | None            # 最终格式化输出
    error: str | None
```

每个子 flow 是独立节点函数，内部构建并调用对应的 compiled graph，将结果写入 `result`。

### Market Flow (`flows/market_flow.py`)

```
START → fetch_market_data → analyze_market → advisor_node → format_result → END
```

**MarketFlowState (TypedDict)**:
```python
class MarketFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str                    # 用户原始查询（从 Router 传入）
    home_data: dict | None        # 首页指数数据
    sub_data: dict | None         # 指数详情
    market_context: str | None    # LLM 分析结果
    recommendation: str | None    # Advisor 建议
    risk_level: str | None
    error: str | None
```

### Scout Flow (`flows/scout_flow.py`)

```
START → fetch_rank_data → analyze_opportunities → advisor_node → format_result → END
```

**ScoutFlowState (TypedDict)**:
```python
class ScoutFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str                    # 用户原始查询（从 Router 传入）
    rank_data: dict | None        # 三维度排行原始数据
    scout_context: str | None     # 交叉筛选 + LLM 总结
    recommendation: str | None    # Advisor 建议
    risk_level: str | None
    error: str | None
```

### Item Flow — 需小幅重构

在现有 `resolve_item → fetch_chart → analyze` 之后增加 `advisor_node → format_result`，使其自包含输出 result。

## 4. 入口改动

### main.py

`run_item_query` → `run_query`:
```python
async def run_query(app: App, query: str) -> str:
    """Run a query through the router flow."""
    router_flow = build_router_flow(
        item_api=app.item_api,
        market_api=app.market_api,
        rank_api=app.rank_api,
        model_factory=app.model_factory,
    )
    result = await router_flow.ainvoke({
        "messages": [],
        "query": query,
        "intent": None,
        "item_name": None,
        "result": None,
        "error": None,
    })
    return result.get("result") or f"查询失败: {result.get('error', '未知错误')}"
```

`App.init()` 新增:
- `self._market_api = MarketAPI(self._csqaq_client)`
- `self._rank_api = RankAPI(self._csqaq_client)`
- 对应 property + runtime guard

### cli.py

- `chat()` 和 `_single_query` / `_interactive_mode` 调用 `run_query` 替换 `run_item_query`

## 5. 测试策略

### 单元测试

- `tests/test_infrastructure/test_market_endpoints.py` — MarketAPI mock 测试（参考 test_item_endpoints.py）
- `tests/test_infrastructure/test_rank_endpoints.py` — RankAPI mock 测试
- `tests/test_components/test_router.py` — 关键词匹配测试（各种查询→正确 intent）

### Flow 测试

- `tests/test_flows/test_market_flow.py` — Market Flow 全链路 mock 测试
- `tests/test_flows/test_scout_flow.py` — Scout Flow 全链路 mock 测试
- `tests/test_flows/test_router_flow.py` — Router 分发 + 子 flow mock 测试

### E2E 测试

- 更新 `tests/test_e2e.py`，增加 market_query 和 scout_query 路径测试

## 6. 错误处理

- API 失败 → 节点返回 `{error: ...}` → 条件边跳过 → Advisor 输出 "数据不足"
- LLM 失败 → 节点 catch → 写入 error
- Router 分类失败 → 默认走 `item_query` 兜底

## 7. 不在范围

- 并行子图执行 → TODO
- K线技术分析增强 → TODO
- HITL 高风险确认 → Phase 3
- 记忆系统 → Phase 3
- Server mode → Phase 4
