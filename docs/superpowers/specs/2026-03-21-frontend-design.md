# CSQAQ Frontend Design Spec

> Date: 2026-03-21
> Status: Draft

## 1. Overview

为 CSQAQ (CS2 饰品投资分析系统) 构建面向大众的专业级前端。前后端完全分离，前端独立仓库，通过 WebSocket + REST API 与现有 Python 后端通信。

### 1.1 技术选型

| 类别 | 选择 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| UI 组件库 | Ant Design 5 (暗色主题) |
| 图表 | ECharts 5 |
| 状态管理 | Zustand (UI 状态) + React Query (服务端缓存) |
| 通信 | WebSocket (实时分析) + REST (数据查询) |
| 路由 | React Router v6 |
| HTTP 客户端 | Axios |
| 认证 | JWT (Access + Refresh Token) |

### 1.2 项目定位

- 面向大众的 CS2 饰品投资分析产品
- 暗色主题为主，类 TradingView 专业金融风格
- 混合交互：Dashboard + 搜索 + 可展开 AI 对话侧边栏

## 2. Overall Architecture

```
┌─────────────────────────────────────┐
│  Frontend (独立仓库: csqaq-web)       │
│  React + TS + Vite + Ant Design 5   │
│                                     │
│  Zustand ── UI 状态                  │
│  React Query ── 服务端数据缓存        │
│  useWebSocket ── 实时分析推送         │
│  ECharts ── K线/技术指标/存世量图表    │
└──────────────┬──────────────────────┘
               │ WebSocket + REST
┌──────────────┴──────────────────────┐
│  Backend (现有 CSQAQ 仓库)            │
│  FastAPI + WebSocket Server          │
│                                     │
│  /api/v1/* ── REST (CRUD, 查询)      │
│  /ws/analysis ── WebSocket (分析推送) │
│  ↓                                  │
│  现有 LangGraph 多 Agent 系统         │
│  (Router → Flows → Agents → APIs)   │
└─────────────────────────────────────┘
```

**设计原则**：
- 前端不直接调用 CSQAQ 外部 API，所有数据通过后端中转
- WebSocket 只做分析任务的实时推送（进度 + 结果），普通数据查询走 REST
- 后端 FastAPI 层是薄适配层，核心逻辑保持在现有 LangGraph 系统中

## 3. Pages & Routing

### 3.1 全局布局 (AppLayout)

所有页面共享：
- **顶部导航栏**：Logo + 页面 tabs (首页/单品/大盘/发现/存世量/收藏) + 全局搜索栏 + 用户头像
- **内容区域**：路由页面内容
- **AI 对话侧边栏**：右侧可折叠，输入任意查询触发 WebSocket 分析

### 3.2 路由表

| 路径 | 页面 | 说明 | 鉴权 |
|------|------|------|------|
| `/` | Dashboard | 市场概览、热门饰品、指数卡片 | 公开 |
| `/item/:id` | 单品分析 | K线、技指、价格、存世量、AI建议 | 公开 |
| `/market` | 大盘行情 | 指数走势、涨跌分布、板块热度 | 公开 |
| `/scout` | 发现机会 | 排行榜、推荐、捡漏 | 公开 |
| `/inventory/:id` | 存世量分析 | 趋势图、信号检测、庄家行为判断 | 公开 |
| `/favorites` | 我的收藏 | 收藏列表、查询历史、价格提醒 | 需登录 |
| `/profile` | 用户中心 | 个人设置、订阅管理 | 需登录 |
| `/login` | 登录/注册 | JWT 认证 | 公开 |

### 3.3 关键交互

- **全局搜索栏**：输入饰品名 → 下拉联想 (search_suggest API) → 点击跳转 `/item/:id`
- **AI 对话侧边栏**：右侧可展开，输入任意查询 → WebSocket 推送分析进度 → 流式显示结果，可追问
- **高风险确认**：`risk_level=high` 时弹出确认弹窗，用户点确认才展示 `action_detail`
- **收藏 & 历史**：单品页一键收藏，查询历史自动记录

## 4. WebSocket & Data Flow

### 4.1 消息协议

