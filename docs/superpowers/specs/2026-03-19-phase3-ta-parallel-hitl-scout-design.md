# Phase 3 Design: 技术分析 · 并行子图 · HITL · Scout 全维度

## 概述

Phase 3 在 Phase 2（Market/Scout/Router）基础上，引入股市技术分析方法论，增强分析深度和用户体验。

CS2 饰品市场本质上是一个简化版金融市场（有 K 线、成交量、涨跌幅、贪婪指数），股市中的 MA、MACD、RSI、布林带等技术分析方法完全适用。

### 功能清单

| # | 功能 | 说明 |
|---|------|------|
| 1 | K 线技术分析增强 | 单品 + 大盘指数 K 线，输出结构化指标 + 信号标签 + 文字总结 |
| 2 | 并行子图执行 | 单品查询时同时并行拉取大盘 + Scout 上下文 |
| 3 | HITL 高风险确认 | risk_level=high 时分段输出，用户确认后才给操作建议 |
| 4 | Scout 全维度扫描 | 新增存世量、在售/求购数量、总市值排行维度 |

### 架构方案

**方案 B：技术分析独立模块**。把技术分析抽成独立的 `components/analysis/` 模块，和 agents 平级。不重写现有 flow，在已有架构上扩展。

---

## 1. 技术分析模块

### 1.1 模块结构

```
src/csqaq/components/analysis/
├── __init__.py
├── indicators.py    # 纯数值计算（从 infrastructure/analysis/ 迁移 + 扩展）
├── signals.py       # 信号生成器：指标 → 信号标签
└── analyzer.py      # 组合入口：raw data → TA 报告
```

### 1.2 indicators.py — 技术指标

从 `infrastructure/analysis/indicators.py` 迁移已有方法，并新增：

| 指标 | 方法 | 参数 | 返回值 |
|------|------|------|--------|
| SMA | `moving_average()` | prices, window | `list[float\|None]` |
| EMA | `exponential_moving_average()` | prices, window, smoothing=2 | `list[float\|None]` |
| RSI | `rsi()` | prices, period=14 | `float` (0-100) |
| MACD | `macd()` | prices, fast=12, slow=26, signal=9 | `MACDResult(macd_line, signal_line, histogram)` |
| 布林带 | `bollinger_bands()` | prices, window=20, num_std=2 | `BollingerResult(upper, middle, lower)` |
| 波动率 | `volatility()` | prices, window | `float` |
| 动量 | `price_momentum()` | prices, period | `float` |
| 平台价差 | `platform_spread()` | price_a, price_b | `float` |
| 量价趋势 | `volume_trend()` | volumes, window | `str` |

所有方法均为 `@staticmethod`，纯函数，无副作用。

**迁移计划**：`infrastructure/analysis/indicators.py` 的现有 5 个方法（`moving_average`、`volatility`、`price_momentum`、`platform_spread`、`volume_trend`）迁移到新模块，原位置改为 re-export（`from csqaq.components.analysis.indicators import TechnicalIndicators`）保持向后兼容。

### 1.3 signals.py — 信号生成

```python
@dataclass
class Signal:
    name: str           # e.g. "ma_crossover"
    direction: str      # "bullish" | "bearish" | "neutral"
    strength: float     # 0.0 ~ 1.0
    description: str    # "MA5 上穿 MA20，短期看多"
```

信号检测函数：

| 信号 | 函数 | 触发条件 |
|------|------|----------|
| MA 交叉 | `detect_ma_crossover(prices, short=5, long=20)` | MA5 上穿/下穿 MA20 |
| RSI 极端 | `detect_rsi_extreme(prices, period=14)` | RSI > 70 超买 / RSI < 30 超卖 |
| MACD 交叉 | `detect_macd_crossover(prices)` | MACD 线上穿/下穿信号线 |
| 布林突破 | `detect_bollinger_breakout(prices)` | 价格突破上轨/下轨 |
| 量价背离 | `detect_volume_price_divergence(prices, volumes)` | 价格涨但量跌 / 价格跌但量涨 |

每个函数返回 `Signal | None`（无信号时返回 None）。

### 1.4 analyzer.py — TA 报告

```python
@dataclass
class TAReport:
    signals: list[Signal]           # 所有检测到的信号
    indicators: dict                # 原始指标数值 {ma5, ma20, rsi, macd, bollinger...}
    overall_direction: str          # "bullish" | "bearish" | "neutral"
    summary: str                    # 一句话中文总结
```

入口函数：

- `analyze_kline(bars: list[KlineBar]) -> TAReport` — 单品 K 线分析
- `analyze_index_kline(bars: list[IndexKlineBar]) -> TAReport` — 大盘指数 K 线分析

