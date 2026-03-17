# CSQAQ Multi-Agent 饰品投资分析系统 — 设计文档

## 概述

基于 LangGraph 构建的 CS2 饰品市场 Multi-Agent 分析系统。系统自动查询大盘趋势和单品趋势，结合技术指标分析，通过 GPT-5 推理模型提供投资建议和异常预警。

**目标用户**：CS2 饰品投资者/交易者
**数据源**：CSQAQ 开放 API（https://api.csqaq.com/api/v1）
**部署策略**：本地 CLI 优先，配置切换即可部署到服务器（FastAPI + WebSocket）

---

## 需求摘要

1. **大盘趋势分析**：饰品指数、涨跌分布、贪婪指数、在线人数、K线图
2. **单品趋势分析**：多平台价格、历史走势、K线技术分析、存世量
3. **机会发现**：定时扫描排行榜，发现异常涨跌和低估饰品
4. **投资建议**：综合以上数据，GPT-5 深度推理给出有理据的买卖建议
5. **异常预警**：后台监控，价格异动、大盘情绪突变时主动提醒
6. **混合监控**：关注列表高频轮询 + 全站排行榜低频扫描

---

## 架构设计

### 四层架构

```
┌─────────────────────────────────────────┐
│           API Layer (接口层)             │
│   cli.py (Typer) / web.py (FastAPI)     │
├─────────────────────────────────────────┤
│        Flow Layer (编排层)               │
│   LangGraph 图定义 + 子图组合            │
├─────────────────────────────────────────┤
│      Component Layer (组件层)            │
│   Agents / Tools / Models / Memory      │
├─────────────────────────────────────────┤
│    Infrastructure Layer (基础设施层)      │
│   CSQAQ Client / DB / Cache / Notifier  │
└─────────────────────────────────────────┘
```

各层单向依赖：上层依赖下层，下层不感知上层。

### Agent 角色

| Agent | 职责 | LLM | 使用的 CSQAQ API |
|-------|------|-----|-----------------|
| **Router Agent** | 解析用户意图，路由到对应 agent/子图 | GPT-4o-mini | 无 |
| **Market Agent** | 大盘指数分析、情绪判断、K线解读 | GPT-4o | `current_data`, `sub_data`, `sub/kline` |
| **Item Agent** | 单品详情、多平台价差、历史走势分析 | GPT-4o | `search/suggest`, `info/good`, `info/chart`, `info/simple/chartAll` |
| **Scout Agent** | 扫描排行榜、发现异常饰品、筛选机会 | GPT-4o | `get_rank_list`, `get_page_list` |
| **Advisor Agent** | 汇总所有数据，给出最终投资建议和风险评估 | GPT-5 | 无（消费其他 agent 输出） |

Router 用轻量模型控制成本；数据 Agent 用 GPT-4o 平衡速度和分析质量；Advisor 用 GPT-5 推理模型做深度综合决策。

---

## 工作流设计

### 工作流 1：用户对话（交互式）

```
User Input
    │
    ▼
┌─────────┐
│  Router  │ ── 意图分类 ──┬── "market"  → MarketSubGraph ──┐
│  Agent   │               ├── "item"    → ItemSubGraph   ──┤
│          │               ├── "scout"   → ScoutSubGraph  ──┤
│          │               └── "complex" → 多个子图串联   ──┤
└─────────┘                                                 │
                                                            ▼
                                                    AdvisorSubGraph
                                                      (GPT-5)
                                                            │
                                                ┌───────────┤
                                                ▼           ▼
                                          Response     HITL 确认
                                          to User     (高风险建议)
```

**路由逻辑举例**：
- "大盘现在什么情况" → Router → MarketSubGraph → 直接返回
- "AK红线能入吗" → Router → ItemSubGraph → AdvisorSubGraph → 返回建议
- "有没有低估的刀" → Router → ScoutSubGraph → AdvisorSubGraph → 返回建议
- "大盘跌了，我的关注列表里哪些该出" → Router → MarketSubGraph + ItemSubGraph(批量) → AdvisorSubGraph

### 工作流 2：后台监控（定时自动）

```
Scheduler (APScheduler)
├── 每 5 分钟 → Market Agent → 大盘异常检测 → 触发预警?
├── 每 5 分钟 → Item Agent   → 关注列表轮询 → 触发预警?
└── 每 30 分钟 → Scout Agent  → 排行榜扫描  → 触发预警?
                                                  │
                                                  ▼ (是)
                                           Advisor Agent
                                           生成预警报告
                                                  │
                                                  ▼
                                           Notifier 输出
```

**预警触发条件（可配置）**：
- 大盘贪婪指数突变（如跨级别变动）
- 关注列表饰品日涨跌幅超过阈值（默认 5%）
- 排行榜出现异常集中涨跌的品类
- 关注饰品多平台价差异常扩大