```typescript
// 客户端 → 服务端
type ClientMessage =
  | { type: "auth"; payload: { token: string } }           // 连接后首条消息认证
  | { type: "query"; payload: { text: string } }
  | { type: "cancel"; payload: { task_id: string } }

// 服务端 → 客户端
type ServerMessage =
  | { type: "auth_ok" }
  | { type: "auth_error"; message: string }
  | { type: "task_started"; task_id: string }
  | { type: "progress"; task_id: string; step: string; message: string }
  | { type: "result"; task_id: string; payload: AnalysisResult }
  | { type: "error"; task_id: string; message: string }

// 扩展的分析结果（比 RunQueryResult 多了 intent + contexts）
interface AnalysisResult {
  intent: string;                    // "item_query" | "market_query" | "scout_query" | "inventory_query"
  summary: string;
  action_detail: string;
  risk_level: string;                // "low" | "medium" | "high"
  requires_confirmation: boolean;
  contexts: {
    item?: object;                   // 价格、指标、K线数据
    market?: object;                 // 大盘数据
    scout?: object;                  // 排行数据
    inventory?: string;              // 存世量分析
  };
}
```

### 4.2 分析流程

```
用户输入查询
  → 前端发送 { type: "query", payload: { text: "AK红线能入吗" } }
  → 后端返回 { type: "task_started", task_id: "..." }
  → 推送进度 { step: "routing", message: "正在分析意图..." }
  → 推送进度 { step: "fetching", message: "正在获取行情数据..." }
  → 推送进度 { step: "analyzing", message: "正在进行技术分析..." }
  → 推送进度 { step: "advising", message: "正在生成投资建议..." }
  → 推送结果 { type: "result", payload: AnalysisResult }
```

### 4.2.1 进度推送实现 (run_query_with_progress)

当前 `run_query` 使用 `router_flow.ainvoke()` 一次性返回结果。为支持进度推送，改用 LangGraph 的 `astream_events(version="v2")` API：

```python
# 核心思路：将 LangGraph node 名称映射为用户友好的进度消息
NODE_PROGRESS_MAP = {
    "router": ("routing", "正在分析意图..."),
    "prepare_queries": ("fetching", "正在获取行情数据..."),
    "run_parallel": ("analyzing", "正在并行分析（行情+大盘+排行+存世量）..."),
    "advise": ("advising", "正在生成投资建议..."),
    # market_flow / scout_flow / inventory_flow 有各自的 node 映射
}

async def run_query_with_progress(app, query):
    router_flow = app.get_router_flow()  # 启动时预编译，复用
    async for event in router_flow.astream_events(input_state, version="v2"):
        if event["event"] == "on_chain_start" and event["name"] in NODE_PROGRESS_MAP:
            step, message = NODE_PROGRESS_MAP[event["name"]]
            yield ProgressStep(name=step, message=message)
    # 最终 result 从 astream_events 的 on_chain_end 中提取
```

**并行分支处理**：`run_parallel` 内部 4 路 `asyncio.gather` 的子进度不细分，统一报告为 "正在并行分析..."。如果需要更细粒度，可在后续版本中为每个分支注册独立的回调。

**取消任务**：通过 `asyncio.Task.cancel()` 取消运行中的 `astream_events` 协程。LangGraph 的 async 节点会收到 `CancelledError`，已有的 try/except 容错机制会正常处理。v1 阶段取消的粒度是整个任务，不支持单分支取消。

### 4.3 状态管理分工

| 层 | 工具 | 职责 |
|----|------|------|
| UI 状态 | Zustand | 主题、侧边栏开关、当前活跃查询、进度步骤 |
| 服务端数据缓存 | React Query | 饰品搜索联想、饰品详情、市场首页、排行榜 |
| 实时分析 | useWebSocket hook | WebSocket 连接管理、消息分发、重连逻辑 |
| 用户数据 | Zustand + React Query | JWT token、用户信息、收藏列表 |

### 4.4 重连策略

断线后指数退避重连（1s → 2s → 4s → 8s → 最大 30s），重连成功后自动恢复进行中的任务状态。

## 5. Frontend Directory Structure