**综合方向**：加权信号投票。每个 Signal 的 `strength` 作为投票权重，`sum(bullish strengths)` vs `sum(bearish strengths)`，差距 < 0.1 为 neutral。

**最小数据要求**：如果输入 `bars` 不足以计算某个指标（如 MACD 需要至少 35 根 K 线），该信号检测函数返回 None（跳过），`TAReport.summary` 中注明"数据不足，部分指标未生效"。各指标最小数据量：

| 指标 | 最小 K 线数 |
|------|------------|
| MA5/MA20 | 20 |
| RSI(14) | 15 |
| MACD(12,26,9) | 35 |
| 布林带(20) | 20 |
| 量价背离 | 10 |

**指数 K 线适配**：`IndexKlineBar` 的 `v` 字段对指数恒为 0，因此 `analyze_index_kline()` 跳过量价背离信号。`IndexKlineBar.t` 为字符串时间戳，Schema 中通过 Pydantic `@field_validator` 转为 int。

---

## 2. 大盘指数 K 线接入

### 2.1 API 端点

```
GET /api/v1/sub/kline?id={sub_id}&type={period}
```

- `id`：子指数 ID（从 `sub_index_data` 获取，默认 1）
- `type`：`1hour` | `4hour` | `1day` | `7day`（默认 `1day`）

### 2.2 响应格式

```json
{
  "code": 200,
  "msg": "Success",
  "data": [
    {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0}
  ]
}
```

### 2.3 Schema

`market_schemas.py` 新增：

```python
class IndexKlineBar(BaseModel):
    t: str      # 毫秒时间戳（字符串）
    o: float    # open
    c: float    # close
    h: float    # high
    l: float    # low
    v: int      # volume（指数恒为 0）
```

### 2.4 MarketAPI 扩展

```python
async def get_index_kline(
    self, sub_id: int = 1, period: str = "1day"
) -> list[IndexKlineBar]:
    """GET /api/v1/sub/kline"""
```

### 2.5 与单品 K 线的对比

| | 单品 K 线 | 大盘指数 K 线 |
|---|---|---|
| 端点 | `POST /info/simple/chartAll` | `GET /api/v1/sub/kline` |
| 客户端 | `ItemAPI.get_item_kline()` | `MarketAPI.get_index_kline()` |
| Schema | `KlineBar` (timestamp/open/close/high/low/volume) | `IndexKlineBar` (t/o/c/h/l/v) |
| Volume | 有实际值 | 恒为 0 |
| TA 分析 | `analyze_kline()` | `analyze_index_kline()` |

---

## 3. 并行子图执行

### 3.1 问题

用户查询单品时，只跑 Item Flow，Advisor 只有单品数据，缺乏大盘和同类饰品参考。

### 3.2 方案

新建 `parallel_item_flow.py`，单品查询时同时 fork 三路：

```
用户查询 "AK-47 红线"
         │
    ┌────┼────────┐
    ▼    ▼        ▼
  Item  Market  Scout
  Flow  Flow    Flow
    │    │        │
    └────┼────────┘
         ▼
    merge_contexts
         │
         ▼
      Advisor
      (综合三路上下文)
         │
         ▼
        END
```

### 3.3 State Schema

```python
class ParallelItemFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str                          # 原始用户查询
    good_name: str | None               # 提取的饰品名称

    # 三路并行结果
    item_context: dict | None           # Item Flow 的分析结果
    market_context: dict | None         # Market Flow 的分析结果
    scout_context: dict | None          # Scout Flow 的分析结果

    # 各路错误（不阻塞其他路）
    item_error: str | None
    market_error: str | None
    scout_error: str | None

    # Advisor 输出
    recommendation: str | None
    risk_level: str | None
    requires_confirmation: bool
    summary: str | None                 # 分析摘要（始终输出）
    action_detail: str | None           # 操作建议（高风险时需确认）
```

### 3.4 实现

1. **入口节点 `prepare_queries`**：从用户查询中提取 `good_name`。Market 和 Scout 子 flow 不需要 query 参数（它们的 fetch 节点直接调 API），只需启动即可。

2. **三路并行 `run_parallel` 节点**：在单个节点内用 `asyncio.gather()` 并行调用三个已编译子 flow。每路用 `try/except` 包裹，失败时写入对应 `*_error` 字段，不影响其他路。

```python
async def run_parallel(state, *, item_flow, market_flow, scout_flow):
    item_task = _run_item(state, item_flow)
    market_task = _run_market(market_flow)
    scout_task = _run_scout(scout_flow)

    item_result, market_result, scout_result = await asyncio.gather(
        item_task, market_task, scout_task, return_exceptions=True
    )

    return {
        "item_context": item_result.get("item_context") if not isinstance(item_result, Exception) else None,
        "market_context": market_result.get("market_context") if not isinstance(market_result, Exception) else None,
        "scout_context": scout_result.get("scout_context") if not isinstance(scout_result, Exception) else None,
        "item_error": str(item_result) if isinstance(item_result, Exception) else None,
        "market_error": str(market_result) if isinstance(market_result, Exception) else None,
        "scout_error": str(scout_result) if isinstance(scout_result, Exception) else None,
    }
```

