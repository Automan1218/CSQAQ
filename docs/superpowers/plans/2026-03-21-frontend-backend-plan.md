# CSQAQ Frontend + Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade React frontend and FastAPI backend API layer for the CSQAQ CS2 skin investment analysis system, enabling web-based access to all existing LangGraph multi-agent capabilities.

**Architecture:** Frontend is a separate repository (csqaq-web) using React 18 + TypeScript + Vite + Ant Design 5 (dark theme) + ECharts. Backend API layer lives in the existing CSQAQ repo as a FastAPI server at `src/csqaq/api/`, acting as a thin adapter over existing LangGraph flows and API clients. WebSocket handles real-time AI analysis streaming; REST handles data queries. JWT authentication with httpOnly refresh cookies.

**Tech Stack:** Python 3.11+ / FastAPI / uvicorn / python-jose / passlib / Alembic (backend); React 18 / TypeScript / Vite / Ant Design 5 / ECharts 5 / Zustand / React Query / Axios (frontend)

**Spec:** `docs/superpowers/specs/2026-03-21-frontend-design.md`

---

## File Structure

### Backend — New Files (in existing CSQAQ repo)

| File | Responsibility |
|------|---------------|
| `src/csqaq/api/server.py` | FastAPI app factory, lifespan, uvicorn launcher |
| `src/csqaq/api/deps.py` | Dependency injection: `get_app`, `get_current_user`, `get_optional_user` |
| `src/csqaq/api/middleware.py` | CORS, error handling middleware |
| `src/csqaq/api/routes/__init__.py` | Route module init |
| `src/csqaq/api/routes/item.py` | Item REST endpoints |
| `src/csqaq/api/routes/market.py` | Market REST endpoints |
| `src/csqaq/api/routes/scout.py` | Scout REST endpoints |
| `src/csqaq/api/routes/inventory.py` | Inventory REST endpoints |
| `src/csqaq/api/routes/auth.py` | Auth endpoints (login/register/refresh) |
| `src/csqaq/api/routes/favorites.py` | Favorites CRUD endpoints |
| `src/csqaq/api/routes/history.py` | Query history endpoints |
| `src/csqaq/api/ws/__init__.py` | WebSocket module init |
| `src/csqaq/api/ws/analysis.py` | WebSocket analysis handler with progress streaming |
| `src/csqaq/api/ws/progress.py` | `run_query_with_progress` using `astream_events` |
| `src/csqaq/infrastructure/database/models.py` | Extended: add `User`, `QueryHistory` models |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Alembic environment |
| `alembic/versions/001_baseline.py` | Baseline migration |
| `alembic/versions/002_add_user_and_history.py` | User + QueryHistory tables |
| `tests/test_api/__init__.py` | API test module |
| `tests/test_api/conftest.py` | API test fixtures (AsyncClient, test app) |
| `tests/test_api/test_health.py` | Health endpoint test |
| `tests/test_api/test_item_routes.py` | Item route tests |
| `tests/test_api/test_market_routes.py` | Market route tests |
| `tests/test_api/test_scout_routes.py` | Scout route tests |
| `tests/test_api/test_auth.py` | Auth route tests |
| `tests/test_api/test_favorites.py` | Favorites route tests |
| `tests/test_api/test_ws.py` | WebSocket handler tests |

### Frontend — New Repo (csqaq-web)

| File | Responsibility |
|------|---------------|
| `package.json` | Dependencies and scripts |
| `vite.config.ts` | Vite configuration with proxy |
| `tsconfig.json` | TypeScript configuration |
| `index.html` | HTML entry point |
| `src/main.tsx` | React entry point |
| `src/App.tsx` | Root component with router |
| `src/vite-env.d.ts` | Vite type declarations |
| `src/styles/theme.ts` | Ant Design dark theme tokens |
| `src/utils/constants.ts` | API base URL, WS URL constants |
| `src/utils/format.ts` | Price/percentage/date formatters |
| `src/api/client.ts` | Axios instance with interceptors |
| `src/api/endpoints/item.ts` | Item API functions |
| `src/api/endpoints/market.ts` | Market API functions |
| `src/api/endpoints/scout.ts` | Scout API functions |
| `src/api/endpoints/inventory.ts` | Inventory API functions |
| `src/api/endpoints/auth.ts` | Auth API functions |
| `src/types/index.ts` | Shared TypeScript interfaces |
| `src/stores/uiStore.ts` | UI state (sidebar, theme) |
| `src/stores/analysisStore.ts` | Analysis task state |
| `src/stores/authStore.ts` | Auth token + user state |
| `src/hooks/useWebSocket.ts` | WS connection + reconnect |
| `src/hooks/useAnalysis.ts` | Analysis query orchestration |
| `src/hooks/useAuth.ts` | Auth state hook |
| `src/components/layout/AppLayout.tsx` | Global shell layout |
| `src/components/layout/TopNav.tsx` | Navigation bar |
| `src/components/layout/SearchBar.tsx` | Global search with autocomplete |
| `src/components/layout/AISidebar.tsx` | AI chat sidebar |
| `src/components/charts/KlineChart.tsx` | ECharts K-line |
| `src/components/charts/PriceChart.tsx` | ECharts price line |
| `src/components/charts/InventoryChart.tsx` | ECharts inventory trend |
| `src/components/charts/MarketHeatmap.tsx` | Market heatmap |
| `src/components/analysis/AnalysisCard.tsx` | Analysis result card |
| `src/components/analysis/ProgressSteps.tsx` | Progress indicator |
| `src/components/analysis/RiskBadge.tsx` | Risk level badge |
| `src/components/common/ItemCard.tsx` | Item display card |
| `src/components/common/ConfirmModal.tsx` | High-risk confirmation |
| `src/components/common/FavoriteButton.tsx` | Favorite toggle |
| `src/pages/Dashboard/index.tsx` | Dashboard page |
| `src/pages/ItemDetail/index.tsx` | Item detail page |
| `src/pages/Market/index.tsx` | Market overview page |
| `src/pages/Scout/index.tsx` | Scout rankings page |
| `src/pages/Inventory/index.tsx` | Inventory analysis page |
| `src/pages/Favorites/index.tsx` | Favorites page |
| `src/pages/Profile/index.tsx` | User profile page |
| `src/pages/Login/index.tsx` | Login/register page |

### Modified Files (in existing CSQAQ repo)

| File | Change |
|------|--------|
| `src/csqaq/main.py` | Add `get_router_flow()` method to `App`, pre-compile at init |
| `src/csqaq/infrastructure/database/models.py` | Add `User`, `QueryHistory` models |
| `src/csqaq/infrastructure/database/connection.py` | No change (Base.metadata.create_all handles new models) |
| `pyproject.toml` | Add `alembic` to `[project.optional-dependencies] server` |

---

## Phase 1: Foundation

### Task 1: FastAPI Server Scaffold + Health Endpoint

**Files:**
- Create: `src/csqaq/api/server.py`
- Create: `src/csqaq/api/deps.py`
- Create: `src/csqaq/api/middleware.py`
- Create: `src/csqaq/api/routes/__init__.py`
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/conftest.py`
- Create: `tests/test_api/test_health.py`
- Modify: `src/csqaq/main.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing test for health endpoint**

Create `tests/test_api/__init__.py` (empty) and `tests/test_api/conftest.py`:

```python
# tests/test_api/conftest.py
"""Shared fixtures for API route tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from csqaq.config import Settings
from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, IndexKlineBar, SubData
from csqaq.infrastructure.csqaq_client.rank_schemas import PageListItem, RankItem
from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    KlineBar,
    SuggestItem,
)
from csqaq.infrastructure.csqaq_client.vol_schemas import VolItem

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _build_mock_app():
    """Build a mock App with all API clients mocked."""
    from csqaq.main import App

    settings = Settings(
        csqaq_api_token="test-token",
        openai_api_key="test-key",
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-key-for-jwt-signing-min-32-chars",
    )
    app = App(settings)

    # Mock all API clients
    app._item_api = AsyncMock()
    app._market_api = AsyncMock()
    app._rank_api = AsyncMock()
    app._vol_api = AsyncMock()
    app._model_factory = MagicMock()
    app._database = AsyncMock()

    # Wire fixture data
    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    app._item_api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    app._item_api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    app._item_api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
    app._item_api.get_item_kline.return_value = [KlineBar.model_validate(k) for k in kline_data]

    stat_data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
    app._item_api.get_item_statistic.return_value = [InventoryStat.model_validate(s) for s in stat_data]

    home = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    app._market_api.get_home_data.return_value = HomeData.model_validate(home)

    sub = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    app._market_api.get_sub_data.return_value = SubData.model_validate(sub)

    index_kline = json.loads((FIXTURES / "index_kline_response.json").read_text(encoding="utf-8"))
    app._market_api.get_index_kline.return_value = [IndexKlineBar.model_validate(k) for k in index_kline]

    rank = json.loads((FIXTURES / "rank_list_response.json").read_text(encoding="utf-8"))
    app._rank_api.get_rank_list.return_value = [RankItem.model_validate(i) for i in rank["data"]]

    page = json.loads((FIXTURES / "page_list_response.json").read_text(encoding="utf-8"))
    app._rank_api.get_page_list.return_value = [PageListItem.model_validate(i) for i in page["data"]]

    vol = json.loads((FIXTURES / "vol_data_response.json").read_text(encoding="utf-8"))
    app._vol_api.get_vol_data.return_value = [VolItem.model_validate(i) for i in vol]

    return app


@pytest.fixture
def mock_app():
    """A fully mocked App instance for API testing."""
    return _build_mock_app()


@pytest.fixture
async def client(mock_app):
    """httpx AsyncClient bound to the FastAPI test app."""
    from csqaq.api.server import create_app

    fastapi_app = create_app(mock_app)
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

Create `tests/test_api/test_health.py`:

```python
# tests/test_api/test_health.py
import pytest


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_includes_version(self, client):
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api/test_health.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'csqaq.api.server'`

- [ ] **Step 3: Update pyproject.toml with alembic dependency**

Add `"alembic>=1.13"` to the `server` optional dependencies list in `pyproject.toml`:

```toml
[project.optional-dependencies]
server = [
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "websockets>=12.0",
    "redis>=5.0",
    "asyncpg>=0.29",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "cryptography>=43.0",
    "alembic>=1.13",
]
```

- [ ] **Step 4: Implement server.py**

Create `src/csqaq/api/server.py`:

```python
# src/csqaq/api/server.py
"""FastAPI application factory and uvicorn launcher."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from csqaq.main import App


def create_app(app_container: App | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        app_container: Pre-initialized App instance (for testing).
            If None, creates and initializes one from Settings.
    """

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        nonlocal app_container
        if app_container is None:
            from csqaq.config import Settings
            from csqaq.main import App, setup_logging

            setup_logging()
            settings = Settings(mode="server")
            app_container = App(settings)
            await app_container.init()

        fastapi_app.state.app = app_container
        yield

        if app_container is not None:
            await app_container.close()

    fastapi_app = FastAPI(
        title="CSQAQ API",
        description="CS2 饰品投资分析系统 API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "https://csqaq.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from csqaq.api.routes import register_routes

    register_routes(fastapi_app)

    return fastapi_app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Launch uvicorn server."""
    import uvicorn

    uvicorn.run(
        "csqaq.api.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )
```

- [ ] **Step 5: Implement deps.py**

Create `src/csqaq/api/deps.py`:

```python
# src/csqaq/api/deps.py
"""FastAPI dependency injection."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

if TYPE_CHECKING:
    from csqaq.main import App

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app(request: Request) -> App:
    """Get the App container from FastAPI app state."""
    return request.app.state.app


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    app: App = Depends(get_app),
) -> dict:
    """Require a valid JWT token. Returns user payload dict.

    Raises HTTPException 401 if token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from csqaq.api.routes.auth import verify_access_token

    payload = verify_access_token(credentials.credentials, app.settings.secret_key)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    app: App = Depends(get_app),
) -> dict | None:
    """Optionally extract user from JWT. Returns None if no token or invalid."""
    if credentials is None:
        return None
    from csqaq.api.routes.auth import verify_access_token

    return verify_access_token(credentials.credentials, app.settings.secret_key)
```

- [ ] **Step 6: Implement middleware.py**

Create `src/csqaq/api/middleware.py`:

```python
# src/csqaq/api/middleware.py
"""Error handling and middleware utilities."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "服务器内部错误", "detail": str(exc)},
        )