```
csqaq-web/
├── public/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts              # axios 实例 (baseURL, interceptors, JWT)
│   │   ├── ws.ts                  # WebSocket 连接管理
│   │   └── endpoints/
│   │       ├── item.ts
│   │       ├── market.ts
│   │       ├── scout.ts
│   │       ├── inventory.ts
│   │       └── auth.ts
│   ├── hooks/
│   │   ├── useWebSocket.ts        # WS 连接 + 重连 + 消息分发
│   │   ├── useAnalysis.ts         # 封装查询 → 进度 → 结果
│   │   └── useAuth.ts             # JWT 认证状态
│   ├── stores/
│   │   ├── uiStore.ts             # 主题、侧边栏、全局搜索状态
│   │   ├── analysisStore.ts       # 当前分析任务、进度、结果
│   │   └── authStore.ts           # 用户信息、token
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── ItemDetail/
│   │   ├── Market/
│   │   ├── Scout/
│   │   ├── Inventory/
│   │   ├── Favorites/
│   │   ├── Profile/
│   │   └── Login/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx      # 全局壳
│   │   │   ├── TopNav.tsx
│   │   │   ├── SearchBar.tsx      # 搜索栏 + 联想下拉
│   │   │   └── AISidebar.tsx      # AI 对话侧边栏
│   │   ├── charts/
│   │   │   ├── KlineChart.tsx     # K 线图
│   │   │   ├── PriceChart.tsx     # 价格走势
│   │   │   ├── InventoryChart.tsx # 存世量趋势
│   │   │   └── MarketHeatmap.tsx  # 涨跌热力图
│   │   ├── analysis/
│   │   │   ├── AnalysisCard.tsx   # 分析结果卡片
│   │   │   ├── ProgressSteps.tsx  # 分析进度条
│   │   │   └── RiskBadge.tsx      # 风险等级标签
│   │   └── common/
│   │       ├── ItemCard.tsx       # 饰品卡片
│   │       ├── ConfirmModal.tsx   # 高风险确认弹窗
│   │       └── FavoriteButton.tsx
│   ├── styles/
│   │   └── theme.ts               # Ant Design 暗色主题定制
│   └── utils/
│       ├── format.ts              # 价格/百分比/日期格式化
│       └── constants.ts
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

**组件设计原则**：
- 页面组件 (`pages/`) 负责数据获取和状态编排，不含样式逻辑
- 通用组件 (`components/`) 纯展示 + 交互，通过 props 接收数据
- 图表组件 (`charts/`) 封装 ECharts 实例，暴露统一的 `data` prop 接口
- Hooks 封装所有副作用（API 调用、WebSocket、认证）

## 6. Backend API Layer (FastAPI)

在现有 CSQAQ 仓库中新增 FastAPI 服务层。

### 6.1 目录结构

```
src/csqaq/api/
├── cli.py              # 已有 Typer CLI
├── server.py           # FastAPI app + uvicorn 启动
├── routes/
│   ├── item.py         # GET /api/v1/items/search, GET /api/v1/items/:id
│   ├── market.py       # GET /api/v1/market/overview
│   ├── scout.py        # GET /api/v1/scout/rankings
│   ├── inventory.py    # GET /api/v1/items/:id/inventory
│   ├── auth.py         # POST /api/v1/auth/login, /register, /refresh
│   └── favorites.py    # GET/POST/DELETE /api/v1/favorites
├── ws/
│   └── analysis.py     # WebSocket /ws/analysis
├── deps.py             # FastAPI 依赖注入 (get_app, get_current_user)
└── middleware.py        # CORS, rate limiting, error handling
```

### 6.2 REST 端点

| 方法 | 路径 | 说明 | 数据来源 |
|------|------|------|---------|
| GET | `/api/v1/items/search?q=AK红线` | 搜索联想 | ItemAPI.search_suggest |
| GET | `/api/v1/items/:id` | 饰品详情 | ItemAPI.get_item_detail |
| GET | `/api/v1/items/:id/chart` | 价格走势 | ItemAPI.get_item_chart |
| GET | `/api/v1/items/:id/kline` | K线数据 | ItemAPI.get_item_kline |
| GET | `/api/v1/items/:id/inventory` | 存世量数据 | ItemAPI.get_item_statistic |
| GET | `/api/v1/market/overview` | 大盘概览 | MarketAPI.get_home_data |
| GET | `/api/v1/market/sub/:id` | 子指数详情 | MarketAPI.get_sub_data |
| GET | `/api/v1/market/index-kline` | 指数K线 | MarketAPI.get_index_kline |
| GET | `/api/v1/scout/rankings` | 排行榜 | RankAPI.get_rank_list |
| GET | `/api/v1/scout/items` | 排行分页列表 | RankAPI.get_page_list |
| GET | `/api/v1/scout/volume` | 成交量数据 | VolAPI.get_vol_data |
| WS | `/ws/analysis` | 分析查询推送 | run_query_with_progress |

### 6.3 WebSocket Handler

```python
async def analysis_handler(websocket, app):
    # 1. 可选认证：首条消息如果是 auth 类型则验证 token
    #    未认证用户也可使用，但受更严格的 rate limit
    authenticated_user = None

    while True:
        msg = await websocket.receive_json()

        if msg["type"] == "auth":
            authenticated_user = verify_token(msg["payload"]["token"])
            await websocket.send_json({"type": "auth_ok"} if authenticated_user
                                       else {"type": "auth_error", "message": "invalid token"})
            continue

        if msg["type"] == "query":
            task_id = str(uuid4())
            task = asyncio.create_task(
                _run_analysis(websocket, app, task_id, msg["payload"]["text"])
            )
            active_tasks[task_id] = task

        elif msg["type"] == "cancel":
            task = active_tasks.pop(msg["payload"]["task_id"], None)
            if task:
                task.cancel()

