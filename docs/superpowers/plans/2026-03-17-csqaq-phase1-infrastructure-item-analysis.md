# Phase 1: Infrastructure + Item Analysis — 完成记录

**状态：已完成** | 2026-03-18

**目标：** 搭建基础设施 + 实现单品分析流水线 — 用户通过 CLI 查询 CS2 饰品，获得 GPT-4o 分析 + GPT-5 投资建议。

**架构：** 自底向上构建 4 层架构：Infrastructure → Components → Flows → API，每层只向下依赖。

**技术栈：** Python 3.11+, httpx, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 (async + aiosqlite), LangGraph, langchain-openai, Rich, Typer

**设计文档：** `docs/superpowers/specs/2026-03-17-csqaq-multiagent-design.md`

---

## 文件结构

```
src/csqaq/
├── config.py                              # pydantic-settings 配置
├── main.py                                # App 容器 + run_item_query 入口
├── api/cli.py                             # Typer CLI (chat 命令)
├── flows/
│   ├── item_flow.py                       # LangGraph 单品分析子图
│   └── advisor_flow.py                    # LangGraph 顾问子图
├── components/
│   ├── agents/item.py                     # 3 个节点函数: resolve → fetch_chart → analyze
│   ├── agents/advisor.py                  # advise_node, JSON 输出 + risk_level
│   ├── tools/item_tools.py               # 4 个 @tool: search, detail, chart, indicators
│   └── models/factory.py + providers.py   # ModelFactory 注册表 + ChatOpenAI 创建
└── infrastructure/
    ├── csqaq_client/
    │   ├── client.py                      # 异步 HTTP 客户端 (限流 + 重试)
    │   ├── errors.py                      # 异常层级
    │   ├── schemas.py                     # Pydantic 响应模型
    │   └── item.py                        # 4 个 API 端点方法
    ├── database/
    │   ├── connection.py                  # async engine + @asynccontextmanager session
    │   └── models.py                      # ORM: Watchlist, PriceSnapshot, Alert, SessionSummary, Metric
    ├── cache/
    │   ├── base.py                        # CacheBackend ABC
    │   └── memory_cache.py               # 内存 TTL 缓存
    └── analysis/indicators.py             # MA, 波动率, 动量, 价差, 成交量趋势

tests/                                     # 50 个测试，全部通过
├── conftest.py                            # 共享 fixtures (fixture_dir, mock_item_api)
├── fixtures/*.json                        # 4 个 API 响应 fixture
├── test_infrastructure/                   # 25 个测试 (client, schemas, endpoints, db, cache, indicators)
├── test_components/                       # 8 个测试 (model_factory, item_tools)
├── test_flows/                            # 4 个测试 (item_flow, advisor_flow)
└── test_e2e.py                            # 1 个端到端集成测试
```

---

## 任务执行记录

### Task 1: 项目脚手架
- 创建 `pyproject.toml`（hatchling 构建，所有依赖声明）
- 创建 `.gitignore`, `.env.example`, 所有 `__init__.py`

### Task 2: 配置系统
- `Settings(BaseSettings)` + `.env` 加载
- 所有配置项有默认值，`mode: Literal["local", "server"]`

### Task 3: CSQAQ HTTP 客户端
- `CSQAQClient`: ApiToken 头注入，`asyncio.Lock` 限流，指数退避重试 (max 3)
- 异常层级: `CSQAQClientError` → Auth/Validation/RateLimit/Server

### Task 4: API 响应 Schema
- `SuggestItem`, `ItemDetail`, `ChartPoint`, `ChartData`, `KlineBar`
- `populate_by_name=True` + `Field(alias=...)` 映射驼峰 API 字段

### Task 5: Item API 端点
- `ItemAPI`: search_suggest, get_item_detail, get_item_chart, get_item_kline

### Task 6: 数据库层
- SQLAlchemy 2.0 async: `Database` 类自动转换 sqlite → aiosqlite
- ORM: Watchlist, PriceSnapshot, Alert, SessionSummary, Metric
- `session()` 使用 `@asynccontextmanager` 强制正确用法

### Task 7: 内存缓存
- `CacheBackend` ABC + `MemoryCache`（`time.monotonic()` TTL）

### Task 8: 技术指标引擎
- `TechnicalIndicators`: moving_average, volatility, price_momentum, platform_spread, volume_trend
- volume_trend 使用对称窗口（`window*2` 数据量要求）