3. **`merge_contexts` 节点**：将三路非 None 的 context 合并，传入 Advisor。如果三路都失败，直接返回错误。

4. **统一 Advisor**：拿到合并后的上下文，给出综合建议。

**图结构**：`prepare_queries → run_parallel → merge_contexts → advise → END`

### 3.5 改动点

- 三个子 flow 中各自的嵌入式 Advisor **保留**（独立使用时仍需要）
- `parallel_item_flow` 是新的"增强版"入口
- Router 对 `item_query` intent 改为调用 `parallel_item_flow`
- Market/Scout 子 flow 在并行模式下的 Advisor 输出被忽略，只取分析上下文

### 3.5 TA 集成

并行 Item 分支内的 `fetch_chart_node` 或新增的 TA 节点负责：
- 调用 `ItemAPI.get_item_kline()` 获取单品 K 线
- 调用 `analyze_kline()` 生成 TAReport
- TAReport 注入到 `item_context` 中

并行 Market 分支内：
- 调用 `MarketAPI.get_index_kline()` 获取大盘 K 线
- 调用 `analyze_index_kline()` 生成 TAReport
- TAReport 注入到 `market_context` 中

---

## 4. HITL 高风险确认

### 4.1 触发条件

Advisor 返回 `risk_level == "high"` 时。

### 4.2 流程

```
Advisor 输出
     │
     ▼
risk_level == "high"?
   ├── no → 直接输出完整建议 → END
   └── yes → 输出摘要 + 风险警告（隐藏操作细节）
                    │
                    ▼
              等待用户输入
               ├── "继续" → 输出完整操作建议 → END
               └── 取消 → "已取消，建议观望" → END
```

### 4.3 实现

**方案**：Flow 完整执行，CLI 层门控输出（approach a）。不在 Flow 层做 blocking I/O。

**Advisor 输出改为两段结构**。现有 Advisor 返回：
```python
{"recommendation": str, "risk_level": str, "requires_confirmation": bool}
```
改为：
```python
{
    "summary": str,              # 分析摘要 + 风险提示（始终输出）
    "action_detail": str,        # 具体操作建议（高风险时需确认才输出）
    "risk_level": str,           # "low" | "medium" | "high"
    "requires_confirmation": bool # risk_level == "high" 时为 True
}
```
`recommendation` 字段废弃，由 `summary` + `action_detail` 替代。现有三个子 flow 的嵌入式 Advisor 同步更新。

**Advisor Prompt 变更**：要求 LLM 输出 JSON 中将分析摘要放在 `summary`，具体操作建议放在 `action_detail`。

**Flow 层**：无变化。Flow 正常执行到 END，Advisor 输出包含 `summary` 和 `action_detail`。

**CLI 层**：`cli.py` 检测到 `requires_confirmation == True` 时：
1. 打印 `summary` + 风险警告
2. 提示用户输入（"输入'继续'查看操作建议，其他任意键取消"）
3. 确认 → 打印 `action_detail`；取消 → 打印"已取消，建议观望"

### 4.4 不做

- 不在 Flow 层做 blocking I/O 或中断（纯数据流，中断逻辑全在 CLI）
- 不做超时自动取消（CLI 场景等用户即可）
- Advisor LLM prompt 最小改动，只要求输出时把"分析"和"操作建议"分段

---

## 5. Scout 全维度扫描

### 5.1 当前状态

只有"涨跌幅 + 成交量"交叉筛选。

### 5.2 新增维度

| 维度 | filter 排序值 | 说明 |
|------|--------------|------|
| 涨跌幅（已有） | `价格_价格上升(百分比)_近7天` | 价格变化排行 |
| 成交量（已有） | `成交量_Steam日成交量` | 交易量排行 |
| 存世量 | `存世量_存世量_升序` | 存世量少的饰品（稀缺度） |
| 在售数量减少 | `在售数量_数量减少_近7天` | 供给收缩 |
| 求购数量增多 | `求购数量_数量增多_近7天` | 需求扩张 |
| 总市值 | `饰品总市值_总市值降序` | 大市值饰品（流动性好） |

**注**：Phase 2 PROBLEMS.md 第 6 条"存世量只有单品接口，无排行榜"需更正 — 排行榜 filter 支持 `存世量_存世量_升序/降序`。

### 5.3 交叉筛选升级

