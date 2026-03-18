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

## 架构：4 层不变

```
API 层 (cli.py)
  → Flows 层 (router_flow → market_flow / scout_flow / item_flow)
    → Components 层 (router, market_agent, scout_agent, item_agent, advisor)
      → Infrastructure 层 (CSQAQClient, MarketAPI, RankAPI, ItemAPI, indicators, DB)
```

## 1. Infrastructure 层 — 新增

### MarketAPI (`infrastructure/csqaq_client/market.py`)

| 方法 | API路径 | 说明 |
|------|---------|------|
| `get_home_data()` | POST /current_data | 首页指数数据：指数值、涨跌分布、在线人数 |
| `get_sub_data(sub_id)` | POST /sub_data | 指数详情：今日涨跌、图表数据 |

### RankAPI (`infrastructure/csqaq_client/rank.py`)

| 方法 | API路径 | 说明 |
|------|---------|------|
| `get_rank_list(rank_type, period, page, size)` | POST /get_rank_list | 排行榜（涨跌幅/成交量/在售数量） |
| `get_page_list(filters, page, size)` | POST /get_page_list | 饰品列表筛选 |

### 新增 Schemas

- `IndexData` — 指数值、涨跌幅、涨跌家数分布
- `SubIndexDetail` — 指数详情图表数据
- `RankItem` — 排行条目：饰品名、指标值、变化率
- `PageListItem` — 列表条目

## 2. Components 层 — 新增

### Router (`components/router.py`)

```
用户查询 → 关键词匹配 → 命中? → IntentResult
                          ↓ 未命中
                     LLM(GPT-4o-mini) → IntentResult
```

- 关键词规则表：
  - `market_query`: 大盘、指数、行情、市场、涨跌分布
  - `scout_query`: 排行、推荐、值得买、机会、捡漏、热门
  - `item_query`: 默认兜底 + 包含具体饰品名
- 输出: `IntentResult(intent, confidence, item_name)`

### Market Agent (`components/agents/market.py`)

- 调用 MarketAPI 获取首页数据 + 指数详情
- LLM (analyst) 分析大盘方向
- 输出: `market_context`（方向判断 + 关键数据摘要）

### Scout Agent (`components/agents/scout.py`)

- 调用 RankAPI 获取 3 维度排行
- 交叉筛选：多维度同时出现 = 高关注度
- LLM (analyst) 总结机会列表
- 输出: `scout_context`（推荐列表 + 理由）

## 3. Flows 层 — 新增

### Router Flow (`flows/router_flow.py`) — 主入口图

```
START → router_node → 条件边
  ├─ "item_query"   → item_subflow → END
  ├─ "market_query" → market_subflow → END
  └─ "scout_query"  → scout_subflow → END
```

State: `query, intent, item_name, result, error`

每个子 flow 内部自带 Advisor 节点，输出最终 result。

### Market Flow (`flows/market_flow.py`)

```
START → fetch_market_data → analyze_market → advisor_node → END
```

### Scout Flow (`flows/scout_flow.py`)

```
START → fetch_rank_data → analyze_opportunities → advisor_node → END
```

### Item Flow — 不变

已有的 `build_item_flow()` 直接复用。Router 分发过去后接 Advisor。

## 4. 入口改动

### main.py

- `run_item_query` → `run_query`，内部构建 router_flow
- `App.init()` 新增 `MarketAPI`、`RankAPI` 初始化

### cli.py

- `chat()` 调用 `run_query` 替换 `run_item_query`

## 5. 错误处理

- API 失败 → 节点返回 `{error: ...}` → 条件边跳过 → Advisor 输出 "数据不足"
- LLM 失败 → 节点 catch → 写入 error
- Router 分类失败 → 默认走 `item_query` 兜底

## 6. 不在范围

- 并行子图执行 → TODO
- K线技术分析增强 → TODO
- HITL 高风险确认 → Phase 3
- 记忆系统 → Phase 3
- Server mode → Phase 4