---

## LangGraph State 定义

```python
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class MainGraphState(TypedDict):
    """顶层路由图状态"""
    messages: Annotated[list, add_messages]
    intent: str                    # "market" | "item" | "scout" | "complex"
    query_context: dict            # 从用户输入提取的结构化参数

class MarketFlowState(TypedDict):
    """大盘分析子图状态"""
    messages: Annotated[list, add_messages]
    index_data: dict | None        # 首页指数数据
    sub_index_data: dict | None    # 子指数详情
    kline_data: list | None        # K线数据
    analysis_result: str | None    # 分析结论

class ItemFlowState(TypedDict):
    """单品分析子图状态"""
    messages: Annotated[list, add_messages]
    good_id: int | None
    item_detail: dict | None       # 单品详情
    chart_data: dict | None        # 图表数据
    kline_data: list | None        # K线数据
    indicators: dict | None        # 技术指标计算结果
    analysis_result: str | None

class ScoutFlowState(TypedDict):
    """机会发现子图状态"""
    messages: Annotated[list, add_messages]
    rank_data: list | None         # 排行榜数据
    anomalies: list | None         # 检测到的异常
    opportunities: list | None     # 筛选出的机会

class AdvisorFlowState(TypedDict):
    """投资顾问子图状态"""
    messages: Annotated[list, add_messages]
    market_context: dict | None    # Market Agent 产出
    item_context: dict | None      # Item Agent 产出
    scout_context: dict | None     # Scout Agent 产出
    historical_advice: list | None # 从 ChromaDB 检索的历史分析
    recommendation: str | None     # 最终建议
    risk_level: str | None         # "low" | "medium" | "high"
    requires_confirmation: bool    # 是否需要 HITL 确认
```

---

## 三层记忆系统

| 层级 | 存储 | 用途 | 生命周期 |
|------|------|------|---------|
| **短期记忆** | LangGraph State `messages` | 当前对话上下文 | 单次会话 |
| **长期摘要** | SQLite `session_summaries` 表 | 对话过长时 LLM 压缩成摘要 | 跨会话持久化 |
| **分析记忆** | ChromaDB | Advisor 历史分析报告的向量索引 | 永久，可手动清理 |

**记忆流转**：
1. 对话进行中，`messages` 累积
2. 当 messages 超过阈值（如 20 条），Compressor 用 LLM 将旧消息压缩为摘要存入 SQLite
3. Advisor 每次给出建议后，将分析报告（含数据快照 + 结论 + 时间戳）存入 ChromaDB
4. 下次分析时，先检索 ChromaDB 中相似场景的历史分析，注入 Advisor 的 prompt

---

## LLM 工厂模式

```python
# components/models/factory.py
class ModelFactory:
    _registry: dict[str, ModelConfig] = {}

    @classmethod
    def register(cls, role: str, provider: str, model: str, **kwargs):
        cls._registry[role] = ModelConfig(provider=provider, model=model, **kwargs)

    @classmethod
    def get(cls, role: str) -> BaseChatModel:
        config = cls._registry[role]
        return create_model(config)

# 配置注册（从 .env 读取）
ModelFactory.register("router",  provider="openai", model="gpt-4o-mini")
ModelFactory.register("market",  provider="openai", model="gpt-4o")
ModelFactory.register("item",    provider="openai", model="gpt-4o")
ModelFactory.register("scout",   provider="openai", model="gpt-4o")
ModelFactory.register("advisor", provider="openai", model="gpt-5")
```

切换模型只需改 `.env`，不改代码。架构预留了多 provider 支持。

---

## 数据层设计

### CSQAQ API Client

```
infrastructure/csqaq_client/
├── client.py      # 核心 HTTP 客户端
│                  # - httpx.AsyncClient
│                  # - 令牌桶限流 (1 req/sec)
│                  # - 自动重试 (指数退避, 最多 3 次)
│                  # - 统一错误处理
├── schemas.py     # Pydantic v2 响应模型 (严格类型)
├── market.py      # 大盘端点
│   ├── get_index_data(type) → IndexData
│   ├── get_sub_index(id, type) → SubIndexData
│   └── get_index_kline(id, type) → list[KlineBar]
├── item.py        # 单品端点
│   ├── search_suggest(text) → list[SuggestItem]
│   ├── get_item_detail(good_id) → ItemDetail
│   ├── get_item_chart(good_id, key, platform, period) → ChartData
│   └── get_item_kline(good_id, plat, periods, max_time) → list[KlineBar]
└── ranking.py     # 排行榜端点
    ├── get_rank_list(page, size, filter, sort) → RankResult
    └── get_page_list(page, size, search, filter) → PageResult
```

### 数据库 (SQLAlchemy ORM)