```

- [ ] **Step 7: Implement routes/__init__.py with health endpoint**

Create `src/csqaq/api/routes/__init__.py`:

```python
# src/csqaq/api/routes/__init__.py
"""Route registration."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from csqaq.api.middleware import register_error_handlers

    register_error_handlers(app)

    root = APIRouter(prefix="/api/v1")

    @root.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    app.include_router(root)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python -m pytest tests/test_api/test_health.py -v`
Expected: 2 passed

- [ ] **Step 9: Commit**

```bash
git add src/csqaq/api/server.py src/csqaq/api/deps.py src/csqaq/api/middleware.py src/csqaq/api/routes/__init__.py tests/test_api/__init__.py tests/test_api/conftest.py tests/test_api/test_health.py pyproject.toml
git commit -m "feat: add FastAPI server scaffold with health endpoint"
```

---

### Task 2: Frontend Project Scaffold

**Files:**
- Create: `d:/program/PythonWorkSpace/csqaq-web/` (new repo)
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`
- Create: `src/main.tsx`, `src/App.tsx`, `src/vite-env.d.ts`
- Create: `src/styles/theme.ts`
- Create: `.gitignore`, `.eslintrc.cjs`

- [ ] **Step 1: Initialize project**

```bash
cd d:/program/PythonWorkSpace/
mkdir csqaq-web && cd csqaq-web
npm create vite@latest . -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm install antd @ant-design/icons echarts echarts-for-react zustand @tanstack/react-query react-router-dom axios
npm install -D @types/react @types/react-dom vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 3: Configure vite.config.ts**

Replace `vite.config.ts`:

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
```

- [ ] **Step 4: Create Ant Design dark theme**

Create `src/styles/theme.ts`:

```typescript
// src/styles/theme.ts
import type { ThemeConfig } from 'antd';

export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1668dc',
    colorBgContainer: '#141414',
    colorBgElevated: '#1f1f1f',
    colorBgLayout: '#000000',
    colorText: 'rgba(255, 255, 255, 0.85)',
    colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
    borderRadius: 6,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  components: {
    Layout: {
      headerBg: '#141414',
      bodyBg: '#000000',
      siderBg: '#141414',
    },
    Menu: {
      darkItemBg: '#141414',
    },
  },
};
```

- [ ] **Step 5: Create App.tsx with router shell**

Create `src/App.tsx`:

```tsx
// src/App.tsx
import { ConfigProvider, theme, App as AntApp } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { darkTheme } from './styles/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 2,
    },
  },
});

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<div>Dashboard (coming soon)</div>} />
      <Route path="/item/:id" element={<div>Item Detail</div>} />
      <Route path="/market" element={<div>Market</div>} />
      <Route path="/scout" element={<div>Scout</div>} />
      <Route path="/inventory/:id" element={<div>Inventory</div>} />
      <Route path="/favorites" element={<div>Favorites</div>} />
      <Route path="/profile" element={<div>Profile</div>} />
      <Route path="/login" element={<div>Login</div>} />
    </Routes>
  );
}

export default function App() {
  return (
    <ConfigProvider theme={{ ...darkTheme, algorithm: theme.darkAlgorithm }}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  );
}
```

- [ ] **Step 6: Update main.tsx**

Replace `src/main.tsx`:

```tsx
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 7: Create test setup**

Create `src/test/setup.ts`:

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom';
```

- [ ] **Step 8: Verify build**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build
```
Expected: Build succeeds with no errors.

- [ ] **Step 9: Initialize git and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
git init
git add .
git commit -m "feat: scaffold React + TS + Vite + Ant Design dark theme project"
```

---

### Task 3: API Client Layer + Zustand Stores Skeleton

**Files:**
- Create: `src/utils/constants.ts`
- Create: `src/utils/format.ts`
- Create: `src/types/index.ts`
- Create: `src/api/client.ts`
- Create: `src/api/endpoints/item.ts`
- Create: `src/api/endpoints/market.ts`
- Create: `src/api/endpoints/scout.ts`
- Create: `src/api/endpoints/auth.ts`
- Create: `src/stores/uiStore.ts`
- Create: `src/stores/analysisStore.ts`
- Create: `src/stores/authStore.ts`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create TypeScript types matching backend schemas**

Create `src/types/index.ts`:

```typescript
// src/types/index.ts

// === Item types (matches schemas.py) ===
export interface SuggestItem {
  goodId: number;
  goodName: string;
  marketHashName: string;
  imageUrl: string;
}

export interface ItemDetail {
  goodId: number;
  goodName: string;
  marketHashName: string;
  imageUrl: string;
  buffSellPrice: number;
  buffBuyPrice: number;
  steamSellPrice: number;
  yyypSellPrice: number;
  buffSellNum: number;
  buffBuyNum: number;
  steamSellNum: number;
  dailyChangeRate: number;
  weeklyChangeRate: number;
  monthlyChangeRate: number;
  category: string;
  rarity: string;
  exterior: string;
}

export interface ChartPoint {
  timestamp: number;
  price: number;
  volume: number;
}

export interface ChartData {
  goodId: number;
  platform: string;
  period: string;
  points: ChartPoint[];
}

export interface KlineBar {
  timestamp: number;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}

// === Inventory types (matches inventory_schemas.py) ===
export interface InventoryStat {
  statistic: number;
  created_at: string;
}

// === Market types (matches market_schemas.py) ===
export interface SubIndexItem {
  id: number;
  name: string;
  name_key: string;
  img: string;
  market_index: number;
  chg_num: number;
  chg_rate: number;
  open: number;
  close: number;
  high: number;
  low: number;
  updated_at: string;
}

export interface RateData {
  count_positive_1: number;
  count_negative_1: number;
  count_zero_1: number;
  count_positive_7: number;
  count_negative_7: number;
  count_zero_7: number;
  count_positive_15: number;
  count_negative_15: number;
  count_zero_15: number;
  count_positive_30: number;
  count_negative_30: number;
  count_zero_30: number;
  count_positive_90: number;
  count_negative_90: number;
  count_zero_90: number;
  count_positive_180: number;
  count_negative_180: number;
  count_zero_180: number;
}

export interface GreedyStatus {
  level: string;
  label: string;
}

export interface OnlineNumber {
  current_number: number;
  today_peak: number;
  month_peak: number;
  month_player: number;
  same_month_player: number;
  same_time_number: number;
  rate: number;
  same_time_number_week: number;
  rate_week: number;
  created_at: string;
}

export interface HomeData {
  sub_index_data: SubIndexItem[];
  chg_type_data: Record<string, unknown>[];
  chg_price_data: Record<string, unknown>[];
  rate_data: RateData;
  online_number: OnlineNumber;
  greedy_status: GreedyStatus;
  online_chart: Record<string, unknown>[];
  greedy: unknown[];
  alteration: Record<string, unknown>[];
  view_count: Record<string, unknown>[];
  card_price: Record<string, unknown>[];
}

export interface SubIndexCount {
  name: string;
  img: string;
  now: number;
  amplitude: number;
  rate: number;
  max_value: number;
  min_value: number;
  consecutive_days: number;
}

export interface SubData {
  timestamp: number[];
  count: SubIndexCount;
  main_data: number[][];
  hourly_list: number[];
}

export interface IndexKlineBar {
  t: string;
  o: number;
  c: number;
  h: number;
  l: number;
  v: number;
}

// === Rank types (matches rank_schemas.py) ===
export interface RankItem {
  id: number;
  name: string;
  img: string;
  exterior_localized_name: string | null;
  rarity_localized_name: string;
  buff_sell_price: number;
  buff_sell_num: number;
  buff_buy_price: number;
  steam_sell_price: number;
  sell_price_rate_1: number;
  sell_price_rate_7: number;
  sell_price_rate_30: number;
  sell_price_rate_90: number;
  rank_num: number;
}

// === Volume types (matches vol_schemas.py) ===
export interface VolItem {
  id: number;
  good_id: number;
  name: string;
  img: string;
  group: string;
  statistic: number;
  updated_at: string;
  avg_price: number;
  sum_price: number;
  special: number;
}

// === WebSocket types ===
export type ClientMessage =
  | { type: 'auth'; payload: { token: string } }
  | { type: 'query'; payload: { text: string } }
  | { type: 'cancel'; payload: { task_id: string } };

export type ServerMessage =
  | { type: 'auth_ok' }
  | { type: 'auth_error'; message: string }
  | { type: 'task_started'; task_id: string }
  | { type: 'progress'; task_id: string; step: string; message: string }
  | { type: 'result'; task_id: string; payload: AnalysisResult }
  | { type: 'error'; task_id: string; message: string };

export interface AnalysisResult {
  intent: string;
  summary: string;
  action_detail: string;
  risk_level: 'low' | 'medium' | 'high';
  requires_confirmation: boolean;
  contexts: {
    item?: Record<string, unknown>;
    market?: Record<string, unknown>;
    scout?: Record<string, unknown>;
    inventory?: string;
  };
}

// === Auth types ===
export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// === Favorites ===
export interface WatchlistItem {
  id: number;
  good_id: number;
  name: string;
  market_hash_name: string;
  added_at: string;
  alert_threshold_pct: number;
  notes: string;
}

// === Query History ===
export interface QueryHistoryItem {
  id: number;
  query_text: string;
  intent: string;
  summary: string | null;
  risk_level: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Create constants and formatters**

Create `src/utils/constants.ts`:

```typescript
// src/utils/constants.ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}/ws`;

export const QUERY_KEYS = {
  itemSearch: (q: string) => ['items', 'search', q] as const,
  itemDetail: (id: number) => ['items', id, 'detail'] as const,
  itemChart: (id: number, period: string) => ['items', id, 'chart', period] as const,
  itemKline: (id: number, period: string) => ['items', id, 'kline', period] as const,
  itemInventory: (id: number) => ['items', id, 'inventory'] as const,
  marketOverview: () => ['market', 'overview'] as const,
  marketSub: (id: number) => ['market', 'sub', id] as const,
  marketKline: (id: number, period: string) => ['market', 'kline', id, period] as const,
  scoutRankings: (filter: string, page: number) => ['scout', 'rankings', filter, page] as const,
  scoutItems: (page: number) => ['scout', 'items', page] as const,
  scoutVolume: () => ['scout', 'volume'] as const,
  favorites: () => ['favorites'] as const,
  history: () => ['history'] as const,
} as const;
```

Create `src/utils/format.ts`:

```typescript
// src/utils/format.ts

/** Format price in CNY, e.g. "85.50" or "1,234.56" */
export function formatPrice(price: number): string {
  return price.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Format percentage, e.g. "+1.25%" or "-2.30%" */
export function formatPercent(rate: number): string {
  const sign = rate > 0 ? '+' : '';
  return `${sign}${rate.toFixed(2)}%`;
}

/** Format date from ISO string or timestamp */
export function formatDate(input: string | number): string {
  const date = typeof input === 'number' ? new Date(input * 1000) : new Date(input);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/** Format datetime with time */
export function formatDateTime(input: string | number): string {
  const date = typeof input === 'number' ? new Date(input * 1000) : new Date(input);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Color for price change: green for positive, red for negative */
export function changeColor(rate: number): string {
  if (rate > 0) return '#52c41a';
  if (rate < 0) return '#ff4d4f';
  return 'rgba(255, 255, 255, 0.45)';
}
```

- [ ] **Step 3: Create axios client with JWT interceptor**

Create `src/api/client.ts`:

```typescript
// src/api/client.ts
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Lazy accessor to break circular import (authStore imports apiClient)
let getAuthStore: (() => import('../stores/authStore').AuthState) | null = null;

export function setAuthStoreAccessor(accessor: () => import('../stores/authStore').AuthState) {
  getAuthStore = accessor;
}

// Request interceptor: attach access token
apiClient.interceptors.request.use((config) => {
  const token = getAuthStore?.()?.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 + token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const store = getAuthStore?.();
        const refreshed = await store?.refreshToken();
        if (refreshed) {
          const token = getAuthStore?.()?.accessToken;
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }
      } catch {
        // refresh failed
      }
      getAuthStore?.()?.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default apiClient;
```

> **Note:** In `authStore.ts`, call `setAuthStoreAccessor(() => useAuthStore.getState())` at module init to wire up the accessor. This avoids ESM circular import issues.

- [ ] **Step 4: Create API endpoint modules**

Create `src/api/endpoints/item.ts`:

```typescript
// src/api/endpoints/item.ts
import apiClient from '../client';
import type { SuggestItem, ItemDetail, ChartData, KlineBar, InventoryStat } from '../../types';

export async function searchItems(q: string): Promise<SuggestItem[]> {
  const { data } = await apiClient.get<SuggestItem[]>('/items/search', { params: { q } });
  return data;
}

export async function getItemDetail(id: number): Promise<ItemDetail> {
  const { data } = await apiClient.get<ItemDetail>(`/items/${id}`);
  return data;
}

export async function getItemChart(id: number, period = '30d', platform = 'buff'): Promise<ChartData> {
  const { data } = await apiClient.get<ChartData>(`/items/${id}/chart`, { params: { period, platform } });
  return data;
}

export async function getItemKline(id: number, period = '30d', platform = 'buff'): Promise<KlineBar[]> {
  const { data } = await apiClient.get<KlineBar[]>(`/items/${id}/kline`, { params: { period, platform } });
  return data;
}

export async function getItemInventory(id: number): Promise<InventoryStat[]> {
  const { data } = await apiClient.get<InventoryStat[]>(`/items/${id}/inventory`);
  return data;
}
```

Create `src/api/endpoints/market.ts`:

```typescript
// src/api/endpoints/market.ts
import apiClient from '../client';
import type { HomeData, SubData, IndexKlineBar } from '../../types';

export async function getMarketOverview(): Promise<HomeData> {
  const { data } = await apiClient.get<HomeData>('/market/overview');
  return data;
}

export async function getSubData(id: number, type = 'daily'): Promise<SubData> {
  const { data } = await apiClient.get<SubData>(`/market/sub/${id}`, { params: { type } });
  return data;
}

export async function getIndexKline(id: number, period = '1day'): Promise<IndexKlineBar[]> {
  const { data } = await apiClient.get<IndexKlineBar[]>('/market/index-kline', { params: { id, period } });
  return data;
}
```

Create `src/api/endpoints/scout.ts`:

```typescript
// src/api/endpoints/scout.ts
import apiClient from '../client';
import type { RankItem, VolItem } from '../../types';

export async function getRankings(
  filter: Record<string, unknown> = {},
  page = 1,
  size = 20,
): Promise<RankItem[]> {
  const { data } = await apiClient.post<RankItem[]>('/scout/rankings', { filter, page, size });
  return data;
}

export async function getScoutItems(page = 1, size = 20): Promise<RankItem[]> {
  const { data } = await apiClient.get<RankItem[]>('/scout/items', { params: { page, size } });
  return data;
}

export async function getVolumeData(): Promise<VolItem[]> {
  const { data } = await apiClient.get<VolItem[]>('/scout/volume');
  return data;
}
```

Create `src/api/endpoints/auth.ts`:

```typescript
// src/api/endpoints/auth.ts
import apiClient from '../client';
import type { AuthResponse, User } from '../../types';

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', { username, password });
  return data;
}

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', { username, email, password });
  return data;
}

export async function refreshAccessToken(): Promise<{ access_token: string }> {
  const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
  return data;
}

export async function getProfile(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
}
```

Create `src/api/endpoints/inventory.ts`:

```typescript
// src/api/endpoints/inventory.ts
import apiClient from '../client';
import type { InventoryStat } from '../../types';

export async function getItemInventory(id: number): Promise<InventoryStat[]> {
  const { data } = await apiClient.get<InventoryStat[]>(`/items/${id}/inventory`);
  return data;
}
```

Create `src/api/endpoints/favorites.ts`:

```typescript
// src/api/endpoints/favorites.ts
import apiClient from '../client';

export interface FavoriteItem {
  id: number;
  good_id: number;
  name: string;
  market_hash_name: string;
  added_at: string;
  notes: string;
}

export async function getFavorites(): Promise<FavoriteItem[]> {
  const { data } = await apiClient.get<FavoriteItem[]>('/favorites');
  return data;
}

export async function addFavorite(goodId: number, name: string): Promise<FavoriteItem> {
  const { data } = await apiClient.post<FavoriteItem>('/favorites', { good_id: goodId, name });
  return data;
}

export async function removeFavorite(id: number): Promise<void> {
  await apiClient.delete(`/favorites/${id}`);
}
```

- [ ] **Step 5: Create Zustand stores**

Create `src/stores/uiStore.ts`:

```typescript
// src/stores/uiStore.ts
import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  searchQuery: string;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSearchQuery: (query: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  searchQuery: '',
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
```

Create `src/stores/analysisStore.ts`:

```typescript
// src/stores/analysisStore.ts
import { create } from 'zustand';
import type { AnalysisResult } from '../types';

export interface ProgressStep {
  step: string;
  message: string;
  timestamp: number;
}

interface AnalysisState {
  taskId: string | null;
  isLoading: boolean;
  progress: ProgressStep[];
  result: AnalysisResult | null;
  error: string | null;
  history: Array<{ query: string; result: AnalysisResult }>;

  startTask: (taskId: string) => void;
  addProgress: (step: string, message: string) => void;
  setResult: (result: AnalysisResult) => void;
  setError: (error: string) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  taskId: null,
  isLoading: false,
  progress: [],
  result: null,
  error: null,
  history: [],

  startTask: (taskId) =>
    set({ taskId, isLoading: true, progress: [], result: null, error: null }),

  addProgress: (step, message) =>
    set((s) => ({
      progress: [...s.progress, { step, message, timestamp: Date.now() }],
    })),

  setResult: (result) =>
    set((s) => ({
      isLoading: false,
      result,
      history: s.taskId
        ? [...s.history, { query: s.taskId, result }]
        : s.history,
    })),

  setError: (error) => set({ isLoading: false, error }),

  reset: () =>
    set({ taskId: null, isLoading: false, progress: [], result: null, error: null }),
}));
```

Create `src/stores/authStore.ts`:

```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import type { User } from '../types';
import { refreshAccessToken } from '../api/endpoints/auth';

interface AuthState {
  accessToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  setAuth: (token: string, user: User) => void;
  refreshToken: () => Promise<boolean>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token, user) =>
    set({ accessToken: token, user, isAuthenticated: true }),

  refreshToken: async () => {
    try {
      const { access_token } = await refreshAccessToken();
      set({ accessToken: access_token });
      return true;
    } catch {
      set({ accessToken: null, user: null, isAuthenticated: false });
      return false;
    }
  },

  logout: () => set({ accessToken: null, user: null, isAuthenticated: false }),
}));
```

- [ ] **Step 6: Verify build**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build
```
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add .
git commit -m "feat: add API client layer, TypeScript types, and Zustand stores"
```

---

### Task 4: AppLayout + TopNav + SearchBar Shell

**Files:**
- Create: `src/components/layout/AppLayout.tsx`
- Create: `src/components/layout/TopNav.tsx`
- Create: `src/components/layout/SearchBar.tsx`
- Modify: `src/App.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create SearchBar component**

Create `src/components/layout/SearchBar.tsx`:

```tsx
// src/components/layout/SearchBar.tsx
import { useState, useCallback } from 'react';
import { AutoComplete, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { searchItems } from '../../api/endpoints/item';
import { QUERY_KEYS } from '../../utils/constants';
import type { SuggestItem } from '../../types';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const { data: suggestions = [] } = useQuery({
    queryKey: QUERY_KEYS.itemSearch(query),
    queryFn: () => searchItems(query),
    enabled: query.length >= 2,
    staleTime: 30000,
  });

  const options = suggestions.map((item: SuggestItem) => ({
    value: String(item.goodId),
    label: (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src={item.imageUrl} alt="" style={{ width: 32, height: 24, objectFit: 'contain' }} />
        <span>{item.goodName}</span>
      </div>
    ),
  }));

  const handleSelect = useCallback(
    (value: string) => {
      navigate(`/item/${value}`);
      setQuery('');
    },
    [navigate],
  );

  return (
    <AutoComplete
      options={options}
      onSelect={handleSelect}
      onSearch={setQuery}
      value={query}
      style={{ width: 320 }}
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder="搜索饰品..."
        allowClear
      />
    </AutoComplete>
  );
}
```

- [ ] **Step 2: Create TopNav component**

Create `src/components/layout/TopNav.tsx`:

```tsx
// src/components/layout/TopNav.tsx
import { Layout, Menu, Button, Space } from 'antd';
import { MessageOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import SearchBar from './SearchBar';
import { useUIStore } from '../../stores/uiStore';
import { useAuthStore } from '../../stores/authStore';

const { Header } = Layout;

const NAV_ITEMS = [
  { key: '/', label: '首页' },
  { key: '/market', label: '大盘' },
  { key: '/scout', label: '发现' },
  { key: '/favorites', label: '收藏' },
];

export default function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const activeKey = NAV_ITEMS.find((item) => location.pathname === item.key)?.key || '/';

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 16,
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      }}
    >
      <div
        style={{ fontWeight: 700, fontSize: 18, color: '#1668dc', cursor: 'pointer', whiteSpace: 'nowrap' }}
        onClick={() => navigate('/')}
      >
        CSQAQ
      </div>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={[activeKey]}
        items={NAV_ITEMS}
        onClick={({ key }) => navigate(key)}
        style={{ flex: 1, minWidth: 0, background: 'transparent', borderBottom: 'none' }}
      />
      <SearchBar />
      <Space>
        <Button
          type="text"
          icon={<MessageOutlined />}
          onClick={toggleSidebar}
          style={{ color: 'rgba(255,255,255,0.65)' }}
        />
        <Button
          type="text"
          icon={<UserOutlined />}
          onClick={() => navigate(isAuthenticated ? '/profile' : '/login')}
          style={{ color: 'rgba(255,255,255,0.65)' }}
        />
      </Space>
    </Header>
  );
}
```

- [ ] **Step 3: Create AppLayout component**

Create `src/components/layout/AppLayout.tsx`:

```tsx
// src/components/layout/AppLayout.tsx
import { Layout, Drawer } from 'antd';
import { Outlet } from 'react-router-dom';
import TopNav from './TopNav';
import { useUIStore } from '../../stores/uiStore';

const { Content } = Layout;

export default function AppLayout() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <TopNav />
      <Layout>
        <Content style={{ padding: '24px', overflow: 'auto' }}>
          <Outlet />
        </Content>
        <Drawer
          title="AI 分析助手"
          placement="right"
          width={480}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          styles={{ body: { padding: 0 } }}
        >
          <div style={{ padding: 16, color: 'rgba(255,255,255,0.65)' }}>
            AI Sidebar (coming in Task 14)
          </div>
        </Drawer>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 4: Update App.tsx to use AppLayout**

Update `src/App.tsx` to wrap routes with `AppLayout`:

```tsx
// src/App.tsx
import { ConfigProvider, theme, App as AntApp } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { darkTheme } from './styles/theme';
import AppLayout from './components/layout/AppLayout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 2,
    },
  },
});

export default function App() {
  return (
    <ConfigProvider theme={{ ...darkTheme, algorithm: theme.darkAlgorithm }}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Routes>
              <Route element={<AppLayout />}>
                <Route path="/" element={<div style={{ color: '#fff' }}>Dashboard (coming soon)</div>} />
                <Route path="/item/:id" element={<div>Item Detail</div>} />
                <Route path="/market" element={<div>Market</div>} />
                <Route path="/scout" element={<div>Scout</div>} />
                <Route path="/inventory/:id" element={<div>Inventory</div>} />
                <Route path="/favorites" element={<div>Favorites</div>} />
                <Route path="/profile" element={<div>Profile</div>} />
              </Route>
              <Route path="/login" element={<div>Login</div>} />
            </Routes>
          </BrowserRouter>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  );
}
```

- [ ] **Step 5: Verify build**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build
```
Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add .
git commit -m "feat: add AppLayout with TopNav, SearchBar, and sidebar drawer shell"
```

---

## Phase 2: Item Query (Core Feature, End-to-End)

### Task 5: Backend Item REST Routes

**Files:**
- Create: `src/csqaq/api/routes/item.py`
- Create: `tests/test_api/test_item_routes.py`
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_item_routes.py`:

```python
# tests/test_api/test_item_routes.py
import pytest


class TestItemSearch:
    async def test_search_returns_list(self, client):
        response = await client.get("/api/v1/items/search", params={"q": "AK红线"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["goodId"] == 7310

    async def test_search_empty_query_returns_400(self, client):
        response = await client.get("/api/v1/items/search", params={"q": ""})
        assert response.status_code == 400


class TestItemDetail:
    async def test_detail_returns_item(self, client):
        response = await client.get("/api/v1/items/7310")
        assert response.status_code == 200
        data = response.json()
        assert data["goodId"] == 7310
        assert data["goodName"] == "AK-47 | 红线 (久经沙场)"
        assert "buffSellPrice" in data

    async def test_detail_invalid_id_returns_422(self, client):
        response = await client.get("/api/v1/items/abc")
        assert response.status_code == 422


class TestItemChart:
    async def test_chart_returns_data(self, client):
        response = await client.get("/api/v1/items/7310/chart")
        assert response.status_code == 200
        data = response.json()
        assert "points" in data
        assert len(data["points"]) > 0

    async def test_chart_with_period(self, client):
        response = await client.get("/api/v1/items/7310/chart", params={"period": "7d"})
        assert response.status_code == 200


class TestItemKline:
    async def test_kline_returns_list(self, client):
        response = await client.get("/api/v1/items/7310/kline")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "open" in data[0]
        assert "close" in data[0]


class TestItemInventory:
    async def test_inventory_returns_list(self, client):
        response = await client.get("/api/v1/items/7310/inventory")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "statistic" in data[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api/test_item_routes.py -v`
Expected: FAIL -- 404 (routes not registered)

- [ ] **Step 3: Implement item routes**

Create `src/csqaq/api/routes/item.py`:

```python
# src/csqaq/api/routes/item.py
"""Item REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from csqaq.api.deps import get_app
from csqaq.main import App

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/search")
async def search_items(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    app: App = Depends(get_app),
):
    """Search items by name. Returns list of suggestions."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    results = await app.item_api.search_suggest(q.strip())
    return [r.model_dump(by_alias=True) for r in results]


@router.get("/{item_id}")
async def get_item_detail(
    item_id: int,
    app: App = Depends(get_app),
):
    """Get full item detail by ID."""
    try:
        detail = await app.item_api.get_item_detail(item_id)
        return detail.model_dump(by_alias=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"上游 API 错误: {e}")


@router.get("/{item_id}/chart")
async def get_item_chart(
    item_id: int,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 180d, 365d"),
    platform: str = Query("buff", description="Platform: buff, steam, yyyp"),
    app: App = Depends(get_app),
):
    """Get price chart data for an item."""
    chart = await app.item_api.get_item_chart(item_id, platform=platform, period=period)
    return chart.model_dump(by_alias=True)


@router.get("/{item_id}/kline")
async def get_item_kline(
    item_id: int,
    period: str = Query("30d", description="K-line period"),
    platform: str = Query("buff", description="Platform"),
    app: App = Depends(get_app),
):
    """Get K-line candlestick data for an item."""
    bars = await app.item_api.get_item_kline(item_id, platform=platform, periods=period)
    return [bar.model_dump() for bar in bars]


@router.get("/{item_id}/inventory")
async def get_item_inventory(
    item_id: int,
    app: App = Depends(get_app),
):
    """Get 90-day inventory trend data for an item."""
    stats = await app.item_api.get_item_statistic(item_id)
    return [s.model_dump() for s in stats]
```

- [ ] **Step 4: Register item routes**

Update `src/csqaq/api/routes/__init__.py`:

```python
# src/csqaq/api/routes/__init__.py
"""Route registration."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from csqaq.api.middleware import register_error_handlers
    from csqaq.api.routes.item import router as item_router

    register_error_handlers(app)

    root = APIRouter(prefix="/api/v1")

    @root.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    root.include_router(item_router)
    app.include_router(root)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_api/test_item_routes.py -v`
Expected: All 7 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/api/routes/item.py src/csqaq/api/routes/__init__.py tests/test_api/test_item_routes.py
git commit -m "feat: add item REST routes (search, detail, chart, kline, inventory)"
```

