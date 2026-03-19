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

**迁移计划**：`infrastructure/analysis/indicators.py` 的现有 4 个方法迁移到新模块，原位置改为 re-export（`from csqaq.components.analysis.indicators import TechnicalIndicators`）保持向后兼容。

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

**综合方向**：信号投票机制。统计 bullish/bearish 信号数量，多数胜出。平局为 neutral。

**指数 K 线适配**：`IndexKlineBar` 的 `v` 字段对指数恒为 0，因此 `analyze_index_kline()` 跳过量价背离信号。

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

### 3.3 实现

1. **入口节点 `prepare_queries`**：从用户的单品查询中提取 item_name，同时生成 market 和 scout 的默认查询
2. **三路并行**：各自调用已有的 `build_item_flow()`、`build_market_flow()`、`build_scout_flow()`
3. **`merge_contexts` 节点**：汇总三路的 `item_context`、`market_context`、`scout_context`
4. **统一 Advisor**：拿到完整上下文后给出综合建议

### 3.4 改动点

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

**Advisor 输出改为两段结构**：
- `summary`：分析摘要 + 风险提示（始终输出）
- `action_detail`：具体操作建议（高风险时需确认才输出）

**Flow 层**：在 Advisor 输出后加 `hitl_gate` 条件节点，high risk 时中断图执行。

**CLI 层**：`cli.py` 检测到 `requires_confirmation == True` 时，先打印 summary，等用户输入后再决定是否打印 action_detail。

### 4.4 不做

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

在 `rank.py` 或新建 `rank_filters.py` 中定义常量：

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
| `tests/test_components/test_analysis/` | TA 模块测试 |
| `tests/test_flows/test_parallel_item_flow.py` | 并行 flow 测试 |
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
| `src/csqaq/components/agents/advisor.py` | 输出两段结构（summary + action_detail） |
| `src/csqaq/flows/router_flow.py` | item_query 改为调用 parallel_item_flow |
| `src/csqaq/main.py` | 注入新依赖 |
| `src/csqaq/api/cli.py` | HITL 确认逻辑 |
| `docs/PROBLEMS.md` | 更正存世量排行信息 |
| `docs/TODO.md` | 更新 Phase 3 完成状态 |

---

## 约束与风险

1. **指数 K 线 volume 恒为 0**：`analyze_index_kline()` 必须跳过量价背离信号
2. **排行榜 API 多次调用**：Scout 全维度需要 5-6 次 `get_rank_list()` 调用，需注意 rate limit
3. **并行子图的错误隔离**：三路并行中某一路失败不应阻塞其他两路，merge 节点需要容错
4. **HITL 中断只在 CLI 层**：Flow 层不做 blocking I/O，中断逻辑在 CLI 层处理
