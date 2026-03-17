# Phase 1: Infrastructure + Item Analysis Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation infrastructure and a working item analysis pipeline — user can query a CS2 skin via CLI and receive investment analysis from GPT-4o + GPT-5.

**Architecture:** Bottom-up build of the 4-layer architecture. Start with Infrastructure (CSQAQ HTTP client, DB, cache, indicators), then Components (LLM factory, tools, agents), then Flows (LangGraph item + advisor subgraphs), finally API (Typer CLI). Each layer only depends downward.

**Tech Stack:** Python 3.11+, httpx, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 (async + aiosqlite), LangGraph, langchain-openai, pandas, Rich, Typer

**Spec:** `docs/superpowers/specs/2026-03-17-csqaq-multiagent-design.md`

**Scope:** Phase 1 only. Phases 2-4 (Market/Scout/Router agents, background monitoring, server deployment, user auth) will be separate plans after Phase 1 is verified working.

---

## File Structure

All paths relative to project root `CSQAQ/`.

### Create

```
pyproject.toml                                    # Project metadata + dependencies
.gitignore                                        # Ignore .env, data/, __pycache__
.env.example                                      # Template for required env vars

src/csqaq/__init__.py                             # Package marker (empty)
src/csqaq/config.py                               # Pydantic Settings
src/csqaq/main.py                                 # Application entry point + startup

src/csqaq/api/__init__.py
src/csqaq/api/cli.py                              # Typer CLI commands

src/csqaq/flows/__init__.py
src/csqaq/flows/item_flow.py                      # LangGraph item analysis subgraph
src/csqaq/flows/advisor_flow.py                   # LangGraph advisor subgraph (Phase 1: item-only)

src/csqaq/components/__init__.py
src/csqaq/components/agents/__init__.py
src/csqaq/components/agents/item.py               # Item Agent prompt + node logic
src/csqaq/components/agents/advisor.py             # Advisor Agent prompt + node logic
src/csqaq/components/tools/__init__.py
src/csqaq/components/tools/item_tools.py           # LangChain @tool wrappers for item queries
src/csqaq/components/models/__init__.py
src/csqaq/components/models/factory.py             # ModelFactory registry + factory
src/csqaq/components/models/providers.py           # Provider-specific model creation

src/csqaq/infrastructure/__init__.py
src/csqaq/infrastructure/csqaq_client/__init__.py
src/csqaq/infrastructure/csqaq_client/client.py    # Core HTTP client (rate limit, retry)
src/csqaq/infrastructure/csqaq_client/errors.py    # Custom exception hierarchy
src/csqaq/infrastructure/csqaq_client/schemas.py   # Pydantic response models
src/csqaq/infrastructure/csqaq_client/item.py      # Item endpoint methods
src/csqaq/infrastructure/database/__init__.py
src/csqaq/infrastructure/database/connection.py    # async engine + session factory
src/csqaq/infrastructure/database/models.py        # SQLAlchemy ORM models
src/csqaq/infrastructure/cache/__init__.py
src/csqaq/infrastructure/cache/base.py             # Abstract CacheBackend
src/csqaq/infrastructure/cache/memory_cache.py     # In-memory TTL cache
src/csqaq/infrastructure/analysis/__init__.py
src/csqaq/infrastructure/analysis/indicators.py    # Technical indicators (MA, volatility, etc.)

tests/__init__.py
tests/conftest.py                                  # Shared fixtures
tests/fixtures/                                    # JSON API response fixtures
tests/fixtures/suggest_response.json
tests/fixtures/item_detail_response.json
tests/fixtures/chart_response.json
tests/fixtures/kline_response.json
tests/test_infrastructure/__init__.py
tests/test_infrastructure/test_csqaq_client.py     # Client core tests
tests/test_infrastructure/test_item_endpoints.py   # Item endpoint tests
tests/test_infrastructure/test_database.py         # ORM tests
tests/test_infrastructure/test_cache.py            # Cache tests
tests/test_infrastructure/test_indicators.py       # Indicator tests
tests/test_components/__init__.py
tests/test_components/test_model_factory.py        # Factory tests
tests/test_components/test_item_tools.py           # Tool tests
tests/test_flows/__init__.py
tests/test_flows/test_item_flow.py                 # Item flow tests
tests/test_flows/test_advisor_flow.py              # Advisor flow tests
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`
- Create: All `__init__.py` files listed in File Structure
- Create: `tests/conftest.py` (empty placeholder)

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "csqaq"
version = "0.1.0"
description = "CS2 skin market multi-agent analysis system"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2",
    "langchain-openai>=0.2",
    "langchain-community>=0.3",
    "httpx>=0.27",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "apscheduler>=3.10,<4.0",
    "chromadb>=0.5",
    "rich>=13.0",
    "typer>=0.12",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
]
server = [
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "websockets>=12.0",
    "redis>=5.0",
    "asyncpg>=0.29",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "cryptography>=43.0",
]

[project.scripts]
csqaq = "csqaq.main:cli_entry"