---

### Task 6: Frontend ItemDetail Page with ECharts

**Files:**
- Create: `src/components/charts/KlineChart.tsx`
- Create: `src/components/charts/PriceChart.tsx`
- Create: `src/components/charts/InventoryChart.tsx`
- Create: `src/components/analysis/RiskBadge.tsx`
- Create: `src/components/common/FavoriteButton.tsx`
- Create: `src/pages/ItemDetail/index.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create PriceChart component**

Create `src/components/charts/PriceChart.tsx`:

```tsx
// src/components/charts/PriceChart.tsx
import ReactECharts from 'echarts-for-react';
import type { ChartPoint } from '../../types';
import { formatPrice } from '../../utils/format';

interface Props {
  data: ChartPoint[];
  title?: string;
}

export default function PriceChart({ data, title = '价格走势' }: Props) {
  const option = {
    title: { text: title, textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0];
        const date = new Date(p.value[0] * 1000).toLocaleDateString('zh-CN');
        return `${date}<br/>价格: ¥${formatPrice(p.value[1])}<br/>成交量: ${p.value[2]}`;
      },
    },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'time',
      axisLabel: { color: 'rgba(255,255,255,0.45)' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: 'rgba(255,255,255,0.45)', formatter: '¥{value}' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    },
    series: [
      {
        type: 'line',
        data: data.map((p) => [p.timestamp * 1000, p.price, p.volume]),
        smooth: true,
        lineStyle: { color: '#1668dc', width: 2 },
        areaStyle: { color: 'rgba(22,104,220,0.1)' },
        showSymbol: false,
      },
    ],
    backgroundColor: 'transparent',
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
}
```

- [ ] **Step 2: Create KlineChart component**

Create `src/components/charts/KlineChart.tsx`:

```tsx
// src/components/charts/KlineChart.tsx
import ReactECharts from 'echarts-for-react';
import type { KlineBar } from '../../types';

interface Props {
  data: KlineBar[];
  title?: string;
}