async def _run_analysis(websocket, app, task_id, query):
    await websocket.send_json({"type": "task_started", "task_id": task_id})
    try:
        async for step in run_query_with_progress(app, query):
            await websocket.send_json({
                "type": "progress", "task_id": task_id,
                "step": step.name, "message": step.message
            })
        # 最终结果从 stream 末尾提取
        await websocket.send_json({"type": "result", "task_id": task_id, "payload": result})
    except asyncio.CancelledError:
        await websocket.send_json({"type": "error", "task_id": task_id, "message": "任务已取消"})
    except Exception as e:
        await websocket.send_json({"type": "error", "task_id": task_id, "message": str(e)})
```

### 6.4 并发控制

- **每连接并发限制**：单个 WebSocket 连接最多 1 个进行中的分析任务（排队后续请求）
- **全局并发限制**：服务器最多同时运行 N 个分析任务（N 由配置决定，默认 10），超出返回排队提示
- **未认证用户限流**：IP 级别 rate limit，每分钟最多 3 次查询
- **认证用户限流**：用户级别，每分钟最多 10 次查询

### 6.5 Graph 复用

`router_flow` 在 `App.init()` 时预编译一次，所有请求复用同一个 compiled graph 实例。当前 `run_query` 每次调用 `build_router_flow()` 的模式需要重构为启动时构建。

### 6.6 关键点

- REST 端点是对现有 API 的直接包装，一层透传
- WebSocket 端点使用 `astream_events` 推送进度
- FastAPI `Depends()` 注入 `App` 容器，复用现有 API 客户端和模型工厂
- CORS 白名单允许前端域名
- 生产环境强制 HTTPS/WSS

## 7. Auth & User System

### 7.1 认证流程 (JWT)

```
POST /api/v1/auth/login { username, password }
  → { access_token (30min), refresh_token (7d) }
  → refresh_token 通过 Set-Cookie (httpOnly, Secure, SameSite=Strict) 下发

前端存储:
  - access_token → 内存 (Zustand authStore)
  - refresh_token → httpOnly cookie（JS 不可读）

REST 请求:
  - Authorization: Bearer <access_token>

WebSocket 认证:
  - 连接后发送首条消息 { type: "auth", payload: { token: "<access_token>" } }
  - 服务端验证后回复 { type: "auth_ok" } 或 { type: "auth_error" }
  - 不在 URL query 中传 token（避免日志泄露）

Token 过期:
  - axios interceptor 捕获 401 → POST /api/v1/auth/refresh (cookie 自动携带) → 重试
  - refresh 也过期 → 跳转登录页