| 表 | 字段 | 用途 |
|---|------|------|
| `watchlist` | id, good_id, name, market_hash_name, added_at, alert_threshold_pct, notes | 关注列表 |
| `price_snapshots` | id, good_id, timestamp, buff_sell, buff_buy, steam_sell, yyyp_sell, sell_num, buy_num | 定时价格快照 |
| `alerts` | id, alert_type, good_id, title, message, data_snapshot, triggered_at, acknowledged | 预警记录 |
| `session_summaries` | id, session_id, summary_text, message_count, created_at | 对话摘要 |

本地用 SQLite，服务器用 PostgreSQL，通过 `DATABASE_URL` 环境变量切换。

### 缓存层

```python
# 抽象接口
class CacheBackend(ABC):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int): ...

# 实现
class MemoryCache(CacheBackend): ...      # 本地默认
class RedisCache(CacheBackend): ...       # 服务器
class AutoFallbackCache(CacheBackend):    # 自动降级: Redis → Memory
```

缓存 CSQAQ API 响应（TTL 可配置，默认 60s），避免重复请求，尊重限频。

---

## 技术指标分析引擎

```python
# infrastructure/analysis/indicators.py
class TechnicalIndicators:
    @staticmethod
    def moving_average(prices: list[float], window: int) -> list[float]: ...
    @staticmethod
    def volatility(prices: list[float], window: int) -> float: ...
    @staticmethod
    def price_momentum(prices: list[float], period: int) -> float: ...
    @staticmethod
    def platform_spread(buff_price: float, steam_price: float) -> float: ...
    @staticmethod
    def volume_trend(volumes: list[int], window: int) -> str: ...

# infrastructure/analysis/comparator.py
class TrendComparator:
    def compare_periods(self, good_id: int, period_a: tuple, period_b: tuple) -> ComparisonResult: ...
    def detect_anomaly(self, good_id: int, threshold_pct: float) -> AnomalyResult | None: ...
    def market_correlation(self, good_id: int, market_index: list[float]) -> float: ...
```

Agent 不直接做数值计算 — 由 analysis 引擎计算好指标，Agent 负责解读。

---

## HITL（人在回路）机制

Advisor Agent 给出建议时，如果 `risk_level == "high"`（如建议大额买入/清仓），通过 LangGraph 的 `interrupt` 暂停执行：

1. Advisor 产出建议 + risk_level
2. 如果 risk_level 为 high，触发 `interrupt`，CLI 展示建议并等待用户确认
3. 用户输入 `yes` → 记录并执行后续动作（如存入分析记忆）
4. 用户输入 `no` + 反馈 → Advisor 根据反馈调整建议

---

## 配置管理

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 运行模式
    mode: str = "local"                          # "local" | "server"

    # CSQAQ API
    csqaq_api_token: str
    csqaq_base_url: str = "https://api.csqaq.com/api/v1"
    csqaq_rate_limit: float = 1.0                # 请求/秒

    # OpenAI
    openai_api_key: str
    router_model: str = "gpt-4o-mini"
    analyst_model: str = "gpt-4o"
    advisor_model: str = "gpt-5"

    # 数据库
    database_url: str = "sqlite:///data/csqaq.db"

    # 缓存
    redis_url: str | None = None                 # None → 使用内存缓存
    api_cache_ttl: int = 60                      # 秒

    # 监控
    watchlist_poll_interval: int = 300            # 5 分钟
    market_poll_interval: int = 300               # 5 分钟
    scout_scan_interval: int = 1800               # 30 分钟
    alert_price_threshold_pct: float = 5.0        # 涨跌幅预警阈值 %

    # 记忆
    max_history_messages: int = 20                # 触发摘要压缩的阈值
    chromadb_path: str = "data/chroma"

    # 通知 (服务器模式)
    notify_webhook_url: str | None = None

    model_config = {"env_file": ".env"}
```

---

## 核心依赖

```toml
[project]
name = "csqaq"
requires-python = ">=3.11"

[project.dependencies]
langgraph = ">=0.2"
langchain-openai = ">=0.2"
langchain-community = ">=0.3"
httpx = ">=0.27"
pydantic = ">=2.0"
pydantic-settings = ">=2.0"
sqlalchemy = {version = ">=2.0", extras = ["asyncio"]}
aiosqlite = ">=0.20"
apscheduler = ">=3.10"
chromadb = ">=0.5"
rich = ">=13.0"
typer = ">=0.12"
pandas = ">=2.0"