export default function KlineChart({ data, title = 'K线图' }: Props) {
  const dates = data.map((d) => new Date(d.timestamp * 1000).toLocaleDateString('zh-CN'));
  const values = data.map((d) => [d.open, d.close, d.low, d.high]);
  const volumes = data.map((d) => d.volume);

  const option = {
    title: { text: title, textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    grid: [
      { left: 60, right: 20, top: 40, height: '55%' },
      { left: 60, right: 20, top: '75%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, axisLabel: { color: 'rgba(255,255,255,0.45)' }, gridIndex: 0 },
      { type: 'category', data: dates, axisLabel: { show: false }, gridIndex: 1 },
    ],
    yAxis: [
      {
        type: 'value',
        axisLabel: { color: 'rgba(255,255,255,0.45)', formatter: '¥{value}' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        gridIndex: 0,
      },
      {
        type: 'value',
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    series: [
      {
        type: 'candlestick',
        data: values,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#52c41a',
          color0: '#ff4d4f',
          borderColor: '#52c41a',
          borderColor0: '#ff4d4f',
        },
      },
      {
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: 'rgba(22,104,220,0.4)' },
      },
    ],
    backgroundColor: 'transparent',
  };

  return <ReactECharts option={option} style={{ height: 480 }} />;
}
```

- [ ] **Step 3: Create InventoryChart component**

Create `src/components/charts/InventoryChart.tsx`:

```tsx
// src/components/charts/InventoryChart.tsx
import ReactECharts from 'echarts-for-react';
import type { InventoryStat } from '../../types';
import { formatDate } from '../../utils/format';

interface Props {
  data: InventoryStat[];
  title?: string;
}

export default function InventoryChart({ data, title = '存世量趋势' }: Props) {
  const option = {
    title: { text: title, textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0];
        return `${formatDate(p.name)}<br/>存世量: ${p.value.toLocaleString()}`;
      },
    },
    grid: { left: 80, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.created_at),
      axisLabel: {
        color: 'rgba(255,255,255,0.45)',
        formatter: (val: string) => formatDate(val),
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: 'rgba(255,255,255,0.45)' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    },
    series: [
      {
        type: 'line',
        data: data.map((d) => d.statistic),
        smooth: true,
        lineStyle: { color: '#faad14', width: 2 },
        areaStyle: { color: 'rgba(250,173,20,0.1)' },
        showSymbol: false,
      },
    ],
    backgroundColor: 'transparent',
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
}
```

- [ ] **Step 4: Create RiskBadge and FavoriteButton**

Create `src/components/analysis/RiskBadge.tsx`:

```tsx
// src/components/analysis/RiskBadge.tsx
import { Tag } from 'antd';

const RISK_CONFIG = {
  low: { color: 'green', label: '低风险' },
  medium: { color: 'orange', label: '中风险' },
  high: { color: 'red', label: '高风险' },
} as const;

export default function RiskBadge({ level }: { level: string }) {
  const config = RISK_CONFIG[level as keyof typeof RISK_CONFIG] || RISK_CONFIG.medium;
  return <Tag color={config.color}>{config.label}</Tag>;
}
```

Create `src/components/common/FavoriteButton.tsx`:

```tsx
// src/components/common/FavoriteButton.tsx
import { Button, message } from 'antd';
import { HeartOutlined, HeartFilled } from '@ant-design/icons';
import { useState } from 'react';

interface Props {
  itemId: number;
  itemName: string;
  isFavorited?: boolean;
}

export default function FavoriteButton({ itemId, itemName, isFavorited = false }: Props) {
  const [favorited, setFavorited] = useState(isFavorited);

  const handleToggle = async () => {
    // Will be connected to API in Task 17
    setFavorited(!favorited);
    message.success(favorited ? '已取消收藏' : '已收藏');
  };

  return (
    <Button
      type="text"
      icon={favorited ? <HeartFilled style={{ color: '#ff4d4f' }} /> : <HeartOutlined />}
      onClick={handleToggle}
    >
      {favorited ? '已收藏' : '收藏'}
    </Button>
  );
}
```

- [ ] **Step 5: Create ItemDetail page**

Create `src/pages/ItemDetail/index.tsx`:

```tsx
// src/pages/ItemDetail/index.tsx
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Row, Col, Card, Statistic, Descriptions, Spin, Tabs, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { getItemDetail, getItemChart, getItemKline, getItemInventory } from '../../api/endpoints/item';
import { QUERY_KEYS } from '../../utils/constants';
import { formatPrice, formatPercent, changeColor } from '../../utils/format';
import PriceChart from '../../components/charts/PriceChart';
import KlineChart from '../../components/charts/KlineChart';
import InventoryChart from '../../components/charts/InventoryChart';
import FavoriteButton from '../../components/common/FavoriteButton';

const { Title } = Typography;

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const itemId = Number(id);

  const { data: detail, isLoading } = useQuery({
    queryKey: QUERY_KEYS.itemDetail(itemId),
    queryFn: () => getItemDetail(itemId),
    enabled: !isNaN(itemId),
  });

  const { data: chartData } = useQuery({
    queryKey: QUERY_KEYS.itemChart(itemId, '30d'),
    queryFn: () => getItemChart(itemId),
    enabled: !isNaN(itemId),
  });

  const { data: klineData } = useQuery({
    queryKey: QUERY_KEYS.itemKline(itemId, '30d'),
    queryFn: () => getItemKline(itemId),
    enabled: !isNaN(itemId),
  });

  const { data: inventoryData } = useQuery({
    queryKey: QUERY_KEYS.itemInventory(itemId),
    queryFn: () => getItemInventory(itemId),
    enabled: !isNaN(itemId),
  });

  if (isLoading || !detail) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const dailyColor = changeColor(detail.dailyChangeRate);
  const weeklyColor = changeColor(detail.weeklyChangeRate);
  const monthlyColor = changeColor(detail.monthlyChangeRate);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <img src={detail.imageUrl} alt={detail.goodName} style={{ width: 80, height: 60, objectFit: 'contain' }} />
        <div>
          <Title level={3} style={{ margin: 0, color: '#fff' }}>{detail.goodName}</Title>
          <span style={{ color: 'rgba(255,255,255,0.45)' }}>{detail.marketHashName}</span>
        </div>
        <FavoriteButton itemId={itemId} itemName={detail.goodName} />
      </div>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="BUFF 售价"
              value={detail.buffSellPrice}
              prefix="¥"
              precision={2}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="日涨跌"
              value={detail.dailyChangeRate}
              precision={2}
              suffix="%"
              valueStyle={{ color: dailyColor }}
              prefix={detail.dailyChangeRate >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="周涨跌"
              value={detail.weeklyChangeRate}
              precision={2}
              suffix="%"
              valueStyle={{ color: weeklyColor }}
              prefix={detail.weeklyChangeRate >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="月涨跌"
              value={detail.monthlyChangeRate}
              precision={2}
              suffix="%"
              valueStyle={{ color: monthlyColor }}
              prefix={detail.monthlyChangeRate >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }}>
        <Tabs
          defaultActiveKey="price"
          items={[
            {
              key: 'price',
              label: '价格走势',
              children: chartData ? <PriceChart data={chartData.points} /> : <Spin />,
            },
            {
              key: 'kline',
              label: 'K线图',
              children: klineData ? <KlineChart data={klineData} /> : <Spin />,
            },
            {
              key: 'inventory',
              label: '存世量',
              children: inventoryData ? <InventoryChart data={inventoryData} /> : <Spin />,
            },
          ]}
        />
      </Card>

      <Card title="多平台价格" style={{ marginTop: 16 }}>
        <Descriptions column={4} size="small">
          <Descriptions.Item label="BUFF 卖">¥{formatPrice(detail.buffSellPrice)}</Descriptions.Item>
          <Descriptions.Item label="BUFF 买">¥{formatPrice(detail.buffBuyPrice)}</Descriptions.Item>
          <Descriptions.Item label="Steam">¥{formatPrice(detail.steamSellPrice)}</Descriptions.Item>
          <Descriptions.Item label="悠悠有品">¥{formatPrice(detail.yyypSellPrice)}</Descriptions.Item>
          <Descriptions.Item label="BUFF 在售">{detail.buffSellNum}</Descriptions.Item>
          <Descriptions.Item label="BUFF 求购">{detail.buffBuyNum}</Descriptions.Item>
          <Descriptions.Item label="Steam 在售">{detail.steamSellNum}</Descriptions.Item>
          <Descriptions.Item label="类型">{detail.category} / {detail.rarity}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: Update App.tsx route**

Update the ItemDetail route in `src/App.tsx`:

```tsx
import ItemDetail from './pages/ItemDetail';
// In routes:
<Route path="/item/:id" element={<ItemDetail />} />
```

- [ ] **Step 7: Verify build**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build
```
Expected: Build succeeds.

- [ ] **Step 8: Commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add .
git commit -m "feat: add ItemDetail page with KlineChart, PriceChart, and InventoryChart"
```

---

### Task 7: SearchBar Integration

**Files:**
- Modify: `src/components/layout/SearchBar.tsx` (already functional from Task 4)

SearchBar was already built with full API integration in Task 4. This task verifies the end-to-end flow.

- [ ] **Step 1: Manual integration test**

1. Start backend: `cd d:/program/PythonWorkSpace/CSQAQ && python -m uvicorn csqaq.api.server:create_app --factory --reload`
2. Start frontend: `cd d:/program/PythonWorkSpace/csqaq-web && npm run dev`
3. Type "AK红线" in search bar
4. Verify dropdown shows suggestions
5. Click suggestion, verify navigation to `/item/7310`
6. Verify ItemDetail page renders with charts

- [ ] **Step 2: Commit (if changes needed)**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add .
git commit -m "fix: polish SearchBar integration with item search API"
```

---

## Phase 3: Market & Scout

### Task 8: Backend Market + Scout REST Routes

**Files:**
- Create: `src/csqaq/api/routes/market.py`
- Create: `src/csqaq/api/routes/scout.py`
- Create: `tests/test_api/test_market_routes.py`
- Create: `tests/test_api/test_scout_routes.py`
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Write failing tests for market routes**

Create `tests/test_api/test_market_routes.py`:

```python
# tests/test_api/test_market_routes.py
import pytest


class TestMarketOverview:
    async def test_overview_returns_data(self, client):
        response = await client.get("/api/v1/market/overview")
        assert response.status_code == 200
        data = response.json()
        assert "sub_index_data" in data
        assert "rate_data" in data
        assert "greedy_status" in data

    async def test_sub_data_returns_data(self, client):
        response = await client.get("/api/v1/market/sub/1")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "main_data" in data

    async def test_index_kline_returns_list(self, client):
        response = await client.get("/api/v1/market/index-kline", params={"id": 1})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
```

- [ ] **Step 2: Write failing tests for scout routes**

Create `tests/test_api/test_scout_routes.py`:

```python
# tests/test_api/test_scout_routes.py
import pytest


class TestScoutRankings:
    async def test_rankings_returns_list(self, client):
        response = await client.post("/api/v1/scout/rankings", json={"filter": {}, "page": 1, "size": 20})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_items_returns_list(self, client):
        response = await client.get("/api/v1/scout/items", params={"page": 1, "size": 20})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_volume_returns_list(self, client):
        response = await client.get("/api/v1/scout/volume")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

- [ ] **Step 3: Implement market routes**

Create `src/csqaq/api/routes/market.py`:

```python
# src/csqaq/api/routes/market.py
"""Market REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from csqaq.api.deps import get_app
from csqaq.main import App

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview")
async def get_market_overview(app: App = Depends(get_app)):
    """Get home page market data (indices, sentiment, online players)."""
    data = await app.market_api.get_home_data()
    return data.model_dump()


@router.get("/sub/{sub_id}")
async def get_sub_data(
    sub_id: int,
    type: str = Query("daily", description="Data type: daily, weekly"),
    app: App = Depends(get_app),
):
    """Get sub-index detail data."""
    data = await app.market_api.get_sub_data(sub_id=sub_id, data_type=type)
    return data.model_dump()


@router.get("/index-kline")
async def get_index_kline(
    id: int = Query(1, description="Sub-index ID"),
    period: str = Query("1day", description="K-line period"),
    app: App = Depends(get_app),
):
    """Get index K-line data."""
    bars = await app.market_api.get_index_kline(sub_id=id, period=period)
    return [bar.model_dump() for bar in bars]
```

- [ ] **Step 4: Implement scout routes**

Create `src/csqaq/api/routes/scout.py`:

```python
# src/csqaq/api/routes/scout.py
"""Scout REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from csqaq.api.deps import get_app
from csqaq.main import App

router = APIRouter(prefix="/scout", tags=["scout"])


class RankingsRequest(BaseModel):
    filter: dict = {}
    page: int = 1
    size: int = 20
    search: str = ""


@router.post("/rankings")
async def get_rankings(
    body: RankingsRequest,
    app: App = Depends(get_app),
):
    """Get ranking list with filters."""
    items = await app.rank_api.get_rank_list(
        filter=body.filter, page=body.page, size=body.size, search=body.search,
    )
    return [item.model_dump() for item in items]


@router.get("/items")
async def get_scout_items(
    page: int = Query(1),
    size: int = Query(20),
    search: str = Query(""),
    app: App = Depends(get_app),
):
    """Get paginated item list."""
    items = await app.rank_api.get_page_list(page=page, size=size, search=search)
    return [item.model_dump() for item in items]


@router.get("/volume")
async def get_volume_data(app: App = Depends(get_app)):
    """Get trading volume data."""
    items = await app.vol_api.get_vol_data()
    return [item.model_dump() for item in items]
```

- [ ] **Step 5: Register routes**

Update `src/csqaq/api/routes/__init__.py` to include market and scout routers:

```python
# src/csqaq/api/routes/__init__.py
"""Route registration."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from csqaq.api.middleware import register_error_handlers
    from csqaq.api.routes.item import router as item_router
    from csqaq.api.routes.market import router as market_router
    from csqaq.api.routes.scout import router as scout_router

    register_error_handlers(app)

    root = APIRouter(prefix="/api/v1")

    @root.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    root.include_router(item_router)
    root.include_router(market_router)
    root.include_router(scout_router)
    app.include_router(root)
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_api/test_market_routes.py tests/test_api/test_scout_routes.py -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/api/routes/market.py src/csqaq/api/routes/scout.py src/csqaq/api/routes/__init__.py tests/test_api/test_market_routes.py tests/test_api/test_scout_routes.py
git commit -m "feat: add market and scout REST routes"
```

---

### Task 9: Dashboard Page

**Files:**
- Create: `src/pages/Dashboard/index.tsx`
- Create: `src/components/common/ItemCard.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create ItemCard component**

Create `src/components/common/ItemCard.tsx`:

```tsx
// src/components/common/ItemCard.tsx
import { Card, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { formatPrice, formatPercent, changeColor } from '../../utils/format';

interface Props {
  id: number;
  name: string;
  img: string;
  price: number;
  changeRate: number;
}

export default function ItemCard({ id, name, img, price, changeRate }: Props) {
  const navigate = useNavigate();

  return (
    <Card
      hoverable
      size="small"
      onClick={() => navigate(`/item/${id}`)}
      style={{ cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <img src={img} alt={name} style={{ width: 48, height: 36, objectFit: 'contain' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Typography.Text ellipsis style={{ display: 'block', color: '#fff' }}>
            {name}
          </Typography.Text>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>¥{formatPrice(price)}</span>
            <span style={{ color: changeColor(changeRate) }}>{formatPercent(changeRate)}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Create Dashboard page**

Create `src/pages/Dashboard/index.tsx`:

```tsx
// src/pages/Dashboard/index.tsx
import { useQuery } from '@tanstack/react-query';
import { Row, Col, Card, Statistic, Typography, Spin, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { getMarketOverview } from '../../api/endpoints/market';
import { getRankings } from '../../api/endpoints/scout';
import { QUERY_KEYS } from '../../utils/constants';
import { formatPercent, changeColor } from '../../utils/format';
import ItemCard from '../../components/common/ItemCard';

const { Title } = Typography;

export default function Dashboard() {
  const { data: marketData, isLoading: marketLoading } = useQuery({
    queryKey: QUERY_KEYS.marketOverview(),
    queryFn: getMarketOverview,
  });

  const { data: hotItems = [], isLoading: hotLoading } = useQuery({
    queryKey: QUERY_KEYS.scoutRankings('hot', 1),
    queryFn: () => getRankings({ '排序': ['价格_价格上升(百分比)_近7天'] }, 1, 8),
  });

  if (marketLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const indices = marketData?.sub_index_data || [];
  const greedy = marketData?.greedy_status;
  const online = marketData?.online_number;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#fff' }}>市场概览</Title>

      {/* Index Cards */}
      <Row gutter={[16, 16]}>
        {indices.map((idx) => (
          <Col span={6} key={idx.id}>
            <Card size="small">
              <Statistic
                title={idx.name}
                value={idx.market_index}
                precision={2}
                suffix={
                  <span style={{ fontSize: 14, color: changeColor(idx.chg_rate) }}>
                    {formatPercent(idx.chg_rate)}
                  </span>
                }
                valueStyle={{ color: changeColor(idx.chg_rate) }}
                prefix={idx.chg_rate >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Sentiment & Online */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="市场情绪" value={greedy?.label || '--'} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="在线人数" value={online?.current_number || 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="今日峰值" value={online?.today_peak || 0} />
          </Card>
        </Col>
      </Row>

      {/* Hot Items */}
      <Title level={4} style={{ color: '#fff', marginTop: 24 }}>热门饰品</Title>
      <Row gutter={[12, 12]}>
        {hotItems.map((item) => (
          <Col span={6} key={item.id}>
            <ItemCard
              id={item.id}
              name={item.name}
              img={item.img}
              price={item.buff_sell_price}
              changeRate={item.sell_price_rate_1}
            />
          </Col>
        ))}
      </Row>
    </div>
  );
}
```

- [ ] **Step 3: Update App.tsx route**

```tsx
import Dashboard from './pages/Dashboard';
// ...
<Route path="/" element={<Dashboard />} />
```

- [ ] **Step 4: Verify build and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add Dashboard page with market overview and hot items"
```

---

### Task 10: Market Page

**Files:**
- Create: `src/components/charts/MarketHeatmap.tsx`
- Create: `src/pages/Market/index.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create MarketHeatmap**

Create `src/components/charts/MarketHeatmap.tsx`:

```tsx
// src/components/charts/MarketHeatmap.tsx
import ReactECharts from 'echarts-for-react';

interface HeatmapItem {
  name: string;
  value: number;
}

interface Props {
  data: HeatmapItem[];
  title?: string;
}

export default function MarketHeatmap({ data, title = '涨跌分布' }: Props) {
  const option = {
    title: { text: title, textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: { formatter: (p: any) => `${p.name}: ${p.value > 0 ? '+' : ''}${p.value.toFixed(2)}%` },
    series: [
      {
        type: 'treemap',
        data: data.map((d) => ({
          name: d.name,
          value: Math.abs(d.value) + 1,
          itemStyle: { color: d.value >= 0 ? `rgba(82,196,26,${Math.min(Math.abs(d.value) / 5, 1)})` : `rgba(255,77,79,${Math.min(Math.abs(d.value) / 5, 1)})` },
          label: { show: true, formatter: `${d.name}\n${d.value > 0 ? '+' : ''}${d.value.toFixed(1)}%` },
        })),
        breadcrumb: { show: false },
      },
    ],
    backgroundColor: 'transparent',
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
```

- [ ] **Step 2: Create Market page**

Create `src/pages/Market/index.tsx`:

```tsx
// src/pages/Market/index.tsx
import { useQuery } from '@tanstack/react-query';
import { Row, Col, Card, Spin, Typography, Segmented } from 'antd';
import { useState } from 'react';
import { getMarketOverview, getSubData, getIndexKline } from '../../api/endpoints/market';
import { QUERY_KEYS } from '../../utils/constants';
import KlineChart from '../../components/charts/KlineChart';
import MarketHeatmap from '../../components/charts/MarketHeatmap';

const { Title } = Typography;

export default function Market() {
  const [selectedIndex, setSelectedIndex] = useState(1);
  const [klinePeriod, setKlinePeriod] = useState('1day');

  const { data: overview } = useQuery({
    queryKey: QUERY_KEYS.marketOverview(),
    queryFn: getMarketOverview,
  });

  const { data: subData } = useQuery({
    queryKey: QUERY_KEYS.marketSub(selectedIndex),
    queryFn: () => getSubData(selectedIndex),
  });

  const { data: klineData } = useQuery({
    queryKey: QUERY_KEYS.marketKline(selectedIndex, klinePeriod),
    queryFn: () => getIndexKline(selectedIndex, klinePeriod),
  });

  const heatmapData = (overview?.chg_type_data || []).map((d: any) => ({
    name: d.name || d.type || '',
    value: d.price_diff_1 || 0,
  }));

  const indexKlineForChart = (klineData || []).map((bar) => ({
    timestamp: parseInt(bar.t) / 1000,
    open: bar.o,
    close: bar.c,
    high: bar.h,
    low: bar.l,
    volume: bar.v,
  }));

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#fff' }}>大盘行情</Title>

      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card
            title="指数走势"
            extra={
              <Segmented
                options={['1day', '1week', '1month']}
                value={klinePeriod}
                onChange={(v) => setKlinePeriod(v as string)}
                size="small"
              />
            }
          >
            {indexKlineForChart.length > 0 ? (
              <KlineChart data={indexKlineForChart} title={subData?.count?.name || '指数'} />
            ) : (
              <Spin />
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="涨跌热力图">
            <MarketHeatmap data={heatmapData} title="" />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 3: Update App.tsx route and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add Market page with index kline and sector heatmap"
```

---

### Task 11: Scout Page

**Files:**
- Create: `src/pages/Scout/index.tsx`

File in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create Scout page**

Create `src/pages/Scout/index.tsx`:

```tsx
// src/pages/Scout/index.tsx
import { useQuery } from '@tanstack/react-query';
import { Table, Card, Typography, Segmented, Tag } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRankings, getVolumeData } from '../../api/endpoints/scout';
import { QUERY_KEYS } from '../../utils/constants';
import { formatPrice, formatPercent, changeColor } from '../../utils/format';
import type { RankItem } from '../../types';

const { Title } = Typography;

// Filter keys match the external CSQAQ API format (Chinese keys)
// See: src/csqaq/infrastructure/csqaq_client/rank_filters.py
const RANK_FILTERS: Record<string, Record<string, string[]>> = {
  '周涨幅': { '排序': ['价格_价格上升(百分比)_近7天'] },
  '周跌幅': { '排序': ['价格_价格下降(百分比)_近7天'] },
  '成交量': { '排序': ['成交量_Steam日成交量'] },
  '存世量': { '排序': ['存世量_存世量_升序'] },
  '在售减少': { '排序': ['在售数量_数量减少_近7天'] },
  '求购增多': { '排序': ['求购数量_数量增多_近7天'] },
};

export default function Scout() {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState('日涨幅');
  const [page, setPage] = useState(1);

  const { data: rankings = [], isLoading } = useQuery({
    queryKey: QUERY_KEYS.scoutRankings(activeFilter, page),
    queryFn: () => getRankings(RANK_FILTERS[activeFilter], page, 20),
  });

  const { data: volumeData = [] } = useQuery({
    queryKey: QUERY_KEYS.scoutVolume(),
    queryFn: getVolumeData,
  });

  const columns = [
    {
      title: '#',
      dataIndex: 'rank_num',
      key: 'rank',
      width: 50,
    },
    {
      title: '饰品',
      key: 'name',
      render: (_: unknown, record: RankItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img src={record.img} alt="" style={{ width: 40, height: 30, objectFit: 'contain' }} />
          <div>
            <div style={{ color: '#fff' }}>{record.name}</div>
            <Tag color="blue" style={{ fontSize: 10 }}>{record.rarity_localized_name}</Tag>
          </div>
        </div>
      ),
    },
    {
      title: 'BUFF 价格',
      dataIndex: 'buff_sell_price',
      key: 'price',
      render: (v: number) => `¥${formatPrice(v)}`,
      sorter: (a: RankItem, b: RankItem) => a.buff_sell_price - b.buff_sell_price,
    },
    {
      title: '日涨跌',
      dataIndex: 'sell_price_rate_1',
      key: 'daily',
      render: (v: number) => <span style={{ color: changeColor(v) }}>{formatPercent(v)}</span>,
      sorter: (a: RankItem, b: RankItem) => a.sell_price_rate_1 - b.sell_price_rate_1,
    },
    {
      title: '周涨跌',
      dataIndex: 'sell_price_rate_7',
      key: 'weekly',
      render: (v: number) => <span style={{ color: changeColor(v) }}>{formatPercent(v)}</span>,
    },
    {
      title: '月涨跌',
      dataIndex: 'sell_price_rate_30',
      key: 'monthly',
      render: (v: number) => <span style={{ color: changeColor(v) }}>{formatPercent(v)}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#fff' }}>发现机会</Title>

      <Card>
        <Segmented
          options={Object.keys(RANK_FILTERS)}
          value={activeFilter}
          onChange={(v) => { setActiveFilter(v as string); setPage(1); }}
          style={{ marginBottom: 16 }}
        />
        <Table
          columns={columns}
          dataSource={rankings}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: 20,
            onChange: setPage,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/item/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size="small"
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Update App.tsx route and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add Scout page with rankings table and filters"
```

---

## Phase 4: WebSocket + AI Sidebar

### Task 12: Backend WebSocket Handler

**Files:**
- Create: `src/csqaq/api/ws/__init__.py`
- Create: `src/csqaq/api/ws/progress.py`
- Create: `src/csqaq/api/ws/analysis.py`
- Create: `tests/test_api/test_ws.py`
- Modify: `src/csqaq/main.py`
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Write failing WebSocket test**

Create `tests/test_api/test_ws.py`:

```python
# tests/test_api/test_ws.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient


class TestWebSocketAnalysis:
    def test_ws_connect_and_query(self, mock_app):
        """Test WebSocket connection, query, and result reception."""
        from csqaq.api.server import create_app
        from csqaq.main import RunQueryResult

        fastapi_app = create_app(mock_app)

        mock_result = RunQueryResult(
            summary="AK红线短期震荡，建议观望",
            action_detail="当前价格85.5元处于30日均线附近...",
            risk_level="low",
            requires_confirmation=False,
        )

        with patch("csqaq.api.ws.analysis.run_query_with_progress") as mock_progress:
            async def fake_progress(app, query):
                from csqaq.api.ws.progress import ProgressStep
                yield ProgressStep(step="routing", message="正在分析意图...")
                yield ProgressStep(step="analyzing", message="正在分析...")
                yield mock_result

            mock_progress.side_effect = fake_progress

            with TestClient(fastapi_app) as tc:
                with tc.websocket_connect("/ws/analysis") as ws:
                    # Send query
                    ws.send_json({"type": "query", "payload": {"text": "AK红线能入吗"}})

                    # Receive task_started
                    msg = ws.receive_json()
                    assert msg["type"] == "task_started"
                    task_id = msg["task_id"]

                    # Receive progress
                    msg = ws.receive_json()
                    assert msg["type"] == "progress"
                    assert msg["step"] == "routing"

                    msg = ws.receive_json()
                    assert msg["type"] == "progress"
                    assert msg["step"] == "analyzing"

                    # Receive result
                    msg = ws.receive_json()
                    assert msg["type"] == "result"
                    assert msg["task_id"] == task_id
                    assert "summary" in msg["payload"]
```

- [ ] **Step 2: Add `get_router_flow()` to App**

Modify `src/csqaq/main.py` to add graph pre-compilation. Add these lines to the `App` class:

```python
# In App.__init__, add:
self._router_flow = None

# New method:
def get_router_flow(self):
    """Get pre-compiled router flow. Compiles on first call, reuses thereafter."""
    if self._router_flow is None:
        from csqaq.flows.router_flow import build_router_flow
        self._router_flow = build_router_flow(
            item_api=self.item_api, market_api=self.market_api,
            rank_api=self.rank_api, vol_api=self.vol_api,
            model_factory=self.model_factory,
        )
    return self._router_flow
```

- [ ] **Step 3: Implement progress streaming**

Create `src/csqaq/api/ws/__init__.py` (empty).

Create `src/csqaq/api/ws/progress.py`:

```python
# src/csqaq/api/ws/progress.py
"""Progress streaming for LangGraph analysis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Union

from csqaq.main import App, RunQueryResult


@dataclass
class ProgressStep:
    step: str
    message: str


NODE_PROGRESS_MAP = {
    "router": ("routing", "正在分析意图..."),
    "prepare_queries": ("fetching", "正在获取行情数据..."),
    "run_parallel": ("analyzing", "正在并行分析（行情+大盘+排行+存世量）..."),
    "merge_contexts": ("merging", "正在整合分析结果..."),
    "advise": ("advising", "正在生成投资建议..."),
    "fetch_market_data": ("fetching", "正在获取大盘数据..."),
    "analyze_market": ("analyzing", "正在分析大盘行情..."),
    "fetch_rank_data": ("fetching", "正在获取排行数据..."),
    "analyze_opportunities": ("analyzing", "正在分析投资机会..."),
    "resolve_item": ("fetching", "正在解析饰品信息..."),
    "fetch_inventory": ("fetching", "正在获取存世量数据..."),
    "analyze_inventory": ("analyzing", "正在分析存世量趋势..."),
    "interpret_inventory": ("analyzing", "正在解读存世量变化..."),
    "item_subflow": ("analyzing", "正在执行单品分析..."),
    "market_subflow": ("analyzing", "正在执行大盘分析..."),
    "scout_subflow": ("analyzing", "正在执行机会发现..."),
    "inventory_subflow": ("analyzing", "正在执行存世量分析..."),
}


async def run_query_with_progress(
    app: App, query: str,
) -> AsyncIterator[Union[ProgressStep, RunQueryResult]]:
    """Run a query through the router flow, yielding progress steps.

    Yields ProgressStep objects for each LangGraph node entered,
    and finally yields the RunQueryResult.
    """
    router_flow = app.get_router_flow()
    input_state = {
        "messages": [], "query": query, "intent": None,
        "item_name": None, "result": None, "error": None,
        "requires_confirmation": False, "risk_level": None,
        "summary": None, "action_detail": None,
    }

    final_state = None
    seen_nodes = set()

    async for event in router_flow.astream_events(input_state, version="v2"):
        if event["event"] == "on_chain_start":
            node_name = event.get("name", "")
            if node_name in NODE_PROGRESS_MAP and node_name not in seen_nodes:
                seen_nodes.add(node_name)
                step, message = NODE_PROGRESS_MAP[node_name]
                yield ProgressStep(step=step, message=message)

        if event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
            final_state = event.get("data", {}).get("output", {})

    if final_state is None:
        yield RunQueryResult(
            summary="分析超时或被取消",
            action_detail="",
            risk_level="unknown",
            requires_confirmation=False,
        )
        return

    r = final_state
    if r.get("error") and not r.get("summary"):
        yield RunQueryResult(
            summary=f"查询失败: {r['error']}",
            action_detail="",
            risk_level="unknown",
            requires_confirmation=False,
        )
    else:
        yield RunQueryResult(
            summary=r.get("summary") or r.get("result") or "查询完成",
            action_detail=r.get("action_detail") or "",
            risk_level=r.get("risk_level") or "unknown",
            requires_confirmation=r.get("requires_confirmation", False),
        )
```

- [ ] **Step 4: Implement WebSocket handler**

Create `src/csqaq/api/ws/analysis.py`:

```python
# src/csqaq/api/ws/analysis.py
"""WebSocket endpoint for real-time analysis."""
from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from csqaq.api.ws.progress import ProgressStep, run_query_with_progress
from csqaq.main import App, RunQueryResult

logger = logging.getLogger(__name__)

# Per-connection concurrency: max 1 active task
MAX_CONCURRENT_PER_CONNECTION = 1
# Global concurrency
MAX_GLOBAL_CONCURRENT = 10

_global_semaphore = asyncio.Semaphore(MAX_GLOBAL_CONCURRENT)


async def analysis_handler(websocket: WebSocket, app: App) -> None:
    """Handle a WebSocket connection for analysis queries."""
    await websocket.accept()
    active_tasks: dict[str, asyncio.Task] = {}
    authenticated_user: dict | None = None

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "auth":
                token = msg.get("payload", {}).get("token", "")
                from csqaq.api.routes.auth import verify_access_token

                authenticated_user = verify_access_token(token, app.settings.secret_key)
                if authenticated_user:
                    await websocket.send_json({"type": "auth_ok"})
                else:
                    await websocket.send_json({"type": "auth_error", "message": "Token 无效"})

            elif msg_type == "query":
                text = msg.get("payload", {}).get("text", "").strip()
                if not text or len(text) > 200:
                    await websocket.send_json({
                        "type": "error",
                        "task_id": "",
                        "message": "查询内容不能为空，且不超过200字",
                    })
                    continue

                # Enforce per-connection limit
                if len(active_tasks) >= MAX_CONCURRENT_PER_CONNECTION:
                    await websocket.send_json({
                        "type": "error",
                        "task_id": "",
                        "message": "已有分析任务进行中，请等待完成",
                    })
                    continue

                task_id = str(uuid4())
                task = asyncio.create_task(
                    _run_analysis(websocket, app, task_id, text, active_tasks)
                )
                active_tasks[task_id] = task

            elif msg_type == "cancel":
                cancel_id = msg.get("payload", {}).get("task_id", "")
                task = active_tasks.pop(cancel_id, None)
                if task:
                    task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        for task in active_tasks.values():
            task.cancel()


async def _run_analysis(
    websocket: WebSocket,
    app: App,
    task_id: str,
    query: str,
    active_tasks: dict[str, asyncio.Task],
) -> None:
    """Run analysis and stream progress over WebSocket."""
    try:
        async with _global_semaphore:
            await websocket.send_json({"type": "task_started", "task_id": task_id})

            async for item in run_query_with_progress(app, query):
                if isinstance(item, ProgressStep):
                    await websocket.send_json({
                        "type": "progress",
                        "task_id": task_id,
                        "step": item.step,
                        "message": item.message,
                    })
                elif isinstance(item, RunQueryResult):
                    result_payload = {
                        "summary": item.summary,
                        "action_detail": item.action_detail,
                        "risk_level": item.risk_level,
                        "requires_confirmation": item.requires_confirmation,
                    }
                    await websocket.send_json({
                        "type": "result",
                        "task_id": task_id,
                        "payload": result_payload,
                    })
                    # Record query history for authenticated users
                    if hasattr(websocket, '_user_id') and websocket._user_id:
                        try:
                            from csqaq.infrastructure.database.models import QueryHistory
                            async with app.database.session() as session:
                                record = QueryHistory(
                                    user_id=websocket._user_id,
                                    query_text=query[:200],
                                    intent=result_payload.get("intent", ""),
                                    summary=item.summary,
                                    risk_level=item.risk_level,
                                )
                                session.add(record)
                                await session.commit()
                        except Exception as hist_err:
                            logger.warning("Failed to save query history: %s", hist_err)
    except asyncio.CancelledError:
        try:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "message": "任务已取消",
            })
        except Exception:
            pass
    except Exception as e:
        logger.error("Analysis error for task %s: %s", task_id, e)
        try:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "message": f"分析出错: {e}",
            })
        except Exception:
            pass
    finally:
        active_tasks.pop(task_id, None)
```

- [ ] **Step 5: Register WebSocket route**

Update `src/csqaq/api/routes/__init__.py`:

```python
# Add after existing route registration:
from fastapi import WebSocket
from csqaq.api.ws.analysis import analysis_handler

@app.websocket("/ws/analysis")
async def ws_analysis(websocket: WebSocket):
    from csqaq.api.deps import get_app
    app_container = websocket.app.state.app
    await analysis_handler(websocket, app_container)
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_api/test_ws.py -v`
Expected: Pass

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/api/ws/ src/csqaq/main.py src/csqaq/api/routes/__init__.py tests/test_api/test_ws.py
git commit -m "feat: add WebSocket handler with progress streaming and concurrency control"
```

---

### Task 13: Frontend useWebSocket Hook + analysisStore

**Files:**
- Create: `src/hooks/useWebSocket.ts`
- Create: `src/hooks/useAnalysis.ts`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create useWebSocket hook**

Create `src/hooks/useWebSocket.ts`:

```typescript
// src/hooks/useWebSocket.ts
import { useRef, useCallback, useEffect } from 'react';
import { WS_BASE_URL } from '../utils/constants';
import { useAuthStore } from '../stores/authStore';
import { useAnalysisStore } from '../stores/analysisStore';
import type { ServerMessage } from '../types';

const MAX_RECONNECT_DELAY = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<number | null>(null);

  const accessToken = useAuthStore((s) => s.accessToken);
  const { startTask, addProgress, setResult, setError } = useAnalysisStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE_URL}/analysis`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttempt.current = 0;
      // Authenticate if we have a token
      if (accessToken) {
        ws.send(JSON.stringify({ type: 'auth', payload: { token: accessToken } }));
      }
    };

    ws.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);

      switch (msg.type) {
        case 'auth_ok':
          break;
        case 'auth_error':
          console.warn('WebSocket auth failed:', msg.message);
          break;
        case 'task_started':
          startTask(msg.task_id);
          break;
        case 'progress':
          addProgress(msg.step, msg.message);
          break;
        case 'result':
          setResult(msg.payload);
          break;
        case 'error':
          setError(msg.message);
          break;
      }
    };

    ws.onclose = () => {
      const delay = Math.min(1000 * 2 ** reconnectAttempt.current, MAX_RECONNECT_DELAY);
      reconnectAttempt.current++;
      reconnectTimer.current = window.setTimeout(connect, delay);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };
  }, [accessToken, startTask, addProgress, setResult, setError]);

  const sendQuery = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'query', payload: { text } }));
    } else {
      setError('WebSocket 未连接，请稍后重试');
    }
  }, [setError]);

  const cancelTask = useCallback((taskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel', payload: { task_id: taskId } }));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { sendQuery, cancelTask, isConnected: wsRef.current?.readyState === WebSocket.OPEN };
}
```

- [ ] **Step 2: Create useAnalysis hook**

Create `src/hooks/useAnalysis.ts`:

```typescript
// src/hooks/useAnalysis.ts
import { useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAnalysisStore } from '../stores/analysisStore';
import { useUIStore } from '../stores/uiStore';

export function useAnalysis() {
  const { sendQuery, cancelTask } = useWebSocket();
  const { taskId, isLoading, progress, result, error, reset } = useAnalysisStore();
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  const analyze = useCallback(
    (query: string) => {
      reset();
      setSidebarOpen(true);
      sendQuery(query);
    },
    [sendQuery, reset, setSidebarOpen],
  );

  const cancel = useCallback(() => {
    if (taskId) {
      cancelTask(taskId);
    }
  }, [taskId, cancelTask]);

  return {
    analyze,
    cancel,
    isLoading,
    progress,
    result,
    error,
    taskId,
  };
}
```

- [ ] **Step 3: Verify build and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add useWebSocket hook with reconnect and useAnalysis orchestration"
```

---

### Task 14: AISidebar Component

**Files:**
- Create: `src/components/layout/AISidebar.tsx`
- Create: `src/components/analysis/ProgressSteps.tsx`
- Create: `src/components/analysis/AnalysisCard.tsx`
- Create: `src/components/common/ConfirmModal.tsx`
- Modify: `src/components/layout/AppLayout.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create ProgressSteps component**

Create `src/components/analysis/ProgressSteps.tsx`:

```tsx
// src/components/analysis/ProgressSteps.tsx
import { Steps, Spin } from 'antd';
import type { ProgressStep } from '../../stores/analysisStore';

interface Props {
  steps: ProgressStep[];
  isLoading: boolean;
}

export default function ProgressSteps({ steps, isLoading }: Props) {
  if (steps.length === 0) return null;

  const items = steps.map((s, i) => ({
    title: s.message,
    status: (i < steps.length - 1 ? 'finish' : isLoading ? 'process' : 'finish') as 'finish' | 'process',
  }));

  return (
    <div style={{ padding: '16px 0' }}>
      <Steps
        direction="vertical"
        size="small"
        current={steps.length - 1}
        items={items}
      />
      {isLoading && <Spin size="small" style={{ marginTop: 8 }} />}
    </div>
  );
}
```

- [ ] **Step 2: Create AnalysisCard component**

Create `src/components/analysis/AnalysisCard.tsx`:

```tsx
// src/components/analysis/AnalysisCard.tsx
import { Card, Typography } from 'antd';
import RiskBadge from './RiskBadge';
import type { AnalysisResult } from '../../types';

const { Paragraph } = Typography;

interface Props {
  result: AnalysisResult;
  showDetail: boolean;
}

export default function AnalysisCard({ result, showDetail }: Props) {
  return (
    <Card size="small" style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <RiskBadge level={result.risk_level} />
      </div>
      <Paragraph style={{ color: '#fff', marginBottom: 8 }}>
        {result.summary}
      </Paragraph>
      {showDetail && result.action_detail && (
        <Paragraph style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13 }}>
          {result.action_detail}
        </Paragraph>
      )}
    </Card>
  );
}
```

- [ ] **Step 3: Create ConfirmModal**

Create `src/components/common/ConfirmModal.tsx`:

```tsx
// src/components/common/ConfirmModal.tsx
import { Modal, Typography } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

interface Props {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  summary: string;
}

export default function ConfirmModal({ open, onConfirm, onCancel, summary }: Props) {
  return (
    <Modal
      title={
        <span>
          <ExclamationCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
          高风险操作确认
        </span>
      }
      open={open}
      onOk={onConfirm}
      onCancel={onCancel}
      okText="我了解风险，查看详情"
      cancelText="取消"
      okButtonProps={{ danger: true }}
    >
      <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.85)' }}>
        {summary}
      </Typography.Paragraph>
      <Typography.Paragraph type="warning">
        该分析结果包含高风险操作建议，请确认后查看详细操作建议。
      </Typography.Paragraph>
    </Modal>
  );
}
```

- [ ] **Step 4: Create AISidebar component**

Create `src/components/layout/AISidebar.tsx`:

```tsx
// src/components/layout/AISidebar.tsx
import { useState } from 'react';
import { Input, Button, Empty } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';
import { useAnalysis } from '../../hooks/useAnalysis';
import ProgressSteps from '../analysis/ProgressSteps';
import AnalysisCard from '../analysis/AnalysisCard';
import ConfirmModal from '../common/ConfirmModal';

export default function AISidebar() {
  const [input, setInput] = useState('');
  const [showDetail, setShowDetail] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const { analyze, cancel, isLoading, progress, result, error } = useAnalysis();

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setShowDetail(false);
    analyze(text);
    setInput('');
  };

  const handleResultDisplay = () => {
    if (result?.requires_confirmation && !showDetail) {
      setConfirmOpen(true);
    }
  };

  // Auto-trigger confirmation modal when result arrives
  if (result && result.requires_confirmation && !showDetail && !confirmOpen) {
    handleResultDisplay();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Chat area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {!result && !isLoading && progress.length === 0 && (
          <Empty
            description="输入任意查询开始分析"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 60 }}
          />
        )}

        {progress.length > 0 && (
          <ProgressSteps steps={progress} isLoading={isLoading} />
        )}

        {error && (
          <div style={{ color: '#ff4d4f', padding: '8px 0' }}>{error}</div>
        )}

        {result && (
          <AnalysisCard
            result={result}
            showDetail={showDetail || !result.requires_confirmation}
          />
        )}
      </div>

      {/* Input area */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <Input.Search
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onSearch={handleSend}
          placeholder="输入查询，如 'AK红线能入吗'"
          enterButton={
            isLoading ? (
              <Button icon={<StopOutlined />} onClick={cancel} danger>
                取消
              </Button>
            ) : (
              <Button icon={<SendOutlined />} type="primary">
                分析
              </Button>
            )
          }
          maxLength={200}
        />
      </div>

      <ConfirmModal
        open={confirmOpen}
        summary={result?.summary || ''}
        onConfirm={() => { setShowDetail(true); setConfirmOpen(false); }}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
```

- [ ] **Step 5: Update AppLayout to use AISidebar**

Update `src/components/layout/AppLayout.tsx` Drawer content:

```tsx
import AISidebar from './AISidebar';
// In the Drawer:
<Drawer ...>
  <AISidebar />
</Drawer>
```

- [ ] **Step 6: Verify build and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add AISidebar with progress display, result rendering, and risk confirmation"
```

---

## Phase 5: Auth + User Features

### Task 15: Alembic Setup + User Model + Auth Routes

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/001_baseline.py`
- Create: `alembic/versions/002_add_user_and_history.py`
- Create: `src/csqaq/api/routes/auth.py`
- Create: `tests/test_api/test_auth.py`
- Modify: `src/csqaq/infrastructure/database/models.py`
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Write failing auth tests**

Create `tests/test_api/test_auth.py`:

```python
# tests/test_api/test_auth.py
import pytest
from httpx import ASGITransport, AsyncClient

from csqaq.config import Settings
from csqaq.main import App


@pytest.fixture
async def auth_client():
    """Client with real in-memory database for auth testing."""
    settings = Settings(
        csqaq_api_token="test",
        openai_api_key="test",
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-key-for-jwt-minimum-32-characters-long",
    )
    app = App(settings)
    await app.init()

    from csqaq.api.server import create_app

    fastapi_app = create_app(app)
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await app.close()


class TestAuthRegister:
    async def test_register_success(self, auth_client):
        response = await auth_client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["username"] == "testuser"

    async def test_register_duplicate_username(self, auth_client):
        await auth_client.post("/api/v1/auth/register", json={
            "username": "testuser", "email": "a@b.com", "password": "pass123",
        })
        response = await auth_client.post("/api/v1/auth/register", json={
            "username": "testuser", "email": "c@d.com", "password": "pass123",
        })
        assert response.status_code == 409


class TestAuthLogin:
    async def test_login_success(self, auth_client):
        # Register first
        await auth_client.post("/api/v1/auth/register", json={
            "username": "loginuser", "email": "login@test.com", "password": "pass123",
        })
        # Login
        response = await auth_client.post("/api/v1/auth/login", json={
            "username": "loginuser", "password": "pass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_wrong_password(self, auth_client):
        await auth_client.post("/api/v1/auth/register", json={
            "username": "user2", "email": "u2@test.com", "password": "correct",
        })
        response = await auth_client.post("/api/v1/auth/login", json={
            "username": "user2", "password": "wrong",
        })
        assert response.status_code == 401


class TestAuthProtected:
    async def test_me_requires_auth(self, auth_client):
        response = await auth_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_token(self, auth_client):
        reg = await auth_client.post("/api/v1/auth/register", json={
            "username": "meuser", "email": "me@test.com", "password": "pass123",
        })
        token = reg.json()["access_token"]
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "meuser"
```

- [ ] **Step 2: Add User and QueryHistory models**

Add to `src/csqaq/infrastructure/database/models.py`:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(String(200), nullable=False)
    intent: Mapped[str] = mapped_column(String(50), default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Implement auth routes**

Create `src/csqaq/api/routes/auth.py`:

```python
# src/csqaq/api/routes/auth.py
"""Authentication routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select

from csqaq.api.deps import get_app, get_current_user
from csqaq.infrastructure.database.models import User
from csqaq.main import App

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, secret_key: str, expires_minutes: int = 30) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def create_refresh_token(data: dict, secret_key: str, expires_days: int = 7) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def verify_access_token(token: str, secret_key: str) -> dict | None:
    """Verify JWT token and return payload, or None if invalid."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        if payload.get("type") == "refresh":
            return None  # Don't accept refresh tokens as access tokens
        return payload
    except JWTError:
        return None


@router.post("/register")
async def register(body: RegisterRequest, response: Response, app: App = Depends(get_app)):
    async with app.database.session() as session:
        # Check duplicate username
        existing = await session.execute(
            select(User).where(User.username == body.username)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="用户名已存在")

        # Check duplicate email
        existing_email = await session.execute(
            select(User).where(User.email == body.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="邮箱已注册")

        user = User(
            username=body.username,
            email=body.email,
            hashed_password=pwd_context.hash(body.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        access_token = create_access_token(
            {"sub": str(user.id), "username": user.username},
            app.settings.secret_key,
            app.settings.access_token_expire_minutes,
        )
        refresh_token = create_refresh_token(
            {"sub": str(user.id)},
            app.settings.secret_key,
            app.settings.refresh_token_expire_days,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=(app.settings.mode == "server"),
            samesite="strict",
            max_age=app.settings.refresh_token_expire_days * 86400,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }


@router.post("/login")
async def login(body: LoginRequest, response: Response, app: App = Depends(get_app)):
    async with app.database.session() as session:
        result = await session.execute(
            select(User).where(User.username == body.username)
        )
        user = result.scalar_one_or_none()

        if not user or not pwd_context.verify(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已禁用")

        access_token = create_access_token(
            {"sub": str(user.id), "username": user.username},
            app.settings.secret_key,
            app.settings.access_token_expire_minutes,
        )
        refresh_token = create_refresh_token(
            {"sub": str(user.id)},
            app.settings.secret_key,
            app.settings.refresh_token_expire_days,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=(app.settings.mode == "server"),
            samesite="strict",
            max_age=app.settings.refresh_token_expire_days * 86400,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }


@router.post("/refresh")
async def refresh(
    request: Request,
    app: App = Depends(get_app),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(refresh_token, app.settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    async with app.database.session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

    new_access = create_access_token(
        {"sub": str(user.id), "username": user.username},
        app.settings.secret_key, app.settings.access_token_expire_minutes,
    )
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    app: App = Depends(get_app),
):
    user_id = int(current_user["sub"])
    async with app.database.session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"id": user.id, "username": user.username, "email": user.email}
```

- [ ] **Step 4: Register auth routes**

Update `src/csqaq/api/routes/__init__.py` to include:

```python
from csqaq.api.routes.auth import router as auth_router
root.include_router(auth_router)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_api/test_auth.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/database/models.py src/csqaq/api/routes/auth.py src/csqaq/api/routes/__init__.py tests/test_api/test_auth.py
git commit -m "feat: add User model, JWT auth routes (register, login, me)"
```

---

### Task 16: Frontend Auth (Login/Register Page)

**Files:**
- Create: `src/pages/Login/index.tsx`
- Create: `src/hooks/useAuth.ts`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Create useAuth hook**

Create `src/hooks/useAuth.ts`:

```typescript
// src/hooks/useAuth.ts
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { login as apiLogin, register as apiRegister } from '../api/endpoints/auth';

export function useAuth() {
  const { isAuthenticated, user, setAuth, logout: storeLogout } = useAuthStore();
  const navigate = useNavigate();

  const login = useCallback(
    async (username: string, password: string) => {
      const data = await apiLogin(username, password);
      setAuth(data.access_token, data.user);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      const data = await apiRegister(username, email, password);
      setAuth(data.access_token, data.user);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const logout = useCallback(() => {
    storeLogout();
    navigate('/login');
  }, [storeLogout, navigate]);

  return { isAuthenticated, user, login, register, logout };
}
```

- [ ] **Step 2: Create Login page**

Create `src/pages/Login/index.tsx`:

```tsx
// src/pages/Login/index.tsx
import { useState } from 'react';
import { Card, Form, Input, Button, Tabs, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useAuth } from '../../hooks/useAuth';

const { Title } = Typography;

export default function Login() {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
    } catch (err: any) {
      message.error(err.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: { username: string; email: string; password: string }) => {
    setLoading(true);
    try {
      await register(values.username, values.email, values.password);
      message.success('注册成功');
    } catch (err: any) {
      message.error(err.response?.data?.detail || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#000' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center', color: '#1668dc' }}>CSQAQ</Title>
        <Tabs activeKey={activeTab} onChange={setActiveTab} centered items={[
          {
            key: 'login',
            label: '登录',
            children: (
              <Form onFinish={handleLogin} size="large">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
                </Form.Item>
              </Form>
            ),
          },
          {
            key: 'register',
            label: '注册',
            children: (
              <Form onFinish={handleRegister} size="large">
                <Form.Item name="username" rules={[{ required: true, min: 3, message: '用户名至少3个字符' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                  <Input prefix={<MailOutlined />} placeholder="邮箱" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6个字符' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>注册</Button>
                </Form.Item>
              </Form>
            ),
          },
        ]} />
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Update App.tsx with Login route and commit**

```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build && git add . && git commit -m "feat: add Login/Register page with JWT auth flow"
```

---

### Task 17: Favorites Routes + Favorites Page

**Files:**
- Create: `src/csqaq/api/routes/favorites.py`
- Create: `tests/test_api/test_favorites.py`
- Create: `src/pages/Favorites/index.tsx` (in csqaq-web)
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Write failing favorites tests**

Create `tests/test_api/test_favorites.py`:

```python
# tests/test_api/test_favorites.py
import pytest
from httpx import ASGITransport, AsyncClient
from csqaq.config import Settings
from csqaq.main import App


@pytest.fixture
async def auth_fav_client():
    settings = Settings(
        csqaq_api_token="test", openai_api_key="test",
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret-key-for-jwt-minimum-32-characters-long",
    )
    app = App(settings)
    await app.init()
    from csqaq.api.server import create_app
    fastapi_app = create_app(app)
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register and get token
        reg = await ac.post("/api/v1/auth/register", json={
            "username": "favuser", "email": "fav@test.com", "password": "pass123",
        })
        token = reg.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
    await app.close()


class TestFavorites:
    async def test_list_empty(self, auth_fav_client):
        response = await auth_fav_client.get("/api/v1/favorites")
        assert response.status_code == 200
        assert response.json() == []

    async def test_add_favorite(self, auth_fav_client):
        response = await auth_fav_client.post("/api/v1/favorites", json={
            "good_id": 7310,
            "name": "AK-47 | 红线 (久经沙场)",
            "market_hash_name": "AK-47 | Redline (Field-Tested)",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["good_id"] == 7310

    async def test_list_after_add(self, auth_fav_client):
        await auth_fav_client.post("/api/v1/favorites", json={
            "good_id": 7310, "name": "AK红线", "market_hash_name": "AK Redline",
        })
        response = await auth_fav_client.get("/api/v1/favorites")
        assert len(response.json()) == 1

    async def test_delete_favorite(self, auth_fav_client):
        add_resp = await auth_fav_client.post("/api/v1/favorites", json={
            "good_id": 7310, "name": "AK红线", "market_hash_name": "AK Redline",
        })
        fav_id = add_resp.json()["id"]
        del_resp = await auth_fav_client.delete(f"/api/v1/favorites/{fav_id}")
        assert del_resp.status_code == 200

    async def test_favorites_require_auth(self):
        settings = Settings(
            csqaq_api_token="test", openai_api_key="test",
            database_url="sqlite+aiosqlite:///:memory:",
            secret_key="test-secret-key-for-jwt-minimum-32-characters-long",
        )
        app = App(settings)
        await app.init()
        from csqaq.api.server import create_app
        fastapi_app = create_app(app)
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/favorites")
            assert response.status_code == 401
        await app.close()
```

- [ ] **Step 2: Implement favorites routes**

Create `src/csqaq/api/routes/favorites.py`:

```python
# src/csqaq/api/routes/favorites.py
"""Favorites routes using existing Watchlist model."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from csqaq.api.deps import get_app, get_current_user
from csqaq.infrastructure.database.models import Watchlist
from csqaq.main import App

router = APIRouter(prefix="/favorites", tags=["favorites"])


class AddFavoriteRequest(BaseModel):
    good_id: int
    name: str
    market_hash_name: str = ""
    alert_threshold_pct: float = 5.0
    notes: str = ""


@router.get("")
async def list_favorites(
    current_user: dict = Depends(get_current_user),
    app: App = Depends(get_app),
):
    user_id = int(current_user["sub"])
    async with app.database.session() as session:
        result = await session.execute(
            select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.added_at.desc())
        )
        items = result.scalars().all()
        return [
            {
                "id": item.id,
                "good_id": item.good_id,
                "name": item.name,
                "market_hash_name": item.market_hash_name,
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "alert_threshold_pct": item.alert_threshold_pct,
                "notes": item.notes,
            }
            for item in items
        ]


@router.post("")
async def add_favorite(
    body: AddFavoriteRequest,
    current_user: dict = Depends(get_current_user),
    app: App = Depends(get_app),
):
    user_id = int(current_user["sub"])
    async with app.database.session() as session:
        # Check duplicate
        existing = await session.execute(
            select(Watchlist).where(
                Watchlist.user_id == user_id, Watchlist.good_id == body.good_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="已收藏该饰品")

        item = Watchlist(
            user_id=user_id,
            good_id=body.good_id,
            name=body.name,
            market_hash_name=body.market_hash_name,
            alert_threshold_pct=body.alert_threshold_pct,
            notes=body.notes,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return {
            "id": item.id,
            "good_id": item.good_id,
            "name": item.name,
            "market_hash_name": item.market_hash_name,
            "added_at": item.added_at.isoformat() if item.added_at else None,
            "alert_threshold_pct": item.alert_threshold_pct,
            "notes": item.notes,
        }


@router.delete("/{favorite_id}")
async def delete_favorite(
    favorite_id: int,
    current_user: dict = Depends(get_current_user),
    app: App = Depends(get_app),
):
    user_id = int(current_user["sub"])
    async with app.database.session() as session:
        result = await session.execute(
            select(Watchlist).where(Watchlist.id == favorite_id, Watchlist.user_id == user_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="收藏不存在")
        await session.delete(item)
        await session.commit()
        return {"status": "deleted"}
```

- [ ] **Step 3: Register favorites routes and run tests**

Update `src/csqaq/api/routes/__init__.py`:

```python
from csqaq.api.routes.favorites import router as favorites_router
root.include_router(favorites_router)
```

Run: `python -m pytest tests/test_api/test_favorites.py -v`
Expected: All pass

- [ ] **Step 4: Create Favorites frontend page**

Create `src/pages/Favorites/index.tsx` in csqaq-web:

```tsx
// src/pages/Favorites/index.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, Card, Typography, Button, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { QUERY_KEYS } from '../../utils/constants';
import { formatPrice, formatDate } from '../../utils/format';
import { useAuthStore } from '../../stores/authStore';
import type { WatchlistItem } from '../../types';

const { Title } = Typography;

export default function Favorites() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const { data: favorites = [], isLoading } = useQuery({
    queryKey: QUERY_KEYS.favorites(),
    queryFn: async () => {
      const { data } = await apiClient.get<WatchlistItem[]>('/favorites');
      return data;
    },
    enabled: isAuthenticated,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/favorites/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.favorites() });
      message.success('已取消收藏');
    },
  });

  if (!isAuthenticated) {
    return (
      <div style={{ textAlign: 'center', marginTop: 100 }}>
        <Empty description="请先登录" />
        <Button type="primary" onClick={() => navigate('/login')} style={{ marginTop: 16 }}>
          去登录
        </Button>
      </div>
    );
  }

  const columns = [
    {
      title: '饰品',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: WatchlistItem) => (
        <a onClick={() => navigate(`/item/${record.good_id}`)}>{name}</a>
      ),
    },
    {
      title: '添加时间',
      dataIndex: 'added_at',
      key: 'added_at',
      render: (v: string) => v ? formatDate(v) : '--',
    },
    {
      title: '提醒阈值',
      dataIndex: 'alert_threshold_pct',
      key: 'alert',
      render: (v: number) => `${v}%`,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: WatchlistItem) => (
        <Popconfirm title="确定取消收藏？" onConfirm={() => deleteMutation.mutate(record.id)}>
          <Button type="text" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#fff' }}>我的收藏</Title>
      <Card>
        <Table
          columns={columns}
          dataSource={favorites}
          rowKey="id"
          loading={isLoading}
          size="small"
          locale={{ emptyText: '暂无收藏' }}
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Commit both repos**

Backend:
```bash
git add src/csqaq/api/routes/favorites.py src/csqaq/api/routes/__init__.py tests/test_api/test_favorites.py
git commit -m "feat: add favorites CRUD routes using Watchlist model"
```

Frontend:
```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add . && git commit -m "feat: add Favorites page with list and delete"
```

---

### Task 18: QueryHistory Model + Routes + Profile Page

**Files:**
- Create: `src/csqaq/api/routes/history.py`
- Create: `src/pages/Profile/index.tsx` (in csqaq-web)
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Implement history routes**

Create `src/csqaq/api/routes/history.py`:

```python
# src/csqaq/api/routes/history.py
"""Query history routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from csqaq.api.deps import get_app, get_current_user
from csqaq.infrastructure.database.models import QueryHistory
from csqaq.main import App

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def list_history(
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    app: App = Depends(get_app),
):
    user_id = int(current_user["sub"])
    async with app.database.session() as session:
        result = await session.execute(
            select(QueryHistory)
            .where(QueryHistory.user_id == user_id)
            .order_by(QueryHistory.created_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [
            {
                "id": item.id,
                "query_text": item.query_text,
                "intent": item.intent,
                "summary": item.summary,
                "risk_level": item.risk_level,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
```

Register in `__init__.py`:

```python
from csqaq.api.routes.history import router as history_router
root.include_router(history_router)
```

- [ ] **Step 2: Create Profile page**

Create `src/pages/Profile/index.tsx` in csqaq-web:

```tsx
// src/pages/Profile/index.tsx
import { useQuery } from '@tanstack/react-query';
import { Card, Typography, Descriptions, Table, Button, Empty } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import apiClient from '../../api/client';
import { QUERY_KEYS } from '../../utils/constants';
import { formatDateTime } from '../../utils/format';
import RiskBadge from '../../components/analysis/RiskBadge';
import type { QueryHistoryItem } from '../../types';

const { Title } = Typography;

export default function Profile() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const { data: history = [] } = useQuery({
    queryKey: QUERY_KEYS.history(),
    queryFn: async () => {
      const { data } = await apiClient.get<QueryHistoryItem[]>('/history');
      return data;
    },
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div style={{ textAlign: 'center', marginTop: 100 }}>
        <Empty description="请先登录" />
        <Button type="primary" onClick={() => navigate('/login')} style={{ marginTop: 16 }}>
          去登录
        </Button>
      </div>
    );
  }

  const historyColumns = [
    { title: '查询', dataIndex: 'query_text', key: 'query' },
    { title: '意图', dataIndex: 'intent', key: 'intent' },
    {
      title: '风险',
      dataIndex: 'risk_level',
      key: 'risk',
      render: (v: string) => v ? <RiskBadge level={v} /> : '--',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'time',
      render: (v: string) => v ? formatDateTime(v) : '--',
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#fff' }}>用户中心</Title>

      <Card title="个人信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user?.email}</Descriptions.Item>
        </Descriptions>
        <Button danger onClick={logout} style={{ marginTop: 16 }}>退出登录</Button>
      </Card>

      <Card title="查询历史">
        <Table
          columns={historyColumns}
          dataSource={history}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: '暂无查询记录' }}
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

Backend:
```bash
git add src/csqaq/api/routes/history.py src/csqaq/api/routes/__init__.py
git commit -m "feat: add query history routes"
```

Frontend:
```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add . && git commit -m "feat: add Profile page with user info and query history"
```

---

## Phase 6: Inventory + Polish

### Task 19: Inventory Detail Page

**Files:**
- Create: `src/csqaq/api/routes/inventory.py`
- Create: `src/pages/Inventory/index.tsx` (in csqaq-web)
- Modify: `src/csqaq/api/routes/__init__.py`

- [ ] **Step 1: Create dedicated inventory route**

Create `src/csqaq/api/routes/inventory.py`:

```python
# src/csqaq/api/routes/inventory.py
"""Inventory-specific REST endpoints (beyond item.py's basic inventory data)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from csqaq.api.deps import get_app
from csqaq.main import App

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{item_id}")
async def get_inventory_detail(
    item_id: int,
    app: App = Depends(get_app),
):
    """Get full inventory analysis for an item.

    Returns raw inventory stats plus basic item detail for context.
    """
    detail = await app.item_api.get_item_detail(item_id)
    stats = await app.item_api.get_item_statistic(item_id)

    return {
        "item": detail.model_dump(by_alias=True),
        "inventory_stats": [s.model_dump() for s in stats],
    }
```

Register in `__init__.py`:

```python
from csqaq.api.routes.inventory import router as inventory_router
root.include_router(inventory_router)
```

- [ ] **Step 2: Create Inventory page**

Create `src/pages/Inventory/index.tsx` in csqaq-web:

```tsx
// src/pages/Inventory/index.tsx
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, Typography, Row, Col, Statistic, Spin, Descriptions } from 'antd';
import apiClient from '../../api/client';
import InventoryChart from '../../components/charts/InventoryChart';
import { formatPrice } from '../../utils/format';

const { Title } = Typography;

export default function Inventory() {
  const { id } = useParams<{ id: string }>();
  const itemId = Number(id);

  const { data, isLoading } = useQuery({
    queryKey: ['inventory', 'detail', itemId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/inventory/${itemId}`);
      return data;
    },
    enabled: !isNaN(itemId),
  });

  if (isLoading || !data) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const { item, inventory_stats: stats } = data;

  // Compute basic stats from raw data
  const latest = stats.length > 0 ? stats[stats.length - 1].statistic : 0;
  const earliest = stats.length > 0 ? stats[0].statistic : 0;
  const change = latest - earliest;
  const changeRate = earliest > 0 ? ((change / earliest) * 100) : 0;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <Link to={`/item/${itemId}`} style={{ color: '#1668dc' }}>
          ← 返回 {item.goodName}
        </Link>
      </div>

      <Title level={4} style={{ color: '#fff' }}>存世量分析 - {item.goodName}</Title>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="当前存世量" value={latest} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="区间变化"
              value={change}
              valueStyle={{ color: change < 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="变化率"
              value={changeRate}
              precision={2}
              suffix="%"
              valueStyle={{ color: changeRate < 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="数据天数" value={stats.length} suffix="天" />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }}>
        <InventoryChart data={stats} title="90天存世量趋势" />
      </Card>

      <Card title="当前价格" style={{ marginTop: 16 }}>
        <Descriptions column={4} size="small">
          <Descriptions.Item label="BUFF 售价">¥{formatPrice(item.buffSellPrice)}</Descriptions.Item>
          <Descriptions.Item label="BUFF 在售">{item.buffSellNum}</Descriptions.Item>
          <Descriptions.Item label="Steam 售价">¥{formatPrice(item.steamSellPrice)}</Descriptions.Item>
          <Descriptions.Item label="悠悠有品">¥{formatPrice(item.yyypSellPrice)}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

Backend:
```bash
git add src/csqaq/api/routes/inventory.py src/csqaq/api/routes/__init__.py
git commit -m "feat: add dedicated inventory detail route"
```

Frontend:
```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add . && git commit -m "feat: add Inventory detail page with trend chart and stats"
```

---

### Task 20: High-Risk Confirmation + Responsive Polish

**Files:**
- Modify: `src/components/layout/AppLayout.tsx`
- Modify: `src/components/layout/TopNav.tsx`
- Modify: `src/components/layout/AISidebar.tsx`

All files in `d:/program/PythonWorkSpace/csqaq-web/`.

- [ ] **Step 1: Add responsive styles to TopNav**

Update `src/components/layout/TopNav.tsx` to collapse navigation on small screens:

```tsx
// Add to TopNav:
// Use Ant Design's Grid breakpoint hook
import { Grid } from 'antd';
const { useBreakpoint } = Grid;

// Inside component:
const screens = useBreakpoint();
const isMobile = !screens.md;

// Conditionally show/hide menu items and use Drawer for mobile
// When isMobile: show hamburger icon that opens a Drawer with nav items
// When desktop: show full horizontal Menu
```

Add the hamburger menu pattern with a local state `menuOpen` and Ant Design Drawer for mobile navigation.

- [ ] **Step 2: Make AISidebar responsive**

Update AISidebar to use full-screen drawer on mobile:

```tsx
// In AppLayout.tsx:
const screens = Grid.useBreakpoint();
const drawerWidth = screens.md ? 480 : '100%';

<Drawer width={drawerWidth} ... />
```

- [ ] **Step 3: Verify the ConfirmModal integration**

The ConfirmModal from Task 14 is already integrated in AISidebar. Verify that when `result.requires_confirmation` is true and `result.risk_level === "high"`:

1. The modal appears with the summary
2. Clicking "我了解风险，查看详情" shows `action_detail`
3. Clicking "取消" hides the modal without showing detail

- [ ] **Step 4: Add global CSS resets**

Create `src/index.css` in csqaq-web:

```css
/* src/index.css */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background: #000;
  color: rgba(255, 255, 255, 0.85);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

#root {
  min-height: 100vh;
}

/* Scrollbar styling for dark theme */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}

/* Ant Design overrides for dark theme */
.ant-card {
  background: #141414 !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

.ant-table {
  background: transparent !important;
}
```

Import in `src/main.tsx`:
```tsx
import './index.css';
```

- [ ] **Step 5: Final build verification**

Frontend:
```bash
cd d:/program/PythonWorkSpace/csqaq-web
npm run build
```

Backend (run full test suite):
```bash
cd d:/program/PythonWorkSpace/CSQAQ
python -m pytest tests/test_api/ -v
```

Both should pass with zero errors.

- [ ] **Step 6: Commit**

Frontend:
```bash
cd d:/program/PythonWorkSpace/csqaq-web
git add . && git commit -m "feat: add responsive design, dark theme polish, and global CSS"
```

---

## Final Route Registration Reference

The final `src/csqaq/api/routes/__init__.py` should look like:

```python
# src/csqaq/api/routes/__init__.py
"""Route registration."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, WebSocket


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from csqaq.api.middleware import register_error_handlers
    from csqaq.api.routes.auth import router as auth_router
    from csqaq.api.routes.favorites import router as favorites_router
    from csqaq.api.routes.history import router as history_router
    from csqaq.api.routes.inventory import router as inventory_router
    from csqaq.api.routes.item import router as item_router
    from csqaq.api.routes.market import router as market_router
    from csqaq.api.routes.scout import router as scout_router

    register_error_handlers(app)

    root = APIRouter(prefix="/api/v1")

    @root.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    root.include_router(item_router)
    root.include_router(market_router)
    root.include_router(scout_router)
    root.include_router(inventory_router)
    root.include_router(auth_router)
    root.include_router(favorites_router)
    root.include_router(history_router)

    app.include_router(root)

    # WebSocket endpoint (outside /api/v1 prefix)
    from csqaq.api.ws.analysis import analysis_handler

    @app.websocket("/ws/analysis")
    async def ws_analysis(websocket: WebSocket):
        app_container = websocket.app.state.app
        await analysis_handler(websocket, app_container)
```

---

### Critical Files for Implementation

- `d:/program/PythonWorkSpace/CSQAQ/src/csqaq/api/server.py` - FastAPI application factory, the core entry point for the entire backend API layer
- `d:/program/PythonWorkSpace/CSQAQ/src/csqaq/api/ws/analysis.py` - WebSocket handler with progress streaming, the most complex backend component connecting LangGraph to the frontend
- `d:/program/PythonWorkSpace/CSQAQ/src/csqaq/main.py` - App container that needs `get_router_flow()` for graph pre-compilation and reuse
- `d:/program/PythonWorkSpace/CSQAQ/src/csqaq/api/routes/auth.py` - JWT authentication implementation that all protected routes depend on
- `d:/program/PythonWorkSpace/CSQAQ/src/csqaq/infrastructure/database/models.py` - Database models that need User and QueryHistory additions