```

### 7.2 数据模型

复用并扩展现有数据库。已有模型 `Watchlist` 承担收藏功能（含 `alert_threshold_pct`），新增 `User` 和 `QueryHistory`。使用 Alembic 管理数据库迁移。

```
User (新增)
├── id: int (PK, autoincrement)
├── username: str (unique)
├── email: str (unique)
├── hashed_password: str
├── created_at: datetime
└── is_active: bool

Watchlist (已有，扩展关联)
├── id: int (PK)
├── user_id: int (FK → User，当前可空，server 模式关联 User)
├── good_id: int
├── name: str
├── market_hash_name: str
├── added_at: datetime
├── alert_threshold_pct: float
└── notes: str

QueryHistory (新增)
├── id: int (PK, autoincrement)
├── user_id: int (FK → User, nullable — 未登录用户不记录)
├── query_text: str
├── intent: str
├── summary: str | None
├── risk_level: str | None
├── created_at: datetime
```

**数据库迁移策略**：引入 Alembic，初始迁移脚本生成现有表结构基线，后续迁移添加 `User`、`QueryHistory` 表。`Watchlist.user_id` 的外键约束在 server 模式下启用。

### 7.3 权限策略

- 公开页面（Dashboard、单品、大盘、Scout、存世量）不需要登录
- AI 分析查询不需要登录（降低使用门槛），但受 IP 级 rate limit（3次/分钟）
- 登录用户 AI 分析 rate limit 放宽至 10次/分钟
- 收藏、历史记录、个人设置需要登录
- v1 不做会员/限额系统，后续可扩展

### 7.4 安全要求

- 生产环境 `secret_key` 必须从环境变量注入，启动时校验非默认值
- 全链路 HTTPS/WSS（生产环境强制）
- refresh_token cookie 设置 `SameSite=Strict` 防 CSRF
- `QueryHistory.query_text` 存储前做 XSS sanitize（去除 HTML 标签）
- 输入长度限制：query 最长 200 字符

## 8. Error Handling

### 8.1 前端

- React Query 自带重试机制（默认 3 次），失败后显示 Ant Design 的错误提示
- WebSocket 断线自动重连，进行中的分析任务展示"连接中断，正在重连..."
- API 返回 401 → 自动刷新 token → 重试；刷新也失败 → 跳转登录
- 全局 ErrorBoundary 兜底未捕获的渲染错误

### 8.2 后端

- FastAPI 异常处理中间件统一返回 `{ error: string, detail?: any }` 格式
- WebSocket 异常通过 `{ type: "error", task_id, message }` 推送给前端
- LangGraph 流程内部错误（某个分支失败）不影响其他分支，已有容错机制

## 9. Responsive Design

- **桌面优先**：主要用户场景是 PC 端看行情分析，桌面体验优先
- **断点策略**：Ant Design 默认断点（xs: 480, sm: 576, md: 768, lg: 992, xl: 1200, xxl: 1600）
- **移动端适配**：
  - 顶部导航收缩为 hamburger 菜单（md 以下）
  - AI 侧边栏在移动端变为全屏抽屉
  - 图表组件自适应宽度，触摸友好
  - Scout 排行榜改为卡片列表（非表格）
- **v1 目标**：桌面端完整体验 + 移动端基本可用，不要求移动端完美

## 10. Testing Strategy

### 9.1 前端

- **单元测试**：Vitest + React Testing Library，测试 hooks、stores、工具函数
- **组件测试**：关键交互组件（SearchBar、AISidebar、ConfirmModal）
- **E2E 测试**：后续引入 Playwright（v1 可选）

### 9.2 后端 API 层

- **路由测试**：httpx AsyncClient + pytest-asyncio 测试 FastAPI 端点
- **WebSocket 测试**：httpx WebSocket 测试连接、消息推送
- **集成测试**：mock LangGraph 流程，测试端到端 WebSocket 流程

## 11. Scope: v1 vs. Later

**v1 包含**：
- 全部 7 个核心页面（Dashboard、单品、大盘、Scout、存世量、收藏、用户中心）
- FastAPI REST + WebSocket 后端 API 层
- JWT 认证系统
- 暗色主题
- 桌面端完整 + 移动端基本可用

**v1 不包含（后续迭代）**：
- 会员/限额系统
- PWA / Service Worker 离线支持
- 国际化 (i18n)
- Playwright E2E 测试
- Docker 部署配置
- 亮色主题切换
