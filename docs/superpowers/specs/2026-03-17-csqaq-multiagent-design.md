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
7. **多用户系统**：用户注册登录、权限管理、数据隔离，每个用户绑定自己的 API Token

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
    error: str | None              # 错误信息（节点失败时写入）

class ItemFlowState(TypedDict):
    """单品分析子图状态"""
    messages: Annotated[list, add_messages]
    good_id: int | None
    item_detail: dict | None       # 单品详情
    chart_data: dict | None        # 图表数据
    kline_data: list | None        # K线数据
    indicators: dict | None        # 技术指标计算结果
    analysis_result: str | None
    error: str | None              # 错误信息（节点失败时写入）

class ScoutFlowState(TypedDict):
    """机会发现子图状态"""
    messages: Annotated[list, add_messages]
    rank_data: list | None         # 排行榜数据
    anomalies: list | None         # 检测到的异常
    opportunities: list | None     # 筛选出的机会
    error: str | None              # 错误信息（节点失败时写入）

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
    error: str | None              # 错误信息（节点失败时写入）
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
| `users` | id, username, password_hash, role("admin"/"user"), csqaq_api_token_enc, openai_api_key_enc, is_active, created_at | 用户账号 |
| `refresh_tokens` | id, user_id(FK), token_hash, expires_at, revoked | JWT 刷新令牌 |
| `watchlist` | id, **user_id(FK)**, good_id, name, market_hash_name, added_at, alert_threshold_pct, notes | 关注列表 |
| `price_snapshots` | id, good_id, timestamp, buff_sell, buff_buy, steam_sell, yyyp_sell, sell_num, buy_num | 定时价格快照（系统级） |
| `alerts` | id, **user_id(FK)**, alert_type, good_id, title, message, data_snapshot, triggered_at, acknowledged | 预警记录 |
| `session_summaries` | id, **user_id(FK)**, session_id, summary_text, message_count, created_at | 对话摘要 |
| `metrics` | id, metric_name, value, agent_role, correlation_id, timestamp | 系统运行指标（系统级） |

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

    # CSQAQ API (本地单用户模式使用；服务器模式下由各用户自行绑定)
    csqaq_api_token: str = ""                    # 服务器模式可为空
    csqaq_base_url: str = "https://api.csqaq.com/api/v1"
    csqaq_rate_limit: float = 1.0                # 请求/秒

    # OpenAI (本地单用户模式使用；服务器模式下由各用户自行绑定)
    openai_api_key: str = ""                     # 服务器模式可为空
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

    # 成本控制
    daily_token_budget: int = 500_000      # 日 Token 上限
    monthly_token_budget: int = 10_000_000 # 月 Token 上限

    # 认证 (服务器模式)
    secret_key: str = "change-me-in-production"  # JWT 签名 + API Token 加密密钥
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

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
apscheduler = ">=3.10,<4.0"
chromadb = ">=0.5"
rich = ">=13.0"
typer = ">=0.12"
pandas = ">=2.0"