### Task 9: LLM 模型工厂
- `ModelFactory`: register(role, provider, model, temperature) → create(role) → ChatOpenAI
- 3 个角色: router(gpt-4o-mini), analyst(gpt-4o), advisor(gpt-5)

### Task 10: Item Tools
- 4 个 `@tool` 装饰的异步函数，供 Agent 调用

### Task 11: Item Agent + Item Flow
- 3 个节点函数: `resolve_item_node` → `fetch_chart_node` → `analyze_node`
- LangGraph StateGraph 条件边: 有错误跳过 chart 直接到 analyze
- `functools.partial` 绑定依赖（item_api, model_factory）到节点

### Task 12: Advisor Agent + Advisor Flow
- `advise_node`: 综合 item/market/scout 上下文，输出 JSON {recommendation, risk_level}
- risk_level ∈ {low, medium, high}，high → requires_confirmation = True
- JSON 解析失败时降级为原始文本 + low 风险

### Task 13: CLI + 应用入口
- `App` 容器类: 延迟导入 + `init()` 异步初始化所有服务
- 属性访问有 `RuntimeError` 保护（未初始化时报错）
- `run_item_query()`: item_flow → advisor_flow 链式调用
- Typer CLI: 单次查询模式 + 交互模式

### Task 14: 端到端集成测试
- 完整流水线: search → detail → chart → indicators → analyze → advise
- Mock LLM 按角色返回不同响应，验证数据全程流通

### Task 15: 最终验证
- 50 测试全部通过
- `data/.gitkeep` 已提交

---

## 代码审查修复

审查后修复了以下问题（提交 `8c1e4a8`）：

| 编号 | 问题 | 修复 |
|------|------|------|
| I-1 | volume_trend 非对称窗口 | 改为 `window*2` 对称比较 |
| I-2 | httpx.AsyncClient 构造异常泄漏 | 添加 `__del__` 安全网 |
| I-3 | Database.session() 无法强制正确用法 | 改为 `@asynccontextmanager` |
| I-4 | App 属性 init() 前返回 None | 添加 RuntimeError 保护 |
| I-5 | data/.gitkeep 未提交 | `git add -f` 提交 |
| I-6 | inspect.isawaitable hack 污染生产代码 | 移除，测试改用 MagicMock |
| M-2 | Settings.mode 无验证 | 改为 `Literal["local", "server"]` |
| M-3/4 | main.py 未使用 import | 移除 asyncio, sys |
| M-6 | CLI query 类型不精确 | 改为 `str \| None` |

---

## 关键设计决策

1. **functools.partial 注入依赖到 LangGraph 节点** — 避免全局状态，保持可测试性
2. **asyncio.Lock 限流** — 简单有效，Phase 1 单用户足够
3. **异常分类重试** — 401/403/422 不重试，429/5xx 重试，指数退避
4. **Pydantic alias + populate_by_name** — 兼容 API 驼峰字段和 Python 蛇形命名
5. **sqlite+aiosqlite 自动转换** — 开发时零配置
6. **条件边处理错误** — resolve 失败时跳过 chart，直接到 analyze 报告错误

---

## 提交历史

```
8c1e4a8 fix: address Phase 1 code review findings
17e38bd test: add E2E integration test for item analysis pipeline
257eff6 feat: add Typer CLI and application entry point
a85a154 feat: add Advisor Agent and LangGraph advisor flow
4e84a6e feat: add Item Agent and LangGraph item analysis flow
92d1935 feat: add LangChain item tools (search, detail, chart, indicators)
201fd3b feat: add LLM model factory with registry pattern
59814fd feat: add technical indicators engine (MA, volatility, momentum, spread)
7755afb feat: add in-memory cache with TTL support
c37d4d6 feat: add SQLAlchemy async database layer with ORM models
f114f89 feat: add CSQAQ item API endpoints with typed responses
8e7b55a feat: add Pydantic schemas for CSQAQ API responses
ec7a834 feat: add CSQAQ API client with rate limiting and retry
9a47c1f feat: add pydantic-settings configuration
ed7c500 chore: scaffold project structure with dependencies
```

---

## Phase 2 方向

- Market Agent（大盘分析）
- Scout Agent（机会发现）
- Router Agent（意图路由，GPT-4o-mini）
- Main Graph（完整多 Agent 编排）
- 监控系统（Watchlist、Alert、定时轮询）
- 记忆系统（ChromaDB 长期记忆）