[tool.hatch.build.targets.wheel]
packages = ["src/csqaq"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create .gitignore**

```
.env
data/
*.db
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 3: Create .env.example**

```
# CSQAQ API (required for local mode)
CSQAQ_API_TOKEN=your_csqaq_api_token_here
CSQAQ_BASE_URL=https://api.csqaq.com/api/v1

# OpenAI (required for local mode)
OPENAI_API_KEY=your_openai_api_key_here

# Model configuration
ROUTER_MODEL=gpt-4o-mini
ANALYST_MODEL=gpt-4o
ADVISOR_MODEL=gpt-5

# Database
DATABASE_URL=sqlite:///data/csqaq.db

# Optional
# REDIS_URL=redis://localhost:6379/0
# SECRET_KEY=your-secret-key
```

- [ ] **Step 4: Create all directory structure and __init__.py files**

```bash
mkdir -p src/csqaq/{api,flows,components/{agents,tools,models},infrastructure/{csqaq_client,database,cache,analysis}}
mkdir -p tests/{fixtures,test_infrastructure,test_components,test_flows}
touch src/csqaq/__init__.py
touch src/csqaq/{api,flows,components,infrastructure}/__init__.py
touch src/csqaq/components/{agents,tools,models}/__init__.py
touch src/csqaq/infrastructure/{csqaq_client,database,cache,analysis}/__init__.py
touch tests/__init__.py tests/conftest.py
touch tests/{test_infrastructure,test_components,test_flows}/__init__.py
```

- [ ] **Step 5: Install project in dev mode and verify**

```bash
pip install -e ".[dev]"
pytest --co -q
```

Expected: No collection errors, 0 tests collected.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/ tests/
git commit -m "chore: scaffold project structure with dependencies"
```

---

## Task 2: Configuration

**Files:**
- Create: `src/csqaq/config.py`
- Test: `tests/test_infrastructure/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infrastructure/test_config.py
import os
import pytest
from csqaq.config import Settings


def test_settings_loads_defaults():
    """Settings should load with defaults when required fields are provided."""
    settings = Settings(
        csqaq_api_token="test-token",
        openai_api_key="test-key",
    )
    assert settings.csqaq_base_url == "https://api.csqaq.com/api/v1"
    assert settings.csqaq_rate_limit == 1.0
    assert settings.router_model == "gpt-4o-mini"
    assert settings.analyst_model == "gpt-4o"
    assert settings.advisor_model == "gpt-5"
    assert settings.database_url == "sqlite:///data/csqaq.db"
    assert settings.mode == "local"
    assert settings.api_cache_ttl == 60
    assert settings.daily_token_budget == 500_000
    assert settings.monthly_token_budget == 10_000_000


def test_settings_local_mode_requires_tokens():
    """In local mode, csqaq_api_token and openai_api_key are required."""
    settings = Settings(
        csqaq_api_token="tok",
        openai_api_key="key",
        mode="local",
    )
    assert settings.csqaq_api_token == "tok"
    assert settings.openai_api_key == "key"


def test_settings_server_mode_allows_empty_tokens():
    """In server mode, tokens can be empty (users bind their own)."""
    settings = Settings(
        mode="server",
        secret_key="test-secret",
    )
    assert settings.csqaq_api_token == ""
    assert settings.openai_api_key == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'csqaq.config'`

- [ ] **Step 3: Implement config.py**

```python
# src/csqaq/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Runtime mode
    mode: str = "local"  # "local" | "server"

    # CSQAQ API
    csqaq_api_token: str = ""
    csqaq_base_url: str = "https://api.csqaq.com/api/v1"
    csqaq_rate_limit: float = 1.0

    # OpenAI
    openai_api_key: str = ""
    router_model: str = "gpt-4o-mini"
    analyst_model: str = "gpt-4o"
    advisor_model: str = "gpt-5"

    # Database
    database_url: str = "sqlite:///data/csqaq.db"

    # Cache
    redis_url: str | None = None
    api_cache_ttl: int = 60

    # Monitoring
    watchlist_poll_interval: int = 300
    market_poll_interval: int = 300
    scout_scan_interval: int = 1800
    alert_price_threshold_pct: float = 5.0

    # Memory
    max_history_messages: int = 20
    chromadb_path: str = "data/chroma"

    # Cost control
    daily_token_budget: int = 500_000
    monthly_token_budget: int = 10_000_000

    # Auth (server mode)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Notifications (server mode)
    notify_webhook_url: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_infrastructure/test_config.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/config.py tests/test_infrastructure/test_config.py
git commit -m "feat: add pydantic-settings configuration"
```

---

## Task 3: CSQAQ Client Core

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/errors.py`
- Create: `src/csqaq/infrastructure/csqaq_client/client.py`
- Test: `tests/test_infrastructure/test_csqaq_client.py`

The client handles: httpx async requests, `ApiToken` header injection, token bucket rate limiting (1 req/sec), exponential backoff retry (max 3), and custom error mapping.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_infrastructure/test_csqaq_client.py
import asyncio
import time

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.errors import (
    CSQAQAuthError,
    CSQAQClientError,
    CSQAQRateLimitError,
    CSQAQServerError,
    CSQAQValidationError,
)


@pytest.fixture
def base_url():
    return "https://api.csqaq.com/api/v1"


@pytest.fixture
def client(base_url):
    return CSQAQClient(
        base_url=base_url,
        api_token="test-token",
        rate_limit=10.0,  # Fast for tests
    )


@respx.mock
@pytest.mark.asyncio
async def test_post_injects_api_token_header(client, base_url):
    """Every request must include the ApiToken header."""
    route = respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": {}})
    )
    result = await client.post("/test", json={})
    assert route.called
    assert route.calls[0].request.headers["ApiToken"] == "test-token"


@respx.mock
@pytest.mark.asyncio
async def test_post_returns_data_field(client, base_url):
    """Client should extract and return the 'data' field from response."""
    respx.post(f"{base_url}/info/good").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": {"name": "AK-47"}})
    )
    result = await client.post("/info/good", json={"goodId": 1})
    assert result == {"name": "AK-47"}


@respx.mock
@pytest.mark.asyncio
async def test_raises_auth_error_on_401(client, base_url):
    """401 should raise CSQAQAuthError without retry."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(401, json={"code": -1, "msg": "unauthorized"})
    )
    with pytest.raises(CSQAQAuthError):
        await client.post("/test", json={})


@respx.mock
@pytest.mark.asyncio
async def test_raises_validation_error_on_422(client, base_url):
    """422 should raise CSQAQValidationError without retry."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(422, json={"code": -1, "msg": "bad params"})
    )
    with pytest.raises(CSQAQValidationError):
        await client.post("/test", json={})


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_500_then_succeeds(client, base_url):
    """Server errors should be retried up to 3 times."""
    route = respx.post(f"{base_url}/test")
    route.side_effect = [
        httpx.Response(500, json={"code": -1, "msg": "server error"}),
        httpx.Response(200, json={"code": 0, "data": {"ok": True}}),
    ]
    result = await client.post("/test", json={})
    assert result == {"ok": True}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_raises_after_max_retries(client, base_url):
    """After 3 retries on 500, should raise CSQAQServerError."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(500, json={"code": -1, "msg": "down"})
    )
    with pytest.raises(CSQAQServerError):
        await client.post("/test", json={})


@pytest.mark.asyncio
async def test_rate_limiter_enforces_interval():
    """Rate limiter should space requests by 1/rate_limit seconds."""
    client = CSQAQClient(
        base_url="https://api.csqaq.com/api/v1",
        api_token="test",
        rate_limit=5.0,  # 5 req/sec → 0.2s interval
    )
    # Just verify the rate limiter exists and has correct interval
    assert client._min_interval == pytest.approx(0.2, abs=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_infrastructure/test_csqaq_client.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement errors.py**

```python
# src/csqaq/infrastructure/csqaq_client/errors.py

class CSQAQClientError(Exception):
    """Base exception for CSQAQ API client."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class CSQAQAuthError(CSQAQClientError):
    """401/403 — token invalid or IP not bound."""


class CSQAQValidationError(CSQAQClientError):
    """422 — request parameters invalid."""


class CSQAQRateLimitError(CSQAQClientError):
    """429 — rate limit exceeded."""


class CSQAQServerError(CSQAQClientError):
    """5xx — CSQAQ server error."""
```

- [ ] **Step 4: Implement client.py**

```python
# src/csqaq/infrastructure/csqaq_client/client.py
import asyncio
import logging
import time

import httpx

from .errors import (
    CSQAQAuthError,
    CSQAQClientError,
    CSQAQRateLimitError,
    CSQAQServerError,
    CSQAQValidationError,
)

logger = logging.getLogger(__name__)

# Errors that should NOT be retried
_NO_RETRY_CODES = {401, 403, 422}

# Errors that SHOULD be retried
_RETRY_CODES = {429, 500, 502, 503, 504}


class CSQAQClient:
    """Async HTTP client for CSQAQ API with rate limiting and retry."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._max_retries = max_retries
        self._min_interval = 1.0 / rate_limit
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"ApiToken": api_token, "Content-Type": "application/json"},
        )

    async def _wait_for_rate_limit(self) -> None:
        """Token bucket: ensure minimum interval between requests."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def post(self, path: str, json: dict, priority: int = 0) -> dict:
        """Send POST request with rate limiting and retry.

        Args:
            path: API endpoint path (e.g. "/info/good")
            json: Request body
            priority: Request priority (0=interactive, 1=alert, 2=background)

        Returns:
            The 'data' field from the API response.

        Raises:
            CSQAQAuthError: 401/403
            CSQAQValidationError: 422
            CSQAQRateLimitError: 429 after retries exhausted
            CSQAQServerError: 5xx after retries exhausted
        """
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                response = await self._http.post(url, json=json)
            except httpx.TransportError as e:
                last_error = CSQAQClientError(f"Network error: {e}")
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_error from e

            if response.status_code == 200:
                body = response.json()
                return body.get("data", body)

            # Non-retryable errors
            if response.status_code in (401, 403):
                raise CSQAQAuthError(
                    f"Authentication failed: {response.text}",
                    status_code=response.status_code,
                )
            if response.status_code == 422:
                raise CSQAQValidationError(
                    f"Validation error: {response.text}",
                    status_code=422,
                )

            # Retryable errors
            if response.status_code in _RETRY_CODES:
                last_error = (
                    CSQAQRateLimitError("Rate limited", status_code=429)
                    if response.status_code == 429
                    else CSQAQServerError(
                        f"Server error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                )
                if attempt < self._max_retries:
                    logger.warning(
                        "CSQAQ API %s returned %d, retry %d/%d",
                        path, response.status_code, attempt + 1, self._max_retries,
                    )
                    await self._backoff(attempt)
                    continue

            # Unknown status code
            if last_error is None:
                last_error = CSQAQClientError(
                    f"Unexpected status {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )
            break

        raise last_error  # type: ignore[misc]

    async def _backoff(self, attempt: int) -> None:
        delay = min(2**attempt * 0.5, 10.0)
        await asyncio.sleep(delay)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_csqaq_client.py -v
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/errors.py src/csqaq/infrastructure/csqaq_client/client.py tests/test_infrastructure/test_csqaq_client.py
git commit -m "feat: add CSQAQ API client with rate limiting and retry"
```

---

## Task 4: CSQAQ API Response Schemas

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/schemas.py`
- Create: `tests/fixtures/suggest_response.json`, `tests/fixtures/item_detail_response.json`, `tests/fixtures/chart_response.json`, `tests/fixtures/kline_response.json`
- Test: `tests/test_infrastructure/test_schemas.py`

These Pydantic models parse CSQAQ API responses. Field names use snake_case internally; `model_config` with `populate_by_name=True` allows both alias (API camelCase) and snake_case access.

- [ ] **Step 1: Create JSON fixtures**

These represent realistic CSQAQ API response `data` payloads. Create each file under `tests/fixtures/`.

`tests/fixtures/suggest_response.json`:
```json
[
    {
        "goodId": 7310,
        "goodName": "AK-47 | 红线 (久经沙场)",
        "marketHashName": "AK-47 | Redline (Field-Tested)",
        "imageUrl": "https://img.csqaq.com/ak47_redline.png"
    },
    {
        "goodId": 7311,
        "goodName": "AK-47 | 红线 (略有磨损)",
        "marketHashName": "AK-47 | Redline (Minimal Wear)",
        "imageUrl": "https://img.csqaq.com/ak47_redline_mw.png"
    }
]
```

`tests/fixtures/item_detail_response.json`:
```json
{
    "goodId": 7310,
    "goodName": "AK-47 | 红线 (久经沙场)",
    "marketHashName": "AK-47 | Redline (Field-Tested)",
    "imageUrl": "https://img.csqaq.com/ak47_redline.png",
    "buffSellPrice": 85.50,
    "buffBuyPrice": 82.00,
    "steamSellPrice": 12.35,
    "yyypSellPrice": 80.00,
    "buffSellNum": 15234,
    "buffBuyNum": 8921,
    "steamSellNum": 4521,
    "dailyChangeRate": 1.25,
    "weeklyChangeRate": -2.30,
    "monthlyChangeRate": 5.60,
    "category": "步枪",
    "rarity": "保密",
    "exterior": "久经沙场"
}
```

`tests/fixtures/chart_response.json`:
```json
{
    "goodId": 7310,
    "platform": "buff",
    "period": "30d",
    "points": [
        {"timestamp": 1710633600, "price": 83.00, "volume": 520},
        {"timestamp": 1710720000, "price": 84.50, "volume": 480},
        {"timestamp": 1710806400, "price": 85.50, "volume": 510}
    ]
}
```

`tests/fixtures/kline_response.json`:
```json
[
    {
        "timestamp": 1710633600,
        "open": 83.00,
        "close": 84.50,
        "high": 85.00,
        "low": 82.50,
        "volume": 520
    },
    {
        "timestamp": 1710720000,
        "open": 84.50,
        "close": 85.50,
        "high": 86.00,
        "low": 84.00,
        "volume": 480
    }
]
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_infrastructure/test_schemas.py
import json
from pathlib import Path

import pytest

from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ChartPoint,
    ItemDetail,
    KlineBar,
    SuggestItem,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_suggest_item_parses_from_api():
    raw = json.loads((FIXTURES / "suggest_response.json").read_text())
    items = [SuggestItem.model_validate(r) for r in raw]
    assert len(items) == 2
    assert items[0].good_id == 7310
    assert items[0].good_name == "AK-47 | 红线 (久经沙场)"
    assert items[0].market_hash_name == "AK-47 | Redline (Field-Tested)"


def test_item_detail_parses_from_api():
    raw = json.loads((FIXTURES / "item_detail_response.json").read_text())
    detail = ItemDetail.model_validate(raw)
    assert detail.good_id == 7310
    assert detail.buff_sell_price == 85.50
    assert detail.daily_change_rate == 1.25
    assert detail.category == "步枪"


def test_chart_data_parses_from_api():
    raw = json.loads((FIXTURES / "chart_response.json").read_text())
    chart = ChartData.model_validate(raw)
    assert chart.good_id == 7310
    assert len(chart.points) == 3
    assert chart.points[0].price == 83.00


def test_kline_bar_parses_from_api():
    raw = json.loads((FIXTURES / "kline_response.json").read_text())
    bars = [KlineBar.model_validate(r) for r in raw]
    assert len(bars) == 2
    assert bars[0].open == 83.00
    assert bars[1].close == 85.50
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement schemas.py**

```python
# src/csqaq/infrastructure/csqaq_client/schemas.py
from pydantic import BaseModel, Field


class SuggestItem(BaseModel):
    """Search suggestion result."""
    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    good_name: str = Field(alias="goodName")
    market_hash_name: str = Field(alias="marketHashName")
    image_url: str = Field(alias="imageUrl")


class ItemDetail(BaseModel):
    """Full item detail with multi-platform prices."""
    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    good_name: str = Field(alias="goodName")
    market_hash_name: str = Field(alias="marketHashName")
    image_url: str = Field(alias="imageUrl")

    buff_sell_price: float = Field(alias="buffSellPrice")
    buff_buy_price: float = Field(alias="buffBuyPrice")
    steam_sell_price: float = Field(alias="steamSellPrice")
    yyyp_sell_price: float = Field(alias="yyypSellPrice")

    buff_sell_num: int = Field(alias="buffSellNum")
    buff_buy_num: int = Field(alias="buffBuyNum")
    steam_sell_num: int = Field(alias="steamSellNum")

    daily_change_rate: float = Field(alias="dailyChangeRate")
    weekly_change_rate: float = Field(alias="weeklyChangeRate")
    monthly_change_rate: float = Field(alias="monthlyChangeRate")

    category: str = ""
    rarity: str = ""
    exterior: str = ""


class ChartPoint(BaseModel):
    """Single data point in a price chart."""
    timestamp: int
    price: float
    volume: int


class ChartData(BaseModel):
    """Price chart for an item on a specific platform."""
    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    platform: str
    period: str
    points: list[ChartPoint]


class KlineBar(BaseModel):
    """Single K-line (candlestick) bar."""
    timestamp: int
    open: float
    close: float
    high: float
    low: float
    volume: int
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_schemas.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/schemas.py tests/fixtures/ tests/test_infrastructure/test_schemas.py
git commit -m "feat: add Pydantic schemas for CSQAQ API responses"
```

---

## Task 5: CSQAQ Client Item Endpoints

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/item.py`
- Test: `tests/test_infrastructure/test_item_endpoints.py`

Thin layer that calls `CSQAQClient.post()` and parses responses into schema models.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infrastructure/test_item_endpoints.py
import json
from pathlib import Path

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.item import ItemAPI
from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    KlineBar,
    SuggestItem,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASE = "https://api.csqaq.com/api/v1"


@pytest.fixture
def client():
    return CSQAQClient(base_url=BASE, api_token="test", rate_limit=100.0)


@pytest.fixture
def item_api(client):
    return ItemAPI(client)


@respx.mock
@pytest.mark.asyncio
async def test_search_suggest(item_api):
    data = json.loads((FIXTURES / "suggest_response.json").read_text())
    respx.post(f"{BASE}/search/suggest").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    results = await item_api.search_suggest("AK红线")
    assert len(results) == 2
    assert isinstance(results[0], SuggestItem)
    assert results[0].good_id == 7310


@respx.mock
@pytest.mark.asyncio
async def test_get_item_detail(item_api):
    data = json.loads((FIXTURES / "item_detail_response.json").read_text())
    respx.post(f"{BASE}/info/good").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    detail = await item_api.get_item_detail(7310)
    assert isinstance(detail, ItemDetail)
    assert detail.buff_sell_price == 85.50


@respx.mock
@pytest.mark.asyncio
async def test_get_item_chart(item_api):
    data = json.loads((FIXTURES / "chart_response.json").read_text())
    respx.post(f"{BASE}/info/chart").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    chart = await item_api.get_item_chart(7310, platform="buff", period="30d")
    assert isinstance(chart, ChartData)
    assert len(chart.points) == 3


@respx.mock
@pytest.mark.asyncio
async def test_get_item_kline(item_api):
    data = json.loads((FIXTURES / "kline_response.json").read_text())
    respx.post(f"{BASE}/info/simple/chartAll").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    bars = await item_api.get_item_kline(7310, platform="buff", periods="30d")
    assert len(bars) == 2
    assert isinstance(bars[0], KlineBar)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_item_endpoints.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement item.py**

```python
# src/csqaq/infrastructure/csqaq_client/item.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .schemas import ChartData, ItemDetail, KlineBar, SuggestItem

if TYPE_CHECKING:
    from .client import CSQAQClient


class ItemAPI:
    """CSQAQ item-related API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def search_suggest(self, text: str) -> list[SuggestItem]:
        """Search for items by name. POST /search/suggest"""
        data = await self._client.post("/search/suggest", json={"text": text})
        if isinstance(data, list):
            return [SuggestItem.model_validate(item) for item in data]
        return []

    async def get_item_detail(self, good_id: int) -> ItemDetail:
        """Get full item detail. POST /info/good"""
        data = await self._client.post("/info/good", json={"goodId": good_id})
        return ItemDetail.model_validate(data)

    async def get_item_chart(
        self,
        good_id: int,
        platform: str = "buff",
        period: str = "30d",
        key: str = "sellPrice",
    ) -> ChartData:
        """Get price chart data. POST /info/chart"""
        data = await self._client.post(
            "/info/chart",
            json={
                "goodId": good_id,
                "key": key,
                "platform": platform,
                "period": period,
            },
        )
        return ChartData.model_validate(data)

    async def get_item_kline(
        self,
        good_id: int,
        platform: str = "buff",
        periods: str = "30d",
        max_time: int | None = None,
    ) -> list[KlineBar]:
        """Get K-line data. POST /info/simple/chartAll"""
        body: dict = {
            "goodId": good_id,
            "plat": platform,
            "periods": periods,
        }
        if max_time is not None:
            body["maxTime"] = max_time
        data = await self._client.post("/info/simple/chartAll", json=body)
        if isinstance(data, list):
            return [KlineBar.model_validate(bar) for bar in data]
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_item_endpoints.py -v
```

Expected: 4 passed

- [ ] **Step 5: Update csqaq_client __init__.py for convenient imports**

```python
# src/csqaq/infrastructure/csqaq_client/__init__.py
from .client import CSQAQClient
from .errors import (
    CSQAQAuthError,
    CSQAQClientError,
    CSQAQRateLimitError,
    CSQAQServerError,
    CSQAQValidationError,
)
from .item import ItemAPI
from .schemas import ChartData, ChartPoint, ItemDetail, KlineBar, SuggestItem