**Breaking change**：现有 `cross_filter_ranks(price_ids, vol_ids, ...)` 改为可变参数签名。调用方 `analyze_opportunities_node` 需同步更新。

```python
def cross_filter_ranks(
    *id_lists: list[int],    # 可变数量的排行 ID 列表
    top_n: int = 10,
    min_overlap: int = 2     # 至少出现在 N 个维度中
) -> list[int]
```

有价值的交叉信号：
- 价格涨 + 存世量少 + 求购增多 → 供需紧张，看多
- 价格跌 + 在售增多 + 求购减少 → 抛压大，看空
- 总市值高 + 价格涨 → 主流品种走强

### 5.4 RankAPI filter 参数常量

新建 `src/csqaq/infrastructure/csqaq_client/rank_filters.py` 定义常量：

```python
RANK_FILTERS = {
    "price_up_7d": {"排序": ["价格_价格上升(百分比)_近7天"]},
    "price_down_7d": {"排序": ["价格_价格下降(百分比)_近7天"]},
    "volume": {"排序": ["成交量_Steam日成交量"]},
    "stock_asc": {"排序": ["存世量_存世量_升序"]},
    "sell_decrease_7d": {"排序": ["在售数量_数量减少_近7天"]},
    "buy_increase_7d": {"排序": ["求购数量_数量增多_近7天"]},
    "market_cap_desc": {"排序": ["饰品总市值_总市值降序"]},
}
```

---

## 文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/csqaq/components/analysis/__init__.py` | 模块导出 |
| `src/csqaq/components/analysis/indicators.py` | 技术指标计算 |
| `src/csqaq/components/analysis/signals.py` | 信号检测 |
| `src/csqaq/components/analysis/analyzer.py` | TA 报告生成 |
| `src/csqaq/flows/parallel_item_flow.py` | 并行增强版单品分析 |
| `src/csqaq/infrastructure/csqaq_client/rank_filters.py` | 排行榜 filter 常量 |
| `tests/test_components/test_analysis/` | TA 模块测试（indicators, signals, analyzer） |
| `tests/test_components/test_scout_multi_dimension.py` | Scout 多维度交叉筛选测试 |
| `tests/test_flows/test_parallel_item_flow.py` | 并行 flow 测试 |
| `tests/test_flows/test_hitl_gate.py` | HITL 门控测试（flow 返回值 + CLI 行为） |
| `tests/fixtures/index_kline_response.json` | 大盘 K 线 fixture |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/csqaq/infrastructure/csqaq_client/market_schemas.py` | 新增 `IndexKlineBar` |
| `src/csqaq/infrastructure/csqaq_client/market.py` | 新增 `get_index_kline()` |
| `src/csqaq/infrastructure/analysis/indicators.py` | 改为 re-export |
| `src/csqaq/components/agents/market.py` | 集成 TA 分析 |
| `src/csqaq/components/agents/item.py` | 集成 TA 分析 |
| `src/csqaq/components/agents/scout.py` | 多维度 fetch + 交叉筛选升级 |
| `src/csqaq/components/agents/advisor.py` | 输出两段结构（summary + action_detail），废弃 recommendation 字段 |
| `src/csqaq/flows/router_flow.py` | item_query 改为调用 parallel_item_flow |
| `src/csqaq/main.py` | 注入新依赖 |
| `src/csqaq/api/cli.py` | HITL 确认逻辑 |
| `docs/PROBLEMS.md` | 更正存世量排行信息 |
| `docs/TODO.md` | 更新 Phase 3 完成状态 |

---

## 约束与风险

1. **指数 K 线 volume 恒为 0**：`analyze_index_kline()` 必须跳过量价背离信号
2. **排行榜 API 多次调用**：Scout 全维度需要 5-6 次 `get_rank_list()` 调用。缓解策略：用 `asyncio.gather()` 并发调用，CSQAQClient 的 token-bucket rate limiter 会自动控制节奏。如果 rate_limit=1.0 导致过慢（6秒+），可在 Scout 场景下调高限速或只取 top 3 维度。
3. **并行子图的错误隔离**：三路并行中某一路失败不应阻塞其他两路。`run_parallel` 节点用 `asyncio.gather(return_exceptions=True)` 捕获异常，写入 `*_error` 字段。
4. **HITL 中断只在 CLI 层**：Flow 层不做 blocking I/O。Flow 正常执行到 END，CLI 层根据 `requires_confirmation` 门控 `action_detail` 的输出。
5. **TA 指标最小数据量**：K 线数据不足时，对应信号返回 None 而非误导性结果。`TAReport.summary` 注明数据缺失。
6. **`cross_filter_ranks` 签名变更**：Breaking change，`analyze_opportunities_node` 调用方需同步更新。