[project.optional-dependencies]
server = [
    "fastapi >= 0.115",
    "uvicorn >= 0.30",
    "websockets >= 12.0",
    "redis >= 5.0",
    "asyncpg >= 0.29",
]
```

本地安装 `pip install -e .`，服务器安装 `pip install -e ".[server]"`。

---

## 项目结构

```
CSQAQ/
├── pyproject.toml
├── .env.example
├── README.md
│
├── src/csqaq/
│   ├── __init__.py
│   ├── main.py                         # 启动入口
│   ├── config.py                       # pydantic-settings 配置
│   │
│   ├── api/                            # 接口层
│   │   ├── __init__.py
│   │   ├── cli.py                      # Typer CLI (本地)
│   │   └── web.py                      # FastAPI + WebSocket (服务器)
│   │
│   ├── flows/                          # 编排层 — LangGraph 图
│   │   ├── __init__.py
│   │   ├── main_graph.py               # 顶层路由图
│   │   ├── market_flow.py              # 大盘分析子图
│   │   ├── item_flow.py                # 单品分析子图
│   │   ├── scout_flow.py               # 机会发现子图
│   │   └── advisor_flow.py             # 投资顾问子图 (GPT-5 + HITL)
│   │
│   ├── components/                     # 组件层
│   │   ├── __init__.py
│   │   ├── agents/                     # Agent prompt + 节点逻辑
│   │   │   ├── __init__.py
│   │   │   ├── router.py               # 意图分类
│   │   │   ├── market.py               # 大盘分析师
│   │   │   ├── item.py                 # 单品分析师
│   │   │   ├── scout.py                # 机会猎手
│   │   │   └── advisor.py              # 投资顾问
│   │   ├── tools/                      # Agent 可调用的工具函数
│   │   │   ├── __init__.py
│   │   │   ├── market_tools.py
│   │   │   ├── item_tools.py
│   │   │   ├── ranking_tools.py
│   │   │   └── watchlist_tools.py
│   │   ├── models/                     # LLM 工厂
│   │   │   ├── __init__.py
│   │   │   ├── factory.py              # Registry + Factory 模式
│   │   │   └── providers.py            # OpenAI 各模型注册
│   │   └── memory/                     # 三层记忆系统
│   │       ├── __init__.py
│   │       ├── session.py              # 短期对话记忆
│   │       ├── compressor.py           # 长期摘要压缩
│   │       └── analysis_store.py       # ChromaDB 分析记忆
│   │
│   └── infrastructure/                 # 基础设施层
│       ├── __init__.py
│       ├── csqaq_client/               # CSQAQ API 客户端
│       │   ├── __init__.py
│       │   ├── client.py               # httpx + 限流 + 重试
│       │   ├── schemas.py              # Pydantic 响应模型
│       │   ├── market.py               # 大盘端点
│       │   ├── item.py                 # 单品端点
│       │   └── ranking.py              # 排行榜端点
│       ├── database/                   # 数据持久化
│       │   ├── __init__.py
│       │   ├── connection.py           # SQLAlchemy 引擎管理
│       │   └── models.py              # ORM 模型
│       ├── cache/                      # 缓存 (自动降级)
│       │   ├── __init__.py
│       │   ├── base.py                 # 抽象接口
│       │   ├── memory_cache.py         # 内存实现
│       │   └── redis_cache.py          # Redis 实现
│       ├── analysis/                   # 数据分析引擎
│       │   ├── __init__.py
│       │   ├── indicators.py           # 技术指标 (MA, 波动率, 动量)
│       │   └── comparator.py           # 趋势对比 (同比/环比/异常检测)
│       ├── monitor/                    # 后台定时监控
│       │   ├── __init__.py
│       │   ├── scheduler.py            # APScheduler 调度器
│       │   ├── checks.py              # 预警检测逻辑
│       │   └── alerts.py               # 预警生成
│       └── notifiers/                  # 通知适配
│           ├── __init__.py
│           ├── base.py                 # 抽象接口
│           ├── console.py              # Rich 终端输出
│           └── webhook.py              # 微信/Telegram webhook
│
├── data/                               # 本地数据 (gitignored)
│   ├── csqaq.db                        # SQLite 数据库
│   └── chroma/                         # ChromaDB 存储
│
├── tests/
│   ├── test_api/
│   ├── test_flows/
│   ├── test_components/
│   └── test_infrastructure/
│
└── docs/
    └── superpowers/
        └── specs/
```

---

## 本地 vs 服务器 — 配置切换

| 维度 | 本地 (MODE=local) | 服务器 (MODE=server) |
|------|-------------------|---------------------|
| 入口 | `python -m csqaq.api.cli` | `uvicorn csqaq.api.web:app` |
| 数据库 | SQLite | PostgreSQL |
| 缓存 | MemoryCache | RedisCache (降级到 Memory) |
| 通知 | Rich 终端 | Webhook |
| 安装 | `pip install -e .` | `pip install -e ".[server]"` |

核心逻辑（flows/、components/、infrastructure/ 大部分）100% 共享，零代码改动。