__all__ = [
    "CSQAQClient",
    "CSQAQAuthError",
    "CSQAQClientError",
    "CSQAQRateLimitError",
    "CSQAQServerError",
    "CSQAQValidationError",
    "ItemAPI",
    "ChartData",
    "ChartPoint",
    "ItemDetail",
    "KlineBar",
    "SuggestItem",
]
```

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/ tests/test_infrastructure/test_item_endpoints.py
git commit -m "feat: add CSQAQ item API endpoints with typed responses"
```

---

## Task 6: Database Layer

**Files:**
- Create: `src/csqaq/infrastructure/database/connection.py`
- Create: `src/csqaq/infrastructure/database/models.py`
- Test: `tests/test_infrastructure/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infrastructure/test_database.py
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from csqaq.infrastructure.database.connection import Database
from csqaq.infrastructure.database.models import Alert, Base, PriceSnapshot, Watchlist


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_converts_sqlite_url():
    """Database class should auto-convert sqlite:/// to sqlite+aiosqlite:///."""
    db = Database("sqlite:///data/test.db")
    # Verify it doesn't crash and the engine URL was converted
    assert "aiosqlite" in str(db._engine.url)
    await db.close()


@pytest.mark.asyncio
async def test_database_init_creates_tables():
    """Database.init() should create all tables."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    async with db.session() as session:
        # Should not raise — tables exist
        result = await session.execute(select(Watchlist))
        assert result.all() == []
    await db.close()


@pytest.mark.asyncio
async def test_create_watchlist_item(db_session: AsyncSession):
    item = Watchlist(good_id=7310, name="AK-47 | 红线", market_hash_name="AK-47 | Redline (FT)")
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(Watchlist).where(Watchlist.good_id == 7310))
    row = result.scalar_one()
    assert row.name == "AK-47 | 红线"
    assert row.alert_threshold_pct == 5.0  # default


@pytest.mark.asyncio
async def test_create_price_snapshot(db_session: AsyncSession):
    snap = PriceSnapshot(
        good_id=7310,
        buff_sell=85.5,
        buff_buy=82.0,
        steam_sell=12.35,
        yyyp_sell=80.0,
        sell_num=15234,
        buy_num=8921,
    )
    db_session.add(snap)
    await db_session.commit()

    result = await db_session.execute(select(PriceSnapshot).where(PriceSnapshot.good_id == 7310))
    row = result.scalar_one()
    assert row.buff_sell == 85.5


@pytest.mark.asyncio
async def test_create_alert(db_session: AsyncSession):
    alert = Alert(
        alert_type="price_change",
        good_id=7310,
        title="AK红线涨幅异常",
        message="日涨幅 8.5%，超过阈值 5%",
        data_snapshot={"price": 85.5, "change": 8.5},
    )
    db_session.add(alert)
    await db_session.commit()

    result = await db_session.execute(select(Alert))
    row = result.scalar_one()
    assert row.alert_type == "price_change"
    assert row.acknowledged is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_database.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement models.py**

```python
# src/csqaq/infrastructure/database/models.py
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    good_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market_hash_name: Mapped[str] = mapped_column(String(255), default="")
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    alert_threshold_pct: Mapped[float] = mapped_column(Float, default=5.0)
    notes: Mapped[str] = mapped_column(Text, default="")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    good_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    buff_sell: Mapped[float] = mapped_column(Float, default=0.0)
    buff_buy: Mapped[float] = mapped_column(Float, default=0.0)
    steam_sell: Mapped[float] = mapped_column(Float, default=0.0)
    yyyp_sell: Mapped[float] = mapped_column(Float, default=0.0)
    sell_num: Mapped[int] = mapped_column(Integer, default=0)
    buy_num: Mapped[int] = mapped_column(Integer, default=0)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    good_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    data_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    agent_role: Mapped[str] = mapped_column(String(50), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Implement connection.py**

```python
# src/csqaq/infrastructure/database/connection.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


class Database:
    """Manages async SQLAlchemy engine and session factory."""

    def __init__(self, url: str):
        # Convert sqlite:/// to sqlite+aiosqlite:///
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init(self) -> None:
        """Create all tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def session(self) -> AsyncSession:
        return self._session_factory()

    async def close(self) -> None:
        await self._engine.dispose()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_database.py -v
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/database/ tests/test_infrastructure/test_database.py
git commit -m "feat: add SQLAlchemy async database layer with ORM models"
```

---

## Task 7: Memory Cache

**Files:**
- Create: `src/csqaq/infrastructure/cache/base.py`
- Create: `src/csqaq/infrastructure/cache/memory_cache.py`
- Test: `tests/test_infrastructure/test_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infrastructure/test_cache.py
import asyncio
import pytest
from csqaq.infrastructure.cache.memory_cache import MemoryCache


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key():
    cache = MemoryCache()
    assert await cache.get("nonexistent") is None


@pytest.mark.asyncio
async def test_set_and_get():
    cache = MemoryCache()
    await cache.set("key1", {"price": 85.5}, ttl=60)
    result = await cache.get("key1")
    assert result == {"price": 85.5}


@pytest.mark.asyncio
async def test_ttl_expiry():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=0)  # expires immediately
    await asyncio.sleep(0.01)
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_delete():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=60)
    await cache.delete("key1")
    assert await cache.get("key1") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_cache.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement base.py**

```python
# src/csqaq/infrastructure/cache/base.py
from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value by key. Returns None if not found or expired."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set value with TTL in seconds."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key."""
```

- [ ] **Step 4: Implement memory_cache.py**

```python
# src/csqaq/infrastructure/cache/memory_cache.py
import time
from typing import Any

from .base import CacheBackend


class MemoryCache(CacheBackend):
    """In-memory cache with TTL expiry. Used in local mode."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_cache.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/cache/ tests/test_infrastructure/test_cache.py
git commit -m "feat: add in-memory cache with TTL support"
```

---

## Task 8: Technical Indicators Engine

**Files:**
- Create: `src/csqaq/infrastructure/analysis/indicators.py`
- Test: `tests/test_infrastructure/test_indicators.py`

Pure functions — no I/O, no LLM. These compute numerical indicators from price/volume data. Agents consume the output.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infrastructure/test_indicators.py
import pytest
from csqaq.infrastructure.analysis.indicators import TechnicalIndicators


class TestMovingAverage:
    def test_basic_ma(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = TechnicalIndicators.moving_average(prices, window=3)
        # MA(3) for [10,20,30,40,50] = [None, None, 20.0, 30.0, 40.0]
        assert result == [None, None, 20.0, 30.0, 40.0]

    def test_window_larger_than_data(self):
        prices = [10.0, 20.0]
        result = TechnicalIndicators.moving_average(prices, window=5)
        assert result == [None, None]


class TestVolatility:
    def test_constant_prices_zero_volatility(self):
        prices = [100.0, 100.0, 100.0, 100.0]
        assert TechnicalIndicators.volatility(prices, window=3) == pytest.approx(0.0, abs=0.001)

    def test_volatile_prices(self):
        prices = [100.0, 110.0, 90.0, 105.0, 95.0]
        vol = TechnicalIndicators.volatility(prices, window=5)
        assert vol > 0


class TestPriceMomentum:
    def test_positive_momentum(self):
        prices = [100.0, 105.0, 110.0, 115.0]
        mom = TechnicalIndicators.price_momentum(prices, period=3)
        assert mom == pytest.approx(15.0, abs=0.01)  # 115 - 100

    def test_negative_momentum(self):
        prices = [100.0, 95.0, 90.0, 85.0]
        mom = TechnicalIndicators.price_momentum(prices, period=3)
        assert mom == pytest.approx(-15.0, abs=0.01)


class TestPlatformSpread:
    def test_spread_calculation(self):
        # Buff 85.5, Steam 12.35 USD ≈ 89.7 CNY (not directly comparable)
        # Spread between Buff and YYYP
        spread = TechnicalIndicators.platform_spread(85.5, 80.0)
        assert spread == pytest.approx(6.875, abs=0.01)  # (85.5-80)/80*100


class TestVolumeTrend:
    def test_increasing_volume(self):
        volumes = [100, 200, 300, 400, 500]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "increasing"

    def test_decreasing_volume(self):
        volumes = [500, 400, 300, 200, 100]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "decreasing"

    def test_stable_volume(self):
        volumes = [100, 101, 99, 100, 100]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "stable"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_infrastructure/test_indicators.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement indicators.py**

```python
# src/csqaq/infrastructure/analysis/indicators.py
import statistics


class TechnicalIndicators:
    """Pure numerical computations for technical analysis.

    Agents don't do math — this module does.
    """

    @staticmethod
    def moving_average(prices: list[float], window: int) -> list[float | None]:
        """Simple Moving Average. Returns None for positions with insufficient data."""
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < window - 1:
                result.append(None)
            else:
                window_slice = prices[i - window + 1 : i + 1]
                result.append(sum(window_slice) / window)
        return result

    @staticmethod
    def volatility(prices: list[float], window: int) -> float:
        """Standard deviation of price changes over the window.

        Returns 0.0 if fewer than 2 data points in window.
        """
        if len(prices) < 2:
            return 0.0
        recent = prices[-window:] if len(prices) >= window else prices
        if len(recent) < 2:
            return 0.0
        return statistics.stdev(recent)

    @staticmethod
    def price_momentum(prices: list[float], period: int) -> float:
        """Price change over a period: current - price_N_periods_ago."""
        if len(prices) <= period:
            return prices[-1] - prices[0] if len(prices) >= 2 else 0.0
        return prices[-1] - prices[-1 - period]

    @staticmethod
    def platform_spread(price_a: float, price_b: float) -> float:
        """Percentage spread between two platform prices.

        Returns (a - b) / b * 100. Positive means A is more expensive.
        """
        if price_b == 0:
            return 0.0
        return (price_a - price_b) / price_b * 100

    @staticmethod
    def volume_trend(volumes: list[int], window: int) -> str:
        """Classify recent volume trend as 'increasing', 'decreasing', or 'stable'.

        Compares average of last `window` volumes to the `window` before that.
        Uses a 10% threshold for classification.
        """
        if len(volumes) < window * 2:
            return "stable"
        recent = volumes[-window:]
        previous = volumes[-window * 2 : -window]
        avg_recent = sum(recent) / len(recent)
        avg_previous = sum(previous) / len(previous)
        if avg_previous == 0:
            return "stable"
        change_pct = (avg_recent - avg_previous) / avg_previous * 100
        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        return "stable"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_infrastructure/test_indicators.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/infrastructure/analysis/indicators.py tests/test_infrastructure/test_indicators.py
git commit -m "feat: add technical indicators engine (MA, volatility, momentum, spread)"
```

---

## Task 9: LLM Model Factory

**Files:**
- Create: `src/csqaq/components/models/factory.py`
- Create: `src/csqaq/components/models/providers.py`
- Test: `tests/test_components/test_model_factory.py`

Registry + Factory pattern. Config-driven model selection. Each agent role maps to a (provider, model_name) tuple.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_components/test_model_factory.py
import pytest
from unittest.mock import patch
from csqaq.components.models.factory import ModelConfig, ModelFactory


def test_register_and_get_config():
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini", temperature=0.0)
    config = factory.get_config("router")
    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.0


def test_get_config_unknown_role_raises():
    factory = ModelFactory()
    with pytest.raises(KeyError, match="unknown_role"):
        factory.get_config("unknown_role")


def test_register_multiple_roles():
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini")
    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    assert factory.get_config("router").model == "gpt-4o-mini"
    assert factory.get_config("analyst").model == "gpt-4o"
    assert factory.get_config("advisor").model == "gpt-5"


def test_create_model_returns_chat_model():
    """Verify create_model calls the right provider and returns a model."""
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini", temperature=0.0)
    # Mock the actual OpenAI model creation to avoid needing API key
    with patch("csqaq.components.models.providers.ChatOpenAI") as mock_cls:
        mock_cls.return_value = "mock_model"
        model = factory.create("router")
        mock_cls.assert_called_once_with(model="gpt-4o-mini", temperature=0.0)
        assert model == "mock_model"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_components/test_model_factory.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement factory.py and providers.py**

```python
# src/csqaq/components/models/factory.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel


@dataclass
class ModelConfig:
    provider: str
    model: str
    temperature: float = 0.7
    extra: dict[str, Any] = field(default_factory=dict)


class ModelFactory:
    """Registry + Factory for LLM models. Config-driven, no code changes needed to switch models."""

    def __init__(self):
        self._registry: dict[str, ModelConfig] = {}

    def register(self, role: str, provider: str, model: str, temperature: float = 0.7, **kwargs: Any) -> None:
        self._registry[role] = ModelConfig(
            provider=provider, model=model, temperature=temperature, extra=kwargs,
        )

    def get_config(self, role: str) -> ModelConfig:
        if role not in self._registry:
            raise KeyError(f"No model registered for role: {role}")
        return self._registry[role]

    def create(self, role: str) -> BaseChatModel:
        config = self.get_config(role)
        return _create_model(config)


def _create_model(config: ModelConfig) -> BaseChatModel:
    from .providers import create_openai_model

    creators = {
        "openai": create_openai_model,
    }
    creator = creators.get(config.provider)
    if creator is None:
        raise ValueError(f"Unknown provider: {config.provider}")
    return creator(config)
```

```python
# src/csqaq/components/models/providers.py
from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from .factory import ModelConfig


def create_openai_model(config: ModelConfig) -> ChatOpenAI:
    return ChatOpenAI(model=config.model, temperature=config.temperature, **config.extra)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_components/test_model_factory.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/models/ tests/test_components/test_model_factory.py
git commit -m "feat: add LLM model factory with registry pattern"
```

---

## Task 10: Item Tools

**Files:**
- Create: `src/csqaq/components/tools/item_tools.py`
- Test: `tests/test_components/test_item_tools.py`

LangChain `@tool` wrappers that agents can call. Each tool delegates to `ItemAPI` + `MemoryCache` + `TechnicalIndicators`. Tools accept simple types (str/int) so the LLM can invoke them.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_components/test_item_tools.py
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ChartPoint,
    ItemDetail,
    KlineBar,
    SuggestItem,
)
from csqaq.components.tools.item_tools import create_item_tools

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_item_api():
    api = AsyncMock()

    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text())
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text())
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text())
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text())
    api.get_item_kline.return_value = [KlineBar.model_validate(k) for k in kline_data]

    return api


@pytest.fixture
def tools(mock_item_api):
    return create_item_tools(mock_item_api)


@pytest.mark.asyncio
async def test_search_item_tool(tools, mock_item_api):
    search_tool = next(t for t in tools if t.name == "search_item")
    result = await search_tool.ainvoke({"query": "AK红线"})
    mock_item_api.search_suggest.assert_called_once_with("AK红线")
    assert "7310" in result
    assert "AK-47" in result


@pytest.mark.asyncio
async def test_get_item_detail_tool(tools, mock_item_api):
    detail_tool = next(t for t in tools if t.name == "get_item_detail")
    result = await detail_tool.ainvoke({"good_id": 7310})
    mock_item_api.get_item_detail.assert_called_once_with(7310)
    assert "85.5" in result


@pytest.mark.asyncio
async def test_get_price_chart_tool(tools, mock_item_api):
    chart_tool = next(t for t in tools if t.name == "get_price_chart")
    result = await chart_tool.ainvoke({"good_id": 7310, "platform": "buff", "period": "30d"})
    mock_item_api.get_item_chart.assert_called_once()
    assert "83.0" in result or "price" in result.lower()


@pytest.mark.asyncio
async def test_get_technical_analysis_tool(tools, mock_item_api):
    ta_tool = next(t for t in tools if t.name == "get_technical_analysis")
    result = await ta_tool.ainvoke({"good_id": 7310, "platform": "buff", "period": "30d"})
    # Should contain indicator results
    assert "MA" in result or "moving_average" in result.lower() or "volatility" in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_components/test_item_tools.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement item_tools.py**

```python
# src/csqaq/components/tools/item_tools.py
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from csqaq.infrastructure.analysis.indicators import TechnicalIndicators

if TYPE_CHECKING:
    from csqaq.infrastructure.csqaq_client.item import ItemAPI


def create_item_tools(item_api: ItemAPI) -> list:
    """Create LangChain tools bound to a specific ItemAPI instance."""

    @tool
    async def search_item(query: str) -> str:
        """Search for CS2 items by name. Returns a list of matching items with IDs."""
        results = await item_api.search_suggest(query)
        if not results:
            return "No items found."
        lines = []
        for item in results[:5]:
            lines.append(f"- ID: {item.good_id} | {item.good_name} ({item.market_hash_name})")
        return "\n".join(lines)

    @tool
    async def get_item_detail(good_id: int) -> str:
        """Get detailed information about a CS2 item including multi-platform prices."""
        detail = await item_api.get_item_detail(good_id)
        return json.dumps(
            {
                "name": detail.good_name,
                "buff_sell": detail.buff_sell_price,
                "buff_buy": detail.buff_buy_price,
                "steam_sell": detail.steam_sell_price,
                "yyyp_sell": detail.yyyp_sell_price,
                "buff_sell_num": detail.buff_sell_num,
                "buff_buy_num": detail.buff_buy_num,
                "daily_change": f"{detail.daily_change_rate}%",
                "weekly_change": f"{detail.weekly_change_rate}%",
                "monthly_change": f"{detail.monthly_change_rate}%",
                "category": detail.category,
                "rarity": detail.rarity,
                "exterior": detail.exterior,
            },
            ensure_ascii=False,
            indent=2,
        )

    @tool
    async def get_price_chart(good_id: int, platform: str = "buff", period: str = "30d") -> str:
        """Get price history chart data for an item on a specific platform."""
        chart = await item_api.get_item_chart(good_id, platform=platform, period=period)
        if not chart.points:
            return "No chart data available."
        lines = [f"Price chart ({chart.platform}, {chart.period}): {len(chart.points)} data points"]
        # Show first, middle, last points for overview
        key_points = [chart.points[0], chart.points[len(chart.points) // 2], chart.points[-1]]
        for p in key_points:
            lines.append(f"  - Price: {p.price}, Volume: {p.volume}")
        return "\n".join(lines)

    @tool
    async def get_technical_analysis(good_id: int, platform: str = "buff", period: str = "30d") -> str:
        """Compute technical indicators (MA, volatility, momentum, spread) for an item."""
        chart = await item_api.get_item_chart(good_id, platform=platform, period=period)
        if not chart.points or len(chart.points) < 3:
            return "Insufficient data for technical analysis."

        prices = [p.price for p in chart.points]
        volumes = [p.volume for p in chart.points]

        ma_7 = TechnicalIndicators.moving_average(prices, window=7)
        ma_30 = TechnicalIndicators.moving_average(prices, window=30)
        vol = TechnicalIndicators.volatility(prices, window=min(len(prices), 30))
        momentum = TechnicalIndicators.price_momentum(prices, period=min(len(prices) - 1, 7))
        vol_trend = TechnicalIndicators.volume_trend(volumes, window=min(len(volumes) // 2, 7))

        # Get latest non-None MA values
        latest_ma7 = next((v for v in reversed(ma_7) if v is not None), None)
        latest_ma30 = next((v for v in reversed(ma_30) if v is not None), None)

        return json.dumps(
            {
                "current_price": prices[-1],
                "MA_7": round(latest_ma7, 2) if latest_ma7 else None,
                "MA_30": round(latest_ma30, 2) if latest_ma30 else None,
                "volatility": round(vol, 2),
                "momentum_7d": round(momentum, 2),
                "volume_trend": vol_trend,
                "price_range": f"{min(prices):.2f} - {max(prices):.2f}",
                "data_points": len(prices),
            },
            ensure_ascii=False,
            indent=2,
        )

    return [search_item, get_item_detail, get_price_chart, get_technical_analysis]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_components/test_item_tools.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/tools/item_tools.py tests/test_components/test_item_tools.py
git commit -m "feat: add LangChain item tools (search, detail, chart, indicators)"
```

---

## Task 11: Item Agent + Item Flow

**Files:**
- Create: `src/csqaq/components/agents/item.py`
- Create: `src/csqaq/flows/item_flow.py`
- Test: `tests/test_flows/test_item_flow.py`

The Item Agent is a ReAct agent (LLM + tools). The Item Flow is a LangGraph subgraph that: resolves item name → ID, fetches data via tools, runs LLM analysis, writes result to state.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flows/test_item_flow.py
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.flows.item_flow import build_item_flow, ItemFlowState
from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    SuggestItem,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_item_api():
    api = AsyncMock()
    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text())
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text())
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text())
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    api.get_item_kline.return_value = []
    return api


@pytest.mark.asyncio
async def test_item_flow_produces_analysis(mock_item_api):
    """Item flow should produce an analysis_result in the final state."""
    from langchain_core.messages import AIMessage

    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="AK-47红线近期表现稳定，价格在83-85元区间震荡。")
    mock_factory.create.return_value = mock_llm

    flow = build_item_flow(item_api=mock_item_api, model_factory=mock_factory)
    initial_state: ItemFlowState = {
        "messages": [],
        "good_id": None,
        "good_name": "AK红线",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is None
    assert result.get("analysis_result") is not None
    assert len(result["analysis_result"]) > 0


@pytest.mark.asyncio
async def test_item_flow_handles_search_failure(mock_item_api):
    """When search fails, error should be written to state."""
    mock_item_api.search_suggest.side_effect = Exception("API down")

    mock_factory = AsyncMock()
    mock_factory.create.return_value = AsyncMock()

    flow = build_item_flow(item_api=mock_item_api, model_factory=mock_factory)
    initial_state: ItemFlowState = {
        "messages": [],
        "good_id": None,
        "good_name": "不存在的饰品",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_flows/test_item_flow.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement Item Agent**

```python
# src/csqaq/components/agents/item.py
"""Item Agent — analyzes a single CS2 skin's price, trend, and technical indicators.

Node functions for the Item Flow LangGraph subgraph.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from csqaq.infrastructure.analysis.indicators import TechnicalIndicators

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.item import ItemAPI

logger = logging.getLogger(__name__)

ITEM_ANALYST_SYSTEM_PROMPT = """你是一个专业的 CS2 饰品市场分析师。你会收到一个饰品的详细数据（多平台价格、涨跌幅、技术指标等），你的任务是：

1. 总结当前价格状态（各平台价格、价差情况）
2. 分析近期趋势（日/周/月涨跌幅、均线位置、波动率）
3. 指出值得关注的信号（异常价差、放量/缩量、趋势转折等）
4. 给出简短的技术面总结

使用中文回答。基于数据说话，不要凭空猜测。"""


async def resolve_item_node(state: dict, *, item_api: ItemAPI) -> dict:
    """Node: resolve item name to good_id via search, then fetch detail."""
    try:
        good_id = state.get("good_id")
        good_name = state.get("good_name", "")

        # If no good_id, search by name
        if good_id is None and good_name:
            results = await item_api.search_suggest(good_name)
            if not results:
                return {"error": f"未找到饰品: {good_name}"}
            good_id = results[0].good_id

        if good_id is None:
            return {"error": "无法确定饰品 ID"}

        # Fetch detail
        detail = await item_api.get_item_detail(good_id)
        return {
            "good_id": good_id,
            "item_detail": detail.model_dump(),
        }
    except Exception as e:
        logger.error("resolve_item_node failed: %s", e)
        return {"error": f"获取饰品信息失败: {e}"}


async def fetch_chart_node(state: dict, *, item_api: ItemAPI) -> dict:
    """Node: fetch chart data and compute technical indicators."""
    if state.get("error"):
        return {}

    good_id = state.get("good_id")
    if good_id is None:
        return {}

    try:
        chart = await item_api.get_item_chart(good_id, platform="buff", period="30d")
        chart_dict = chart.model_dump()

        # Compute indicators if we have enough data
        indicators: dict[str, Any] = {}
        if chart.points and len(chart.points) >= 3:
            prices = [p.price for p in chart.points]
            volumes = [p.volume for p in chart.points]

            ma_7 = TechnicalIndicators.moving_average(prices, window=7)
            latest_ma7 = next((v for v in reversed(ma_7) if v is not None), None)

            indicators = {
                "current_price": prices[-1],
                "MA_7": round(latest_ma7, 2) if latest_ma7 else None,
                "volatility": round(TechnicalIndicators.volatility(prices, window=min(len(prices), 30)), 2),
                "momentum_7d": round(TechnicalIndicators.price_momentum(prices, period=min(len(prices) - 1, 7)), 2),
                "volume_trend": TechnicalIndicators.volume_trend(volumes, window=min(len(volumes) // 2, 7) or 1),
                "price_range": f"{min(prices):.2f} - {max(prices):.2f}",
            }

        return {"chart_data": chart_dict, "indicators": indicators}
    except Exception as e:
        logger.warning("fetch_chart_node failed: %s", e)
        return {"chart_data": None, "indicators": None}


async def analyze_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM analyzes collected data and produces analysis_result."""
    if state.get("error"):
        return {"analysis_result": f"分析失败: {state['error']}"}

    detail = state.get("item_detail")
    indicators = state.get("indicators")
    if detail is None:
        return {"analysis_result": "无数据可分析"}

    # Build context for LLM
    data_summary = json.dumps(
        {"item_detail": detail, "indicators": indicators},
        ensure_ascii=False,
        indent=2,
    )

    llm = model_factory.create("analyst")
    messages = [
        {"role": "system", "content": ITEM_ANALYST_SYSTEM_PROMPT},
        {"role": "user", "content": f"请分析以下饰品数据:\n\n{data_summary}"},
    ]
    response = await llm.ainvoke(messages)
    return {"analysis_result": response.content}
```

- [ ] **Step 4: Implement Item Flow**

```python
# src/csqaq/flows/item_flow.py
"""Item analysis LangGraph subgraph.

Graph: resolve_item → fetch_chart → analyze → END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.item import analyze_node, fetch_chart_node, resolve_item_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.item import ItemAPI


class ItemFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    good_id: int | None
    good_name: str | None
    item_detail: dict | None
    chart_data: dict | None
    kline_data: list | None
    indicators: dict | None
    analysis_result: str | None
    error: str | None


def _should_continue(state: ItemFlowState) -> str:
    """If error occurred in resolve step, skip to end."""
    if state.get("error"):
        return "analyze"
    return "fetch_chart"


def build_item_flow(item_api: ItemAPI, model_factory: ModelFactory):
    """Build and compile the item analysis subgraph. Returns a CompiledStateGraph."""
    graph = StateGraph(ItemFlowState)

    # Bind dependencies to node functions
    graph.add_node("resolve_item", partial(resolve_item_node, item_api=item_api))
    graph.add_node("fetch_chart", partial(fetch_chart_node, item_api=item_api))
    graph.add_node("analyze", partial(analyze_node, model_factory=model_factory))

    graph.set_entry_point("resolve_item")
    graph.add_conditional_edges(
        "resolve_item",
        _should_continue,
        {"analyze": "analyze", "fetch_chart": "fetch_chart"},
    )
    graph.add_edge("fetch_chart", "analyze")
    graph.add_edge("analyze", END)

    return graph.compile()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_flows/test_item_flow.py -v
```

Expected: 2 passed

> **Note:** Tests may need adjustment based on exact LangGraph behavior with mocks. The key is that `analysis_result` is populated on success and `error` is populated on failure.

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/components/agents/item.py src/csqaq/flows/item_flow.py tests/test_flows/test_item_flow.py
git commit -m "feat: add Item Agent and LangGraph item analysis flow"
```

---

## Task 12: Advisor Agent + Advisor Flow

**Files:**
- Create: `src/csqaq/components/agents/advisor.py`
- Create: `src/csqaq/flows/advisor_flow.py`
- Test: `tests/test_flows/test_advisor_flow.py`

Phase 1 Advisor: receives item analysis context, uses GPT-5 to produce investment recommendation with risk level. HITL interrupt for high-risk advice.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flows/test_advisor_flow.py
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.advisor_flow import AdvisorFlowState, build_advisor_flow


@pytest.mark.asyncio
async def test_advisor_produces_recommendation():
    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"recommendation": "建议持有观望，近期价格稳定", "risk_level": "low"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_advisor_flow(model_factory=mock_factory)
    initial_state: AdvisorFlowState = {
        "messages": [],
        "market_context": None,
        "item_context": {"analysis_result": "AK-47红线近期价格稳定在83-85元区间"},
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("recommendation") is not None
    assert result.get("risk_level") in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_advisor_sets_confirmation_for_high_risk():
    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"recommendation": "建议立即清仓AK红线", "risk_level": "high"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_advisor_flow(model_factory=mock_factory)
    initial_state: AdvisorFlowState = {
        "messages": [],
        "market_context": None,
        "item_context": {"analysis_result": "AK-47红线暴跌15%"},
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("risk_level") == "high"
    assert result.get("requires_confirmation") is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_flows/test_advisor_flow.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement Advisor Agent**

```python
# src/csqaq/components/agents/advisor.py
"""Advisor Agent — synthesizes analysis data into investment recommendations.

Uses GPT-5 for deep reasoning. Outputs structured JSON with recommendation + risk_level.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory

logger = logging.getLogger(__name__)

ADVISOR_SYSTEM_PROMPT = """你是一位经验丰富的 CS2 饰品投资顾问。你的任务是根据分析数据给出投资建议。

你会收到以下上下文（部分可能为空）：
- item_context: 单品分析结果
- market_context: 大盘分析结果
- scout_context: 机会发现结果
- historical_advice: 历史分析参考

请综合分析后，输出严格 JSON 格式：
{
  "recommendation": "详细的投资建议（中文，100-300字）",
  "risk_level": "low" | "medium" | "high"
}

风险等级标准：
- low: 观望、小额建仓、长期持有
- medium: 加仓、减仓、平台间套利
- high: 大额买入、清仓、追涨杀跌

基于数据说话，给出理由。如果数据不足，标注数据缺失并给出保守建议。"""


async def advise_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM produces investment recommendation."""
    context_parts = []

    if state.get("item_context"):
        context_parts.append(f"## 单品分析\n{json.dumps(state['item_context'], ensure_ascii=False, indent=2)}")
    if state.get("market_context"):
        context_parts.append(f"## 大盘分析\n{json.dumps(state['market_context'], ensure_ascii=False, indent=2)}")
    if state.get("scout_context"):
        context_parts.append(f"## 机会发现\n{json.dumps(state['scout_context'], ensure_ascii=False, indent=2)}")

    if not context_parts:
        return {
            "recommendation": "数据不足，无法给出建议。请先查询具体饰品或大盘数据。",
            "risk_level": "low",
            "requires_confirmation": False,
        }

    context = "\n\n".join(context_parts)

    try:
        llm = model_factory.create("advisor")
        messages = [
            {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"请基于以下数据给出投资建议:\n\n{context}"},
        ]
        response = await llm.ainvoke(messages)

        # Parse structured output
        try:
            parsed = json.loads(response.content)
            recommendation = parsed.get("recommendation", response.content)
            risk_level = parsed.get("risk_level", "low")
        except json.JSONDecodeError:
            recommendation = response.content
            risk_level = "low"

        if risk_level not in ("low", "medium", "high"):
            risk_level = "medium"

        return {
            "recommendation": recommendation,
            "risk_level": risk_level,
            "requires_confirmation": risk_level == "high",
        }
    except Exception as e:
        logger.error("advise_node failed: %s", e)
        return {
            "recommendation": f"分析出错: {e}",
            "risk_level": "low",
            "requires_confirmation": False,
            "error": str(e),
        }
```

- [ ] **Step 4: Implement Advisor Flow**

```python
# src/csqaq/flows/advisor_flow.py
"""Advisor LangGraph subgraph.

Phase 1: Simple single-node flow (advise → END).
Phase 2+ will add HITL interrupt for high-risk recommendations.
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.models.factory import ModelFactory


class AdvisorFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    market_context: dict | None
    item_context: dict | None
    scout_context: dict | None
    historical_advice: list | None
    recommendation: str | None
    risk_level: str | None  # "low" | "medium" | "high"
    requires_confirmation: bool
    error: str | None


def build_advisor_flow(model_factory: ModelFactory):
    """Build and compile the advisor subgraph. Returns a CompiledStateGraph."""
    graph = StateGraph(AdvisorFlowState)

    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("advise")
    graph.add_edge("advise", END)

    return graph.compile()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_flows/test_advisor_flow.py -v
```

Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/components/agents/advisor.py src/csqaq/flows/advisor_flow.py tests/test_flows/test_advisor_flow.py
git commit -m "feat: add Advisor Agent and LangGraph advisor flow"
```

---

## Task 13: CLI + Application Entry Point

**Files:**
- Create: `src/csqaq/main.py`
- Create: `src/csqaq/api/cli.py`

This task wires everything together. The CLI provides `csqaq chat "query"` command that runs the item + advisor pipeline.

- [ ] **Step 1: Implement main.py (application wiring)**

```python
# src/csqaq/main.py
"""Application entry point and dependency wiring."""
from __future__ import annotations

import asyncio
import logging
import sys

from rich.logging import RichHandler

from csqaq.config import Settings


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


class App:
    """Application container — holds all initialized services."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._csqaq_client = None
        self._item_api = None
        self._model_factory = None
        self._database = None

    async def init(self) -> None:
        from csqaq.components.models.factory import ModelFactory
        from csqaq.components.models.providers import create_openai_model
        from csqaq.infrastructure.csqaq_client.client import CSQAQClient
        from csqaq.infrastructure.csqaq_client.item import ItemAPI
        from csqaq.infrastructure.database.connection import Database

        # CSQAQ Client
        self._csqaq_client = CSQAQClient(
            base_url=self.settings.csqaq_base_url,
            api_token=self.settings.csqaq_api_token,
            rate_limit=self.settings.csqaq_rate_limit,
        )
        self._item_api = ItemAPI(self._csqaq_client)

        # LLM Factory
        self._model_factory = ModelFactory()
        self._model_factory.register("router", provider="openai", model=self.settings.router_model, temperature=0.0)
        self._model_factory.register("analyst", provider="openai", model=self.settings.analyst_model, temperature=0.3)
        self._model_factory.register("advisor", provider="openai", model=self.settings.advisor_model, temperature=0.5)

        # Database
        self._database = Database(self.settings.database_url)
        await self._database.init()

    @property
    def item_api(self):
        return self._item_api

    @property
    def model_factory(self):
        return self._model_factory

    @property
    def database(self):
        return self._database

    async def close(self) -> None:
        if self._csqaq_client:
            await self._csqaq_client.close()
        if self._database:
            await self._database.close()


async def run_item_query(app: App, query: str) -> str:
    """Run a single item analysis query end-to-end."""
    from csqaq.flows.advisor_flow import build_advisor_flow
    from csqaq.flows.item_flow import build_item_flow

    # Build flows
    item_flow = build_item_flow(item_api=app.item_api, model_factory=app.model_factory)
    advisor_flow = build_advisor_flow(model_factory=app.model_factory)

    # Run item analysis
    item_result = await item_flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": query,
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    })

    if item_result.get("error") and not item_result.get("analysis_result"):
        return f"查询失败: {item_result['error']}"

    # Run advisor
    advisor_result = await advisor_flow.ainvoke({
        "messages": [],
        "market_context": None,
        "item_context": {
            "analysis_result": item_result.get("analysis_result", ""),
            "item_detail": item_result.get("item_detail"),
            "indicators": item_result.get("indicators"),
        },
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    # Format output
    parts = []
    if item_result.get("analysis_result"):
        parts.append(f"📊 分析:\n{item_result['analysis_result']}")
    if advisor_result.get("recommendation"):
        risk = advisor_result.get("risk_level", "unknown")
        parts.append(f"\n💡 建议 (风险: {risk}):\n{advisor_result['recommendation']}")

    return "\n".join(parts) if parts else "未能生成分析结果"


def cli_entry() -> None:
    """Entry point for the `csqaq` CLI command."""
    from csqaq.api.cli import app as typer_app
    typer_app()
```

- [ ] **Step 2: Implement cli.py**

```python
# src/csqaq/api/cli.py
"""Typer CLI for CSQAQ. Local-mode entry point."""
from __future__ import annotations

import asyncio

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from csqaq.config import Settings
from csqaq.main import App, run_item_query, setup_logging

app = typer.Typer(name="csqaq", help="CS2 饰品投资分析系统")
console = Console()


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        console.print(f"[red]配置错误:[/red] {e}")
        console.print("请检查 .env 文件或环境变量，参考 .env.example")
        raise typer.Exit(1)


@app.command()
def chat(query: str = typer.Argument(None, help="查询内容，如 'AK红线能入吗'")):
    """查询饰品分析和投资建议。不带参数进入交互模式。"""
    setup_logging()
    settings = _load_settings()

    if query:
        # Single query mode
        result = asyncio.run(_single_query(settings, query))
        console.print(Panel(result, title="CSQAQ 分析结果", border_style="blue"))
    else:
        # Interactive mode
        asyncio.run(_interactive_mode(settings))


async def _single_query(settings: Settings, query: str) -> str:
    application = App(settings)
    await application.init()
    try:
        return await run_item_query(application, query)
    finally:
        await application.close()


async def _interactive_mode(settings: Settings) -> None:
    application = App(settings)
    await application.init()
    console.print("[bold blue]CSQAQ 饰品分析系统[/bold blue] — 输入问题，输入 quit 退出\n")
    try:
        while True:
            query = console.input("[bold green]> [/bold green]")
            if query.strip().lower() in ("quit", "exit", "q"):
                break
            if not query.strip():
                continue
            with console.status("分析中..."):
                result = await run_item_query(application, query.strip())
            console.print(Panel(result, title="分析结果", border_style="blue"))
            console.print()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await application.close()
        console.print("\n[dim]再见！[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """CSQAQ — CS2 饰品投资分析系统"""
    if ctx.invoked_subcommand is None:
        chat()
```

- [ ] **Step 3: Manually test CLI runs**

```bash
# Verify CLI starts without errors (will fail on missing .env, that's OK)
python -m csqaq.api.cli --help
```

Expected: Shows help text with `chat` command.

- [ ] **Step 4: Commit**

```bash
git add src/csqaq/main.py src/csqaq/api/cli.py
git commit -m "feat: add Typer CLI and application entry point"
```

---

## Task 14: End-to-End Integration Test

**Files:**
- Create: `tests/test_e2e.py`
- Modify: `tests/conftest.py`

Wire up the full pipeline with mocked external dependencies (CSQAQ API + LLM) and verify the complete flow from query to recommendation.

- [ ] **Step 1: Set up shared fixtures in conftest.py**

```python
# tests/conftest.py
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    KlineBar,
    SuggestItem,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_dir():
    return FIXTURES


@pytest.fixture
def mock_item_api():
    """Fully mocked ItemAPI with fixture data."""
    api = AsyncMock()

    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text())
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text())
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text())
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text())
    api.get_item_kline.return_value = [KlineBar.model_validate(k) for k in kline_data]

    return api
```

- [ ] **Step 2: Write the E2E test**

```python
# tests/test_e2e.py
"""End-to-end test: query → item flow → advisor flow → recommendation."""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.components.models.factory import ModelFactory
from csqaq.flows.advisor_flow import build_advisor_flow
from csqaq.flows.item_flow import build_item_flow


@pytest.mark.asyncio
async def test_full_item_to_advisor_pipeline(mock_item_api):
    """Complete pipeline: search item → analyze → advise."""
    # Set up model factory with mock LLMs
    factory = ModelFactory()

    # Mock analyst LLM
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(
        content="AK-47红线当前Buff售价85.5元，买价82元，价差4.3%。Steam售价12.35美元。"
        "日涨幅1.25%，周跌2.3%，月涨5.6%。近30日价格在83-85.5元区间震荡，波动较小。"
        "成交量稳定，流动性良好。技术面偏中性。"
    )

    # Mock advisor LLM
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"recommendation": "AK-47红线近期价格稳定，月度仍有5.6%涨幅。'
        '建议持有观望，不建议追高。如回调至82元以下可小额加仓。", "risk_level": "low"}'
    )

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    # Override create to return our mocks
    _call_count = {"analyst": 0, "advisor": 0}

    original_create = factory.create

    def mock_create(role):
        if role == "analyst":
            return mock_analyst
        elif role == "advisor":
            return mock_advisor
        return original_create(role)

    factory.create = mock_create

    # Build flows
    item_flow = build_item_flow(item_api=mock_item_api, model_factory=factory)
    advisor_flow = build_advisor_flow(model_factory=factory)

    # Run item flow
    item_result = await item_flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": "AK红线",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    })

    assert item_result.get("error") is None
    assert item_result["good_id"] == 7310
    assert item_result["analysis_result"] is not None
    assert "AK-47" in item_result["analysis_result"]

    # Run advisor flow with item context
    advisor_result = await advisor_flow.ainvoke({
        "messages": [],
        "market_context": None,
        "item_context": {
            "analysis_result": item_result["analysis_result"],
            "item_detail": item_result.get("item_detail"),
            "indicators": item_result.get("indicators"),
        },
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    assert advisor_result["recommendation"] is not None
    assert advisor_result["risk_level"] == "low"
    assert advisor_result["requires_confirmation"] is False
    assert "AK-47" in advisor_result["recommendation"]
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass (approximately 25+ tests total).

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_e2e.py
git commit -m "test: add E2E integration test for item analysis pipeline"
```

---

## Task 15: Final Verification + Data Directory

**Files:**
- Create: `data/.gitkeep`

- [ ] **Step 1: Create data directory placeholder**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 2: Run full test suite one final time**

```bash
pytest tests/ -v --tb=long
```

Expected: All tests pass.

- [ ] **Step 3: Verify CLI help works**

```bash
python -m csqaq.api.cli --help
```

Expected: Shows CSQAQ help text.

- [ ] **Step 4: Commit**

```bash
git add data/.gitkeep
git commit -m "chore: add data directory placeholder"
```

---

## Summary

Phase 1 delivers:
- **CSQAQ API Client** with rate limiting, retry, error handling
- **Pydantic schemas** for typed API responses
- **Item endpoints** (search, detail, chart, kline)
- **Database layer** (SQLAlchemy async ORM with all tables)
- **Memory cache** (in-memory TTL)
- **Technical indicators engine** (MA, volatility, momentum, spread, volume trend)
- **LLM model factory** (registry + factory pattern)
- **Item tools** (LangChain tool wrappers)
- **Item Agent** + **Item Flow** (LangGraph subgraph)
- **Advisor Agent** + **Advisor Flow** (LangGraph subgraph)
- **Typer CLI** with `csqaq chat` command
- **27+ tests** covering all layers

**Next:** Phase 2 plan — Market Agent, Scout Agent, Router Agent, full main graph orchestration.