[project.optional-dependencies]
dev = [
    "pytest >= 8.0",
    "pytest-asyncio >= 0.24",
    "respx >= 0.21",
]
server = [
    "fastapi >= 0.115",
    "uvicorn >= 0.30",
    "websockets >= 12.0",
    "redis >= 5.0",
    "asyncpg >= 0.29",
    "python-jose[cryptography] >= 3.3",
    "passlib[bcrypt] >= 1.7",
    "cryptography >= 43.0",
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
│   │   ├── web.py                      # FastAPI + WebSocket (服务器)
│   │   ├── auth.py                     # 注册/登录/改密/Token绑定路由
│   │   └── deps.py                     # FastAPI 依赖注入 (get_current_user 等)
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
│       │   └── models.py              # ORM 模型 (含 User, RefreshToken)
│       ├── auth/                       # 认证基础设施
│       │   ├── __init__.py
│       │   ├── hasher.py              # bcrypt 密码哈希
│       │   ├── jwt.py                 # JWT 生成/验证
│       │   └── crypto.py             # AES-256 加密 (用户 API Token 加密存储)
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
| 认证 | 无（单用户，.env 配置） | JWT Token（多用户注册登录） |
| API Token | .env 全局配置 | 各用户自行绑定，加密存储 |
| 数据库 | SQLite | PostgreSQL |
| 缓存 | MemoryCache | RedisCache (降级到 Memory) |
| 通知 | Rich 终端 | Webhook |
| 安装 | `pip install -e .` | `pip install -e ".[server]"` |

核心逻辑（flows/、components/、infrastructure/ 大部分）100% 共享，零代码改动。

---

## 用户系统与权限

### 用户模型

```python
class UserRole(str, Enum):
    admin = "admin"
    user = "user"
```

| 角色 | 权限 |
|------|------|
| **admin** | 查看所有用户数据、管理用户（禁用/删除）、查看全局统计、系统配置 |
| **user** | 仅操作自己的数据（关注列表、预警、对话历史）、绑定自己的 API Token |

### 认证方式

- **本地 CLI 模式**：单用户，无需登录，配置文件即为个人账户
- **服务器模式**：JWT Token 认证
  - `POST /auth/register` — 开放注册（用户名 + 密码）
  - `POST /auth/login` — 登录，返回 JWT access_token + refresh_token
  - `POST /auth/refresh` — 刷新 token
  - `PUT /auth/password` — 修改密码（需提供旧密码）
  - `GET /auth/me` — 获取当前用户信息

### 密码安全

- 使用 `bcrypt` 哈希存储，永不存明文
- 密码最低 8 位，至少包含字母和数字
- JWT access_token 过期时间 30 分钟，refresh_token 7 天
- refresh_token 存入数据库，支持主动失效（登出/改密时作废）

### API Token 绑定

每个用户绑定自己的密钥：

- `csqaq_api_token` — CSQAQ 开放 API Token（必须）
- `openai_api_key` — OpenAI API Key（必须）

通过 `PUT /auth/me/tokens` 接口绑定/更新，密钥加密存储（AES-256，密钥从环境变量 `SECRET_KEY` 派生）。

### 数据隔离

所有用户级数据表均带 `user_id` 外键，查询时自动注入当前用户 ID 过滤。`price_snapshots` 和 `metrics` 为系统级数据，不区分用户。

### 首个管理员

系统首次启动时，如果 `users` 表为空，第一个注册的用户自动成为 `admin`。后续注册用户默认为 `user` 角色。管理员可通过 `PUT /admin/users/{id}/role` 提升其他用户。

---

## API 认证方式

CSQAQ API 使用 **Header Token** 认证：

```
POST /api/v1/info/chart HTTP/1.1
Host: api.csqaq.com
ApiToken: <your_api_token>
Content-Type: application/json
```

- **Header 名称**：`ApiToken`（注意大小写）
- **获取方式**：在 csqaq.com 注册账号后，在个人中心获取
- **IP 白名单**：首次使用需调用 `POST /api/v1/bindIp` 绑定当前 IP，非固定 IP 场景每次启动时自动调用
- **Token 不过期**，无需刷新

客户端实现中，所有请求统一在 `httpx.AsyncClient` 的 `headers` 参数中注入 `ApiToken`。

---

## 错误处理策略

### API 客户端层

| 错误类型 | 处理方式 |
|---------|---------|
| HTTP 422 (参数校验失败) | 抛出 `CSQAQValidationError`，不重试 |
| HTTP 429 (限频) | 指数退避重试，最多 3 次 |
| HTTP 5xx (服务端错误) | 指数退避重试，最多 3 次 |
| 网络超时/连接错误 | 指数退避重试，最多 3 次 |
| HTTP 401/403 (认证失败) | 抛出 `CSQAQAuthError`，不重试，提示用户检查 Token |

### LangGraph 流程层

**节点失败不中断整个图**：采用"尽力而为"策略。

- 如果 Market Agent 调用 API 失败，将错误信息写入 `market_context`，Advisor 基于可用数据给出建议并标注数据缺失
- 如果所有数据 Agent 都失败，Advisor 直接返回"数据获取失败，请稍后重试"
- 每个子图的入口节点 catch 异常并写入 state 的 `error` 字段

### 后台监控层

- 单次监控失败：记录日志，下一个周期重试
- 连续 3 次失败：降低轮询频率（退避），通知用户"监控异常"
- API Token 失效：停止所有监控，CLI 输出错误提示

---

## 安全设计

### 密钥管理

- `.env` 文件存储敏感配置，**必须** 在 `.gitignore` 中排除
- 提供 `.env.example` 作为模板（不含真实密钥）
- 服务器部署时推荐通过环境变量注入，不使用 `.env` 文件
- `SECRET_KEY` 用于 JWT 签名和用户 API Token 加密，生产环境必须设置强随机值
- 用户的 `csqaq_api_token` 和 `openai_api_key` 使用 AES-256 加密后存入数据库，密钥从 `SECRET_KEY` 派生
- 启动时通过 Pydantic validators 校验必需字段，缺失则立即报错退出

### .gitignore

```
.env
data/
*.db
__pycache__/
*.pyc
.venv/
```

### 启动校验

- **本地模式**：`csqaq_api_token` 和 `openai_api_key` 必须在 `.env` 中配置，缺失时报错退出
- **服务器模式**：系统级仅需 `secret_key` 和 `database_url`；API Token 由各用户自行绑定，首次使用时校验
- 启动时在 `main.py` 中 `try/except` 捕获 `ValidationError`，输出清晰的提示信息

### 启动序列

1. 加载 `.env` → Pydantic Settings 校验（缺失必需字段则报错退出）
2. 调用 `POST /api/v1/bindIp` 绑定当前 IP（非固定 IP 场景必需）
3. 初始化数据库连接、缓存、LLM 工厂
4. 启动 LangGraph 图编译
5. 启动后台监控调度器（如果启用）
6. 进入 CLI 交互循环

---

## 限频与请求调度

CSQAQ API 限制 **1 次/秒/IP**。系统中存在并发请求源：用户交互查询 + 后台监控任务。

### 优先级队列设计

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ 用户交互请求  │────▶│  Priority Queue  │────▶│  Rate Limiter │──▶ CSQAQ API
│ (priority=0) │     │  (heapq)         │     │  (1 req/sec)  │
├──────────────┤     │                  │     └──────────────┘
│ 预警检测请求  │────▶│                  │
│ (priority=1) │     │                  │
├──────────────┤     │                  │
│ 后台扫描请求  │────▶│                  │
│ (priority=2) │     └─────────────────┘
└──────────────┘
```

- **Priority 0**：用户交互请求 — 最高优先级，立即执行
- **Priority 1**：预警检测（关注列表轮询）— 次优先
- **Priority 2**：后台排行榜扫描 — 最低优先，可延迟

用户交互时，后台请求自动让步，避免用户等待 20 秒。

### 批量优化

- 关注列表轮询：使用 `get_rank_list` 批量拉取（page_size=500），单次请求覆盖多个饰品，而非逐个查询
- 排行榜扫描：分页请求间间隔 1 秒

---

## 子图间状态映射

### Router → SubGraph 输入映射

```python
class QueryContext(TypedDict):
    """Router Agent 的结构化输出"""
    good_name: str | None      # 饰品名 (用于 Item/Scout)
    good_id: int | None        # 饰品 ID (如果已知)
    time_range: str | None     # "7d" | "30d" | "90d" | "180d" | "1y"
    platform: str | None       # "buff" | "steam" | "yyyp" | None(全部)
    analysis_type: str | None  # "price" | "trend" | "comparison" | None
```

### SubGraph → Advisor 输出映射

```
MainGraph 调用 SubGraph 时:
  1. 从 MainGraphState 提取 query_context → 传入 SubGraph 的初始 state
  2. SubGraph 执行完毕 → 返回 analysis_result
  3. MainGraph 将 analysis_result 写入 AdvisorFlowState 的对应 context 字段

具体映射:
  MarketFlowState.analysis_result → AdvisorFlowState.market_context
  ItemFlowState.analysis_result   → AdvisorFlowState.item_context
  ScoutFlowState.opportunities    → AdvisorFlowState.scout_context
```

### "complex" 意图处理

Router 输出结构化执行计划：

```python
class RoutingDecision(TypedDict):
    intent: str                          # "market" | "item" | "scout" | "complex"
    agents: list[str]                    # ["market", "item"] — complex 时指定需要的 agent
    query_context: QueryContext
```

complex 时，MainGraph 按 `agents` 列表顺序依次调用子图，每个子图的输出累积到 AdvisorFlowState 中，最后统一调用 Advisor。

---

## 成本控制

### 预估月度成本（中等使用强度）

| 组件 | 场景 | 估算 |
|------|------|------|
| GPT-4o-mini (Router) | 每次交互 ~200 tokens，日 50 次 | ~$0.5/月 |
| GPT-4o (数据 Agent) | 每次 ~2000 tokens，日 50 次 + 后台 ~300 次/天 | ~$15/月 |
| GPT-4o (摘要压缩) | 每日 ~5 次 | ~$0.5/月 |
| GPT-5 (Advisor) | 每次 ~3000 tokens，日 30 次 + 预警 ~10 次/天 | ~$30/月 |
| **合计** | | **~$46/月** |

### 成本控制机制

1. **规则前置过滤**：后台监控先用纯数值规则（`checks.py`）判断是否异常，只有触发阈值后才调用 LLM Agent 分析，避免每 5 分钟都消耗 GPT-5
2. **日/月 Token 预算**：`config.py` 中增加 `daily_token_budget` 和 `monthly_token_budget`，超出后暂停 LLM 调用，保留纯数据查询功能
3. **缓存命中**：相同查询在缓存 TTL 内复用结果，不重复调用 API 和 LLM

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    daily_token_budget: int = 500_000     # 日 Token 上限
    monthly_token_budget: int = 10_000_000 # 月 Token 上限
```

---

## 可观测性

### 日志

- 使用 Python `logging` + `rich.logging.RichHandler` 美化终端输出
- 结构化日志格式：`[时间] [级别] [模块] [correlation_id] 消息`
- 每次用户交互和每次监控周期分配唯一 `correlation_id`，方便追踪完整调用链

### LangGraph 追踪

- 开发阶段集成 LangSmith（可选）：通过环境变量 `LANGCHAIN_TRACING_V2=true` 启用
- 记录每个节点的输入/输出、耗时、Token 消耗

### 关键指标

- API 调用成功率/失败率
- 平均响应延迟（CSQAQ API + LLM）
- Token 消耗量（按 Agent 角色统计）
- 缓存命中率
- 预警触发频率

指标数据写入 SQLite `metrics` 表，CLI 提供 `csqaq stats` 命令查看。

---

## 测试策略

### 单元测试

- **API Client**：使用 `respx` 库 mock httpx 请求，验证限流、重试、错误处理逻辑
- **技术指标**：纯函数，用固定数据集验证计算正确性
- **State 映射**：验证子图间数据传递的正确性

### 集成测试

- **LangGraph Flow**：使用 `langchain-openai` 的 `FakeChatModel` 替代真实 LLM，验证图流转逻辑
- **数据库**：使用内存 SQLite (`sqlite:///:memory:`) 测试 ORM 操作

### E2E 测试（手动）

- 连接真实 CSQAQ API + OpenAI API，端到端验证核心场景
- 场景：查询单品 → 获取建议 → 加入关注列表 → 触发预警

### Mock 策略

- CSQAQ API：录制真实响应存为 JSON fixtures (`tests/fixtures/`)
- LLM：使用 FakeChatModel 返回预设响应，或用 GPT-4o-mini 降低测试成本

---

## CLI 命令设计

```
csqaq                          # 进入交互式对话模式
csqaq chat "AK红线能入吗"       # 单次查询

csqaq watch add "蝴蝶刀"        # 添加到关注列表
csqaq watch add --id 7310      # 通过 good_id 添加
csqaq watch list                # 查看关注列表
csqaq watch remove 7310         # 移除
csqaq watch set-threshold 7310 --pct 3.0  # 设置个别阈值

csqaq monitor start             # 启动后台监控
csqaq monitor stop              # 停止监控
csqaq monitor status            # 查看监控状态

csqaq alerts list               # 查看历史预警
csqaq alerts clear              # 清除已读预警

csqaq stats                     # 查看系统指标（API调用、Token消耗等）
```

---

## 分阶段实施

| 阶段 | 内容 | 目标 |
|------|------|------|
| **Phase 1** | 基础设施 + 单品分析 | CSQAQ Client、Item Agent、CLI 对话、能查询单品并获得建议 |
| **Phase 2** | 大盘 + 排行榜 + 完整对话 | Market Agent、Scout Agent、Router、Advisor 串联完整流程 |
| **Phase 3** | 后台监控 + 预警 | 关注列表、定时调度、预警检测、三层记忆 |
| **Phase 4** | 服务器部署 + 用户系统 | FastAPI、JWT 认证、用户注册登录、API Token 绑定、权限管理、WebSocket、Redis、PostgreSQL、Webhook 通知 |
