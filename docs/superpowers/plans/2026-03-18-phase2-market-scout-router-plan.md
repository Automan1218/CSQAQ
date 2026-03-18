# Phase 2: Market Agent + Scout Agent + Router Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Market Agent, Scout Agent, Router, and Main Graph so users can query market index, discover investment opportunities, and have queries auto-routed.

**Architecture:** Extends Phase 1's 4-layer architecture (API → Flows → Components → Infrastructure). Router Flow becomes the new main entry point, dispatching to Item/Market/Scout sub-flows. Each sub-flow embeds its own Advisor node for self-contained output.

**Tech Stack:** Python 3.13, LangGraph (StateGraph), LangChain, httpx, Pydantic v2, pytest + respx + pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-18-phase2-market-scout-router-design.md`

**Run tests:** `conda run -n CSQAQ pytest tests/ -v`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/csqaq/infrastructure/csqaq_client/market.py` | MarketAPI — wraps market index endpoints |
| `src/csqaq/infrastructure/csqaq_client/rank.py` | RankAPI — wraps rank/page-list endpoints |
| `src/csqaq/infrastructure/csqaq_client/market_schemas.py` | Pydantic models for market API responses |
| `src/csqaq/infrastructure/csqaq_client/rank_schemas.py` | Pydantic models for rank API responses |
| `src/csqaq/components/router.py` | Router — keyword + LLM intent classification |
| `src/csqaq/components/agents/market.py` | Market Agent — node functions for market analysis |
| `src/csqaq/components/agents/scout.py` | Scout Agent — node functions for opportunity discovery |
| `src/csqaq/flows/market_flow.py` | Market Flow — LangGraph subgraph |
| `src/csqaq/flows/scout_flow.py` | Scout Flow — LangGraph subgraph |
| `src/csqaq/flows/router_flow.py` | Router Flow — main entry graph |
| `tests/fixtures/home_data_response.json` | Fixture for MarketAPI.get_home_data |
| `tests/fixtures/sub_data_response.json` | Fixture for MarketAPI.get_sub_data |
| `tests/fixtures/rank_list_response.json` | Fixture for RankAPI.get_rank_list |
| `tests/fixtures/page_list_response.json` | Fixture for RankAPI.get_page_list |
| `tests/test_infrastructure/test_market_endpoints.py` | MarketAPI unit tests |
| `tests/test_infrastructure/test_rank_endpoints.py` | RankAPI unit tests |
| `tests/test_components/test_router.py` | Router unit tests |
| `tests/test_flows/test_market_flow.py` | Market Flow tests |
| `tests/test_flows/test_scout_flow.py` | Scout Flow tests |
| `tests/test_flows/test_router_flow.py` | Router Flow tests |

### Modified Files
| File | Change |
|------|--------|
| `src/csqaq/infrastructure/csqaq_client/client.py` | Add `get()` method |
| `src/csqaq/infrastructure/csqaq_client/__init__.py` | Export new APIs |
| `src/csqaq/flows/item_flow.py` | Embed Advisor node, add `result` to state |
| `src/csqaq/main.py` | Add MarketAPI/RankAPI init, `run_query` replaces `run_item_query` |
| `src/csqaq/api/cli.py` | Call `run_query` instead of `run_item_query` |
| `tests/conftest.py` | Add mock_market_api, mock_rank_api fixtures |
| `tests/test_e2e.py` | Add market/scout E2E tests |
| `tests/test_flows/test_item_flow.py` | Update for embedded Advisor |

---

## Task 1: CSQAQClient — add `get()` method

**Files:**
- Modify: `src/csqaq/infrastructure/csqaq_client/client.py`
- Test: `tests/test_infrastructure/test_csqaq_client.py`

- [ ] **Step 1: Write failing test for GET method**

```python
# Append to tests/test_infrastructure/test_csqaq_client.py

@respx.mock
@pytest.mark.asyncio
async def test_get_request():
    client = CSQAQClient(base_url="https://api.csqaq.com/api/v1", api_token="test", rate_limit=100.0)
    respx.get("https://api.csqaq.com/api/v1/current_data").mock(
        return_value=httpx.Response(200, json={"code": 200, "data": {"index": 1000}})
    )
    result = await client.get("/current_data", params={"type": "init"})
    assert result == {"index": 1000}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_csqaq_client.py::test_get_request -v`
Expected: FAIL — `AttributeError: 'CSQAQClient' object has no attribute 'get'`

- [ ] **Step 3: Implement `get()` method**

Add to `src/csqaq/infrastructure/csqaq_client/client.py`, after the `post()` method:

```python
async def get(self, path: str, params: dict | None = None, priority: int = 0) -> dict:
    """Send GET request with rate limiting and retry.

    Args:
        path: API endpoint path (e.g. "/current_data")
        params: Query parameters
        priority: Request priority (0=interactive, 1=alert, 2=background)

    Returns:
        The 'data' field from the API response.
    """
    url = f"{self._base_url}{path}"
    last_error: Exception | None = None

    for attempt in range(self._max_retries + 1):
        await self._wait_for_rate_limit()
        try:
            response = await self._http.get(url, params=params)
        except httpx.TransportError as e:
            last_error = CSQAQClientError(f"Network error: {e}")
            if attempt < self._max_retries:
                await self._backoff(attempt)
                continue
            raise last_error from e

        if response.status_code == 200:
            body = response.json()
            return body.get("data", body)

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

        if last_error is None:
            last_error = CSQAQClientError(
                f"Unexpected status {response.status_code}: {response.text}",
                status_code=response.status_code,
            )
        break

    raise last_error  # type: ignore[misc]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_csqaq_client.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/client.py tests/test_infrastructure/test_csqaq_client.py
git commit -m "feat: add GET method to CSQAQClient for market endpoints"
```

---

## Task 2: Market Schemas

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/market_schemas.py`
- Test: `tests/test_infrastructure/test_market_schemas.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_infrastructure/test_market_schemas.py`:

```python
from csqaq.infrastructure.csqaq_client.market_schemas import (
    GreedyStatus,
    HomeData,
    OnlineNumber,
    RateData,
    SubData,
    SubIndexCount,
    SubIndexItem,
)


class TestSubIndexItem:
    def test_parse(self):
        data = {
            "id": 1, "name": "BUFF饰品指数", "name_key": "buff",
            "img": "https://example.com/img.png", "market_index": 1052.3,
            "chg_num": 2.5, "chg_rate": 0.24, "open": 1050.0,
            "close": 1052.3, "high": 1055.0, "low": 1048.0,
            "updated_at": "2026-03-18 12:00:00",
        }
        item = SubIndexItem.model_validate(data)
        assert item.market_index == 1052.3
        assert item.chg_rate == 0.24


class TestRateData:
    def test_parse(self):
        data = {
            "count_positive_1": 500, "count_negative_1": 300, "count_zero_1": 200,
            "count_positive_7": 450, "count_negative_7": 350, "count_zero_7": 200,
            "count_positive_15": 400, "count_negative_15": 400, "count_zero_15": 200,
            "count_positive_30": 420, "count_negative_30": 380, "count_zero_30": 200,
            "count_positive_90": 500, "count_negative_90": 300, "count_zero_90": 200,
            "count_positive_180": 480, "count_negative_180": 320, "count_zero_180": 200,
        }
        rate = RateData.model_validate(data)
        assert rate.count_positive_1 == 500
        assert rate.count_negative_30 == 380


class TestSubData:
    def test_parse(self):
        data = {
            "timestamp": [1710720000, 1710806400],
            "count": {
                "name": "BUFF饰品指数", "img": "", "now": 1052.3,
                "amplitude": 2.5, "rate": 0.24, "max_value": 1055,
                "min_value": 1048.0, "consecutive_days": 3,
            },
            "main_data": [[1052.3, 2.5, 0.24], [1050.0, -2.3, -0.22]],
            "hourly_list": [1050.0, 1051.0, 1052.3],
        }
        sub = SubData.model_validate(data)
        assert sub.count.now == 1052.3
        assert sub.count.consecutive_days == 3
        assert len(sub.main_data) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_market_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement market schemas**

Create `src/csqaq/infrastructure/csqaq_client/market_schemas.py`:

```python
from pydantic import BaseModel


class SubIndexItem(BaseModel):
    """饰品指数条目 — from GET /api/v1/current_data"""
    id: int
    name: str
    name_key: str
    img: str
    market_index: float
    chg_num: float
    chg_rate: float
    open: float
    close: float
    high: float
    low: float
    updated_at: str


class RateData(BaseModel):
    """涨跌分布数量 — 各时间段上涨/下跌/持平的饰品数量"""
    count_positive_1: int
    count_negative_1: int
    count_zero_1: int
    count_positive_7: int
    count_negative_7: int
    count_zero_7: int
    count_positive_15: int
    count_negative_15: int
    count_zero_15: int
    count_positive_30: int
    count_negative_30: int
    count_zero_30: int
    count_positive_90: int
    count_negative_90: int
    count_zero_90: int
    count_positive_180: int
    count_negative_180: int
    count_zero_180: int


class OnlineNumber(BaseModel):
    """在线人数数据"""
    current_number: int
    today_peak: int
    month_peak: int
    month_player: int
    same_month_player: int
    same_time_number: int
    rate: float
    same_time_number_week: int
    rate_week: float
    created_at: str


class GreedyStatus(BaseModel):
    """市场情绪"""
    level: str   # "low" | "medium" | "high"
    label: str   # 低迷 / 中等 / 活跃


class HomeData(BaseModel):
    """首页完整数据 — GET /api/v1/current_data?type=init 的 data 字段"""
    sub_index_data: list[SubIndexItem]
    chg_type_data: list[dict]
    chg_price_data: list[dict]
    rate_data: RateData
    online_number: OnlineNumber
    greedy_status: GreedyStatus
    # 以下字段直接用 dict/list 接收，不做强类型（Phase 2 不用）
    online_chart: list[dict] = []
    greedy: list = []
    alteration: list[dict] = []
    view_count: list[dict] = []
    card_price: list[dict] = []


class SubIndexCount(BaseModel):
    """指数概要"""
    name: str
    img: str = ""
    now: float
    amplitude: float
    rate: float
    max_value: float
    min_value: float
    consecutive_days: int


class SubData(BaseModel):
    """指数详情 — GET /api/v1/sub_data 的 data 字段"""
    timestamp: list[int]
    count: SubIndexCount
    main_data: list[list[float]]
    hourly_list: list[float]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_market_schemas.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/market_schemas.py tests/test_infrastructure/test_market_schemas.py
git commit -m "feat: add Pydantic schemas for market API responses"
```

---

## Task 3: MarketAPI + Fixtures

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/market.py`
- Create: `tests/fixtures/home_data_response.json`
- Create: `tests/fixtures/sub_data_response.json`
- Test: `tests/test_infrastructure/test_market_endpoints.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/home_data_response.json`:
```json
{
  "sub_index_data": [
    {
      "id": 1, "name": "BUFF饰品指数", "name_key": "buff",
      "img": "https://example.com/buff.png", "market_index": 1052.3,
      "chg_num": 2.5, "chg_rate": 0.24, "open": 1050.0,
      "close": 1052.3, "high": 1055.0, "low": 1048.0,
      "updated_at": "2026-03-18 12:00:00"
    }
  ],
  "chg_type_data": [{"name": "步枪", "price_diff_1": 0.5, "type": "步枪"}],
  "chg_price_data": [{"xKey": "中件", "price_diff_1": 0.3}],
  "rate_data": {
    "count_positive_1": 500, "count_negative_1": 300, "count_zero_1": 200,
    "count_positive_7": 450, "count_negative_7": 350, "count_zero_7": 200,
    "count_positive_15": 400, "count_negative_15": 400, "count_zero_15": 200,
    "count_positive_30": 420, "count_negative_30": 380, "count_zero_30": 200,
    "count_positive_90": 500, "count_negative_90": 300, "count_zero_90": 200,
    "count_positive_180": 480, "count_negative_180": 320, "count_zero_180": 200
  },
  "online_number": {
    "current_number": 850000, "today_peak": 1200000, "month_peak": 1500000,
    "month_player": 30000000, "same_month_player": 29000000,
    "same_time_number": 800000, "rate": 6.25, "same_time_number_week": 780000,
    "rate_week": 8.97, "created_at": "2026-03-18 12:00:00"
  },
  "greedy_status": {"level": "medium", "label": "中等"},
  "online_chart": [], "greedy": [], "alteration": [], "view_count": [], "card_price": []
}
```

Create `tests/fixtures/sub_data_response.json`:
```json
{
  "timestamp": [1710720000, 1710806400, 1710892800],
  "count": {
    "name": "BUFF饰品指数", "img": "", "now": 1052.3,
    "amplitude": 2.5, "rate": 0.24, "max_value": 1055,
    "min_value": 1048.0, "consecutive_days": 3
  },
  "main_data": [[1050.0, -2.3, -0.22], [1048.0, -2.0, -0.19], [1052.3, 2.5, 0.24]],
  "hourly_list": [1050.0, 1050.5, 1051.0, 1052.3]
}
```

- [ ] **Step 2: Write failing test**

Create `tests/test_infrastructure/test_market_endpoints.py`:

```python
import json
from pathlib import Path

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.market import MarketAPI
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, SubData

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASE = "https://api.csqaq.com/api/v1"


@pytest.fixture
def client():
    return CSQAQClient(base_url=BASE, api_token="test", rate_limit=100.0)


@pytest.fixture
def market_api(client):
    return MarketAPI(client)


@respx.mock
@pytest.mark.asyncio
async def test_get_home_data(market_api):
    data = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    respx.get(f"{BASE}/current_data").mock(
        return_value=httpx.Response(200, json={"code": 200, "data": data})
    )
    result = await market_api.get_home_data()
    assert isinstance(result, HomeData)
    assert len(result.sub_index_data) == 1
    assert result.sub_index_data[0].market_index == 1052.3
    assert result.rate_data.count_positive_1 == 500
    assert result.greedy_status.level == "medium"


@respx.mock
@pytest.mark.asyncio
async def test_get_sub_data(market_api):
    data = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    respx.get(f"{BASE}/sub_data").mock(
        return_value=httpx.Response(200, json={"code": 200, "data": data})
    )
    result = await market_api.get_sub_data(sub_id=1, type="daily")
    assert isinstance(result, SubData)
    assert result.count.now == 1052.3
    assert result.count.consecutive_days == 3
    assert len(result.main_data) == 3
```

- [ ] **Step 3: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_market_endpoints.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'csqaq.infrastructure.csqaq_client.market'`

- [ ] **Step 4: Implement MarketAPI**

Create `src/csqaq/infrastructure/csqaq_client/market.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from .market_schemas import HomeData, SubData

if TYPE_CHECKING:
    from .client import CSQAQClient


class MarketAPI:
    """CSQAQ market index API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def get_home_data(self, type: str = "init") -> HomeData:
        """Get home page index data. GET /api/v1/current_data"""
        data = await self._client.get("/current_data", params={"type": type})
        return HomeData.model_validate(data)

    async def get_sub_data(self, sub_id: int = 1, type: str = "daily") -> SubData:
        """Get sub-index detail. GET /api/v1/sub_data"""
        data = await self._client.get("/sub_data", params={"id": str(sub_id), "type": type})
        return SubData.model_validate(data)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_market_endpoints.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/market.py tests/test_infrastructure/test_market_endpoints.py tests/fixtures/home_data_response.json tests/fixtures/sub_data_response.json
git commit -m "feat: add MarketAPI with home data and sub-index endpoints"
```

---

## Task 4: Rank Schemas

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/rank_schemas.py`
- Test: `tests/test_infrastructure/test_rank_schemas.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_infrastructure/test_rank_schemas.py`:

```python
from csqaq.infrastructure.csqaq_client.rank_schemas import PageListItem, RankItem


class TestRankItem:
    def test_parse(self):
        data = {
            "id": 7310, "name": "AK-47 | 红线 (久经沙场)",
            "img": "https://example.com/ak.png",
            "exterior_localized_name": "久经沙场",
            "rarity_localized_name": "保密",
            "buff_sell_price": 85.5, "buff_sell_num": 1200,
            "buff_buy_price": 82.0, "buff_buy_num": 500,
            "steam_sell_price": 12.35, "steam_sell_num": 3000,
            "steam_buy_price": 11.0, "steam_buy_num": 800,
            "yyyp_sell_price": 83.0, "yyyp_sell_num": 600,
            "yyyp_buy_price": 80.0, "yyyp_buy_num": 200,
            "yyyp_lease_price": 0.5, "yyyp_long_lease_price": 0.3,
            "buff_price_chg": 1.25,
            "sell_price_1": 1.0, "sell_price_7": -2.0,
            "sell_price_15": 0, "sell_price_30": 3.0,
            "sell_price_90": 5.0, "sell_price_180": -1.0, "sell_price_365": 10.0,
            "sell_price_rate_1": 1.18, "sell_price_rate_7": -2.29,
            "sell_price_rate_15": 0, "sell_price_rate_30": 3.64,
            "sell_price_rate_90": 6.21, "sell_price_rate_180": -1.16,
            "sell_price_rate_365": 13.3,
            "created_at": "2026-03-18T14:20:19", "rank_num": 42,
        }
        item = RankItem.model_validate(data)
        assert item.id == 7310
        assert item.buff_sell_price == 85.5
        assert item.sell_price_rate_1 == 1.18

    def test_nullable_exterior(self):
        data = {
            "id": 100, "name": "印花 | test",
            "img": "", "exterior_localized_name": None,
            "rarity_localized_name": "高级",
            "buff_sell_price": 0.02, "buff_sell_num": 300,
            "buff_buy_price": 0.06, "buff_buy_num": 11,
            "steam_sell_price": 0.04, "steam_sell_num": 4000,
            "steam_buy_price": 0.03, "steam_buy_num": 400,
            "yyyp_sell_price": 0.02, "yyyp_sell_num": 500,
            "yyyp_buy_price": 0, "yyyp_buy_num": 0,
            "yyyp_lease_price": 0, "yyyp_long_lease_price": 0,
            "buff_price_chg": 0,
            "sell_price_1": 0, "sell_price_7": 0,
            "sell_price_15": 0, "sell_price_30": 0,
            "sell_price_90": 0, "sell_price_180": -0.01, "sell_price_365": -0.02,
            "sell_price_rate_1": 0, "sell_price_rate_7": 0,
            "sell_price_rate_15": 0, "sell_price_rate_30": 0,
            "sell_price_rate_90": 0, "sell_price_rate_180": -33.33,
            "sell_price_rate_365": -50,
            "created_at": "2026-03-18T14:20:19", "rank_num": 0,
        }
        item = RankItem.model_validate(data)
        assert item.exterior_localized_name is None


class TestPageListItem:
    def test_parse(self):
        data = {
            "id": 6798, "name": "蝴蝶刀（★） | 蓝钢 (崭新出厂)",
            "exterior_localized_name": "崭新出厂",
            "rarity_localized_name": "隐秘",
            "img": "https://example.com/knife.png",
            "yyyp_sell_price": 14300, "yyyp_sell_num": 16,
        }
        item = PageListItem.model_validate(data)
        assert item.id == 6798
        assert item.yyyp_sell_price == 14300
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_rank_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement rank schemas**

Create `src/csqaq/infrastructure/csqaq_client/rank_schemas.py`:

```python
from pydantic import BaseModel


class RankItem(BaseModel):
    """排行榜饰品条目 — from POST /api/v1/info/get_rank_list"""
    id: int
    name: str
    img: str
    exterior_localized_name: str | None
    rarity_localized_name: str
    # Multi-platform prices
    buff_sell_price: float
    buff_sell_num: int
    buff_buy_price: float
    buff_buy_num: int
    steam_sell_price: float
    steam_sell_num: int
    steam_buy_price: float = 0
    steam_buy_num: int = 0
    yyyp_sell_price: float
    yyyp_sell_num: int
    yyyp_buy_price: float = 0
    yyyp_buy_num: int = 0
    yyyp_lease_price: float = 0
    yyyp_long_lease_price: float = 0
    # Price changes (absolute)
    sell_price_1: float = 0
    sell_price_7: float = 0
    sell_price_15: float = 0
    sell_price_30: float = 0
    sell_price_90: float = 0
    sell_price_180: float = 0
    sell_price_365: float = 0
    # Price change rates (%)
    buff_price_chg: float = 0
    sell_price_rate_1: float = 0
    sell_price_rate_7: float = 0
    sell_price_rate_15: float = 0
    sell_price_rate_30: float = 0
    sell_price_rate_90: float = 0
    sell_price_rate_180: float = 0
    sell_price_rate_365: float = 0
    created_at: str = ""
    rank_num: int = 0


class PageListItem(BaseModel):
    """饰品列表条目 — from POST /api/v1/info/get_page_list"""
    id: int
    name: str
    exterior_localized_name: str | None
    rarity_localized_name: str
    img: str
    yyyp_sell_price: float
    yyyp_sell_num: float
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_rank_schemas.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/rank_schemas.py tests/test_infrastructure/test_rank_schemas.py
git commit -m "feat: add Pydantic schemas for rank API responses"
```

---

## Task 5: RankAPI + Fixtures

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/rank.py`
- Create: `tests/fixtures/rank_list_response.json`
- Create: `tests/fixtures/page_list_response.json`
- Test: `tests/test_infrastructure/test_rank_endpoints.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/rank_list_response.json`:
```json
{
  "current_page": 1,
  "data": [
    {
      "id": 7310, "name": "AK-47 | 红线 (久经沙场)",
      "img": "https://example.com/ak.png",
      "exterior_localized_name": "久经沙场", "rarity_localized_name": "保密",
      "buff_sell_price": 85.5, "buff_sell_num": 1200,
      "buff_buy_price": 82.0, "buff_buy_num": 500,
      "steam_sell_price": 12.35, "steam_sell_num": 3000,
      "steam_buy_price": 11.0, "steam_buy_num": 800,
      "yyyp_sell_price": 83.0, "yyyp_sell_num": 600,
      "yyyp_buy_price": 80.0, "yyyp_buy_num": 200,
      "yyyp_lease_price": 0.5, "yyyp_long_lease_price": 0.3,
      "buff_price_chg": 1.25,
      "sell_price_1": 1.0, "sell_price_7": -2.0,
      "sell_price_15": 0, "sell_price_30": 3.0,
      "sell_price_90": 5.0, "sell_price_180": -1.0, "sell_price_365": 10.0,
      "sell_price_rate_1": 1.18, "sell_price_rate_7": -2.29,
      "sell_price_rate_15": 0, "sell_price_rate_30": 3.64,
      "sell_price_rate_90": 6.21, "sell_price_rate_180": -1.16,
      "sell_price_rate_365": 13.3,
      "created_at": "2026-03-18T14:20:19", "rank_num": 42
    }
  ],
  "recently_data": {}
}
```

Create `tests/fixtures/page_list_response.json`:
```json
{
  "current_page": 1,
  "data": [
    {
      "id": 6798, "name": "蝴蝶刀（★） | 蓝钢 (崭新出厂)",
      "exterior_localized_name": "崭新出厂", "rarity_localized_name": "隐秘",
      "img": "https://example.com/knife.png",
      "yyyp_sell_price": 14300, "yyyp_sell_num": 16
    }
  ]
}
```

- [ ] **Step 2: Write failing test**

Create `tests/test_infrastructure/test_rank_endpoints.py`:

```python
import json
from pathlib import Path

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.rank import RankAPI
from csqaq.infrastructure.csqaq_client.rank_schemas import PageListItem, RankItem

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASE = "https://api.csqaq.com/api/v1"


@pytest.fixture
def client():
    return CSQAQClient(base_url=BASE, api_token="test", rate_limit=100.0)


@pytest.fixture
def rank_api(client):
    return RankAPI(client)


@respx.mock
@pytest.mark.asyncio
async def test_get_rank_list(rank_api):
    data = json.loads((FIXTURES / "rank_list_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/get_rank_list").mock(
        return_value=httpx.Response(200, json={"code": 200, "msg": "sell_price_rate_1", "data": data})
    )
    items = await rank_api.get_rank_list(
        filter={"排序": ["价格_近1天价格变动率_降序(BUFF)"]},
        page=1, size=20,
    )
    assert len(items) == 1
    assert isinstance(items[0], RankItem)
    assert items[0].id == 7310


@respx.mock
@pytest.mark.asyncio
async def test_get_page_list(rank_api):
    data = json.loads((FIXTURES / "page_list_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/get_page_list").mock(
        return_value=httpx.Response(200, json={"code": 200, "msg": "Success", "data": data})
    )
    items = await rank_api.get_page_list(page=1, size=18, search="蝴蝶")
    assert len(items) == 1
    assert isinstance(items[0], PageListItem)
    assert items[0].name == "蝴蝶刀（★） | 蓝钢 (崭新出厂)"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_rank_endpoints.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement RankAPI**

Create `src/csqaq/infrastructure/csqaq_client/rank.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from .rank_schemas import PageListItem, RankItem

if TYPE_CHECKING:
    from .client import CSQAQClient


class RankAPI:
    """CSQAQ ranking and page-list API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def get_rank_list(
        self,
        filter: dict,
        page: int = 1,
        size: int = 20,
        search: str = "",
        show_recently_price: bool = False,
    ) -> list[RankItem]:
        """Get ranking list. POST /api/v1/info/get_rank_list"""
        body: dict = {
            "page_index": page,
            "page_size": size,
            "filter": filter,
            "show_recently_price": show_recently_price,
        }
        if search:
            body["search"] = search
        data = await self._client.post("/info/get_rank_list", json=body)
        items = data.get("data", []) if isinstance(data, dict) else []
        return [RankItem.model_validate(item) for item in items]

    async def get_page_list(
        self,
        page: int = 1,
        size: int = 20,
        search: str = "",
        filter: dict | None = None,
    ) -> list[PageListItem]:
        """Get item page list. POST /api/v1/info/get_page_list"""
        body: dict = {
            "page_index": page,
            "page_size": size,
        }
        if search:
            body["search"] = search
        if filter:
            body["filter"] = filter
        data = await self._client.post("/info/get_page_list", json=body)
        items = data.get("data", []) if isinstance(data, dict) else []
        return [PageListItem.model_validate(item) for item in items]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_infrastructure/test_rank_endpoints.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/rank.py tests/test_infrastructure/test_rank_endpoints.py tests/fixtures/rank_list_response.json tests/fixtures/page_list_response.json
git commit -m "feat: add RankAPI with rank list and page list endpoints"
```

---

## Task 6: Router Component

**Files:**
- Create: `src/csqaq/components/router.py`
- Test: `tests/test_components/test_router.py`

- [ ] **Step 1: Write failing test for keyword matching**

Create `tests/test_components/test_router.py`:

```python
import pytest

from csqaq.components.router import IntentResult, classify_intent_by_keywords


class TestKeywordRouter:
    def test_market_keywords(self):
        result = classify_intent_by_keywords("今天大盘怎么样")
        assert result is not None
        assert result.intent == "market_query"
        assert result.confidence == 1.0

    def test_market_keyword_指数(self):
        result = classify_intent_by_keywords("饰品指数走势如何")
        assert result is not None
        assert result.intent == "market_query"

    def test_scout_keywords(self):
        result = classify_intent_by_keywords("有什么值得买的")
        assert result is not None
        assert result.intent == "scout_query"

    def test_scout_keyword_排行(self):
        result = classify_intent_by_keywords("涨幅排行前十")
        assert result is not None
        assert result.intent == "scout_query"

    def test_item_fallback(self):
        result = classify_intent_by_keywords("AK红线能入吗")
        assert result is None  # No keyword match -> None -> fallback to LLM or item

    def test_market_priority_over_scout(self):
        """When both market and scout keywords present, market wins."""
        result = classify_intent_by_keywords("大盘行情中有什么值得买的")
        assert result is not None
        assert result.intent == "market_query"

    def test_item_name_extraction(self):
        result = classify_intent_by_keywords("AK红线能入吗")
        # No keyword match, returns None
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_components/test_router.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement keyword router**

Create `src/csqaq/components/router.py`:

```python
"""Router — keyword + LLM intent classification."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    intent: str          # "item_query" | "market_query" | "scout_query"
    confidence: float    # 1.0 for keyword, 0.8 for LLM
    item_name: str | None


# Priority order: market > scout > item
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("market_query", ["大盘", "指数", "行情", "市场", "涨跌分布"]),
    ("scout_query", ["排行", "推荐", "值得买", "值得入", "机会", "捡漏", "热门"]),
]


def classify_intent_by_keywords(query: str) -> IntentResult | None:
    """Try to classify intent by keyword matching. Returns None if no match."""
    for intent, keywords in _KEYWORD_RULES:
        for kw in keywords:
            if kw in query:
                return IntentResult(intent=intent, confidence=1.0, item_name=None)
    return None


ROUTER_SYSTEM_PROMPT = """你是一个查询意图分类器。将用户查询分为三类:
- item_query: 询问某个具体饰品的价格、走势、是否值得入手
- market_query: 询问大盘、市场整体行情、指数
- scout_query: 询问推荐、排行、值得关注的饰品

输出严格 JSON: {"intent": "...", "item_name": "饰品名或null"}"""


async def classify_intent_by_llm(query: str, model_factory: ModelFactory) -> IntentResult:
    """Classify intent using LLM as fallback."""
    try:
        llm = model_factory.create("router")
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        response = await llm.ainvoke(messages)
        parsed = json.loads(response.content)
        intent = parsed.get("intent", "item_query")
        if intent not in ("item_query", "market_query", "scout_query"):
            intent = "item_query"
        return IntentResult(
            intent=intent,
            confidence=0.8,
            item_name=parsed.get("item_name"),
        )
    except Exception as e:
        logger.warning("LLM router failed: %s, defaulting to item_query", e)
        return IntentResult(intent="item_query", confidence=0.5, item_name=query)


async def route_query(query: str, model_factory: ModelFactory) -> IntentResult:
    """Route a query: keyword match first, LLM fallback."""
    result = classify_intent_by_keywords(query)
    if result is not None:
        return result
    return await classify_intent_by_llm(query, model_factory)
```

- [ ] **Step 4: Run keyword tests to verify they pass**

Run: `conda run -n CSQAQ pytest tests/test_components/test_router.py -v`
Expected: ALL PASS

- [ ] **Step 5: Add LLM fallback test**

Append to `tests/test_components/test_router.py`:

```python
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage
from csqaq.components.router import route_query


@pytest.mark.asyncio
async def test_llm_fallback_item_query():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"intent": "item_query", "item_name": "AK红线"}'
    )
    mock_factory.create.return_value = mock_llm

    result = await route_query("AK红线能入吗", mock_factory)
    assert result.intent == "item_query"
    assert result.item_name == "AK红线"
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_llm_failure_defaults_to_item():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("LLM error")
    mock_factory.create.return_value = mock_llm

    result = await route_query("随便问个啥", mock_factory)
    assert result.intent == "item_query"
    assert result.confidence == 0.5
```

- [ ] **Step 6: Run all router tests**

Run: `conda run -n CSQAQ pytest tests/test_components/test_router.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/components/router.py tests/test_components/test_router.py
git commit -m "feat: add Router with keyword matching and LLM fallback"
```

---

## Task 7: Market Agent

**Files:**
- Create: `src/csqaq/components/agents/market.py`
- Test: `tests/test_components/test_market_agent.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_components/test_market_agent.py`:

```python
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.components.agents.market import fetch_market_data_node, analyze_market_node
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, SubData

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_market_api():
    api = AsyncMock()
    home = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    sub = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    api.get_home_data.return_value = HomeData.model_validate(home)
    api.get_sub_data.return_value = SubData.model_validate(sub)
    return api


@pytest.mark.asyncio
async def test_fetch_market_data_node(mock_market_api):
    state = {"query": "大盘怎么样", "home_data": None, "sub_data": None, "error": None}
    result = await fetch_market_data_node(state, market_api=mock_market_api)
    assert result["home_data"] is not None
    assert result["sub_data"] is not None
    assert "error" not in result or result.get("error") is None


@pytest.mark.asyncio
async def test_fetch_market_data_node_error():
    api = AsyncMock()
    api.get_home_data.side_effect = Exception("API down")
    state = {"query": "大盘怎么样", "home_data": None, "sub_data": None, "error": None}
    result = await fetch_market_data_node(state, market_api=api)
    assert result.get("error") is not None


@pytest.mark.asyncio
async def test_analyze_market_node():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="大盘整体偏强，BUFF指数连涨3天")
    mock_factory.create.return_value = mock_llm

    state = {
        "home_data": {"sub_index_data": [{"market_index": 1052.3, "chg_rate": 0.24}]},
        "sub_data": {"count": {"now": 1052.3, "consecutive_days": 3}},
        "market_context": None,
        "error": None,
    }
    result = await analyze_market_node(state, model_factory=mock_factory)
    assert result["market_context"] is not None
    assert "大盘" in result["market_context"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_components/test_market_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Market Agent**

Create `src/csqaq/components/agents/market.py`:

```python
"""Market Agent — analyzes overall market index and sentiment.

Node functions for the Market Flow LangGraph subgraph.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.market import MarketAPI

logger = logging.getLogger(__name__)

MARKET_ANALYST_PROMPT = """你是一个专业的 CS2 饰品市场分析师。你会收到大盘指数数据，你的任务是：

1. 总结当前大盘状态（指数值、涨跌幅、连涨/跌天数）
2. 分析涨跌分布（上涨/下跌/持平家数比例）
3. 判断市场情绪（结合情绪指标和在线人数）
4. 给出大盘方向判断（偏多/偏空/震荡）

使用中文回答。基于数据说话，不要凭空猜测。"""


async def fetch_market_data_node(state: dict, *, market_api: MarketAPI) -> dict:
    """Node: fetch home data and sub-index detail."""
    try:
        home_data = await market_api.get_home_data(type="init")
        sub_data = await market_api.get_sub_data(sub_id=1, type="daily")
        return {
            "home_data": home_data.model_dump(),
            "sub_data": sub_data.model_dump(),
        }
    except Exception as e:
        logger.error("fetch_market_data_node failed: %s", e)
        return {"error": f"获取大盘数据失败: {e}"}


async def analyze_market_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM analyzes market data and produces market_context."""
    if state.get("error"):
        return {"market_context": f"数据不足: {state['error']}"}

    home_data = state.get("home_data")
    sub_data = state.get("sub_data")
    if not home_data:
        return {"market_context": "无大盘数据可分析"}

    data_summary = json.dumps(
        {"home_data": home_data, "sub_data": sub_data},
        ensure_ascii=False,
        indent=2,
    )

    try:
        llm = model_factory.create("analyst")
        messages = [
            {"role": "system", "content": MARKET_ANALYST_PROMPT},
            {"role": "user", "content": f"请分析以下大盘数据:\n\n{data_summary}"},
        ]
        response = await llm.ainvoke(messages)
        return {"market_context": response.content}
    except Exception as e:
        logger.error("analyze_market_node failed: %s", e)
        return {"market_context": f"大盘分析出错: {e}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_components/test_market_agent.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/agents/market.py tests/test_components/test_market_agent.py
git commit -m "feat: add Market Agent with fetch and analyze nodes"
```

---

## Task 8: Scout Agent

**Files:**
- Create: `src/csqaq/components/agents/scout.py`
- Test: `tests/test_components/test_scout_agent.py`

- [ ] **Step 1: Write failing test for cross-filtering**

Create `tests/test_components/test_scout_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

from csqaq.components.agents.scout import cross_filter_ranks, fetch_rank_data_node, analyze_opportunities_node
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem


def _make_rank_item(id: int, name: str = "test") -> dict:
    return RankItem(
        id=id, name=name, img="", exterior_localized_name=None,
        rarity_localized_name="", buff_sell_price=0, buff_sell_num=0,
        buff_buy_price=0, buff_buy_num=0, steam_sell_price=0, steam_sell_num=0,
        yyyp_sell_price=0, yyyp_sell_num=0,
    ).model_dump()


class TestCrossFilter:
    def test_items_in_two_lists_are_selected(self):
        price_ids = [1, 2, 3, 4, 5]
        volume_ids = [3, 4, 5, 6, 7]
        sell_ids = [5, 6, 8, 9, 10]
        result = cross_filter_ranks(price_ids, volume_ids, sell_ids, top_n=10, min_overlap=2)
        # id=5 appears in all 3, id=3,4 in 2, id=6 in 2
        assert 5 in result
        assert 3 in result
        assert 4 in result
        assert 6 in result

    def test_backfill_when_insufficient(self):
        price_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        volume_ids = [11, 12, 13]
        sell_ids = [14, 15, 16]
        # No overlap >= 2, so backfill from price_ids
        result = cross_filter_ranks(price_ids, volume_ids, sell_ids, top_n=5, min_overlap=2)
        assert len(result) == 5
        # Should be backfilled from price_ids
        assert result[:5] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_fetch_rank_data_node():
    api = AsyncMock()
    api.get_rank_list.return_value = [
        RankItem.model_validate({
            "id": 1, "name": "test", "img": "", "exterior_localized_name": None,
            "rarity_localized_name": "", "buff_sell_price": 10, "buff_sell_num": 100,
            "buff_buy_price": 9, "buff_buy_num": 50, "steam_sell_price": 1.5,
            "steam_sell_num": 200, "yyyp_sell_price": 9.5, "yyyp_sell_num": 80,
        })
    ]
    state = {"query": "有什么推荐", "rank_data": None, "error": None}
    result = await fetch_rank_data_node(state, rank_api=api)
    assert result["rank_data"] is not None
    assert "price_change" in result["rank_data"]
    assert api.get_rank_list.call_count == 3  # 3 dimensions


@pytest.mark.asyncio
async def test_analyze_opportunities_node():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="推荐关注AK红线，量价配合良好")
    mock_factory.create.return_value = mock_llm

    state = {
        "rank_data": {
            "price_change": [_make_rank_item(1, "AK红线")],
            "volume": [_make_rank_item(1, "AK红线")],
            "sell_count": [_make_rank_item(2, "M4A4龙王")],
        },
        "scout_context": None,
        "error": None,
    }
    result = await analyze_opportunities_node(state, model_factory=mock_factory)
    assert result["scout_context"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_components/test_scout_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Scout Agent**

Create `src/csqaq/components/agents/scout.py`:

```python
"""Scout Agent — discovers investment opportunities from rankings.

Node functions for the Scout Flow LangGraph subgraph.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.rank import RankAPI

logger = logging.getLogger(__name__)

# Filter configs for the 3 ranking dimensions
RANK_FILTERS = {
    "price_change": {"排序": ["价格_近1天价格变动率_降序(BUFF)"]},
    "volume": {"排序": ["价格_BUFF在售数量_降序"]},
    "sell_count": {"排序": ["价格_BUFF在售数量_降序"]},
}

SCOUT_ANALYST_PROMPT = """你是一个专业的 CS2 饰品市场分析师。你会收到从排行榜交叉筛选出的饰品列表（在多个排行维度同时出现的饰品），你的任务是：

1. 总结每个推荐饰品的关键数据（价格、涨跌幅、成交量）
2. 分析为什么这些饰品值得关注（量价配合、异动信号等）
3. 按推荐优先级排序
4. 给出简短的投资建议

使用中文回答。基于数据说话，不要凭空猜测。"""


def cross_filter_ranks(
    price_ids: list[int],
    volume_ids: list[int],
    sell_ids: list[int],
    top_n: int = 10,
    min_overlap: int = 2,
) -> list[int]:
    """Cross-filter items that appear in multiple ranking dimensions.

    Returns list of good_ids sorted by overlap count (descending).
    If fewer than 5 results, backfills from price_ids.
    """
    counter: Counter[int] = Counter()
    counter.update(price_ids)
    counter.update(volume_ids)
    counter.update(sell_ids)

    # Items appearing in >= min_overlap dimensions
    filtered = [gid for gid, count in counter.most_common() if count >= min_overlap]

    # Backfill if insufficient
    if len(filtered) < 5:
        seen = set(filtered)
        for gid in price_ids:
            if gid not in seen:
                filtered.append(gid)
                seen.add(gid)
            if len(filtered) >= top_n:
                break

    return filtered[:top_n]


async def fetch_rank_data_node(state: dict, *, rank_api: RankAPI) -> dict:
    """Node: fetch ranking data for 3 dimensions."""
    try:
        rank_data = {}
        for dimension, filter_config in RANK_FILTERS.items():
            items = await rank_api.get_rank_list(filter=filter_config, page=1, size=20)
            rank_data[dimension] = [item.model_dump() for item in items]
        return {"rank_data": rank_data}
    except Exception as e:
        logger.error("fetch_rank_data_node failed: %s", e)
        return {"error": f"获取排行数据失败: {e}"}


async def analyze_opportunities_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: cross-filter + LLM analysis of opportunities."""
    if state.get("error"):
        return {"scout_context": f"数据不足: {state['error']}"}

    rank_data = state.get("rank_data")
    if not rank_data:
        return {"scout_context": "无排行数据可分析"}

    # Cross-filter
    price_ids = [item["id"] for item in rank_data.get("price_change", [])]
    volume_ids = [item["id"] for item in rank_data.get("volume", [])]
    sell_ids = [item["id"] for item in rank_data.get("sell_count", [])]
    top_ids = cross_filter_ranks(price_ids, volume_ids, sell_ids)

    # Collect full data for top items
    all_items = {item["id"]: item for dim in rank_data.values() for item in dim}
    top_items = [all_items[gid] for gid in top_ids if gid in all_items]

    if not top_items:
        return {"scout_context": "未找到符合条件的推荐饰品"}

    data_summary = json.dumps(top_items, ensure_ascii=False, indent=2)

    try:
        llm = model_factory.create("analyst")
        messages = [
            {"role": "system", "content": SCOUT_ANALYST_PROMPT},
            {"role": "user", "content": f"以下是交叉筛选出的饰品（在多个排行维度同时出现）:\n\n{data_summary}"},
        ]
        response = await llm.ainvoke(messages)
        return {"scout_context": response.content}
    except Exception as e:
        logger.error("analyze_opportunities_node failed: %s", e)
        return {"scout_context": f"机会分析出错: {e}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_components/test_scout_agent.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/agents/scout.py tests/test_components/test_scout_agent.py
git commit -m "feat: add Scout Agent with cross-filtering and ranking analysis"
```

---

## Task 9: Market Flow

**Files:**
- Create: `src/csqaq/flows/market_flow.py`
- Test: `tests/test_flows/test_market_flow.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_flows/test_market_flow.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.market_flow import build_market_flow


@pytest.mark.asyncio
async def test_market_flow_produces_result():
    mock_market_api = AsyncMock()
    mock_market_api.get_home_data.return_value = MagicMock(
        model_dump=lambda: {"sub_index_data": [{"market_index": 1052.3}]}
    )
    mock_market_api.get_sub_data.return_value = MagicMock(
        model_dump=lambda: {"count": {"now": 1052.3, "consecutive_days": 3}}
    )

    mock_factory = MagicMock()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="大盘偏强，连涨3天")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"recommendation": "大盘偏强，可适度加仓", "risk_level": "low"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    mock_factory.create = mock_create

    flow = build_market_flow(market_api=mock_market_api, model_factory=mock_factory)
    result = await flow.ainvoke({
        "messages": [],
        "query": "大盘怎么样",
        "home_data": None,
        "sub_data": None,
        "market_context": None,
        "recommendation": None,
        "risk_level": None,
        "error": None,
    })
    assert result.get("recommendation") is not None
    assert result.get("market_context") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_market_flow.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Market Flow**

Create `src/csqaq/flows/market_flow.py`:

```python
"""Market analysis LangGraph subgraph.

Graph: fetch_market_data → analyze_market → advise → END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.market import analyze_market_node, fetch_market_data_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.market import MarketAPI


class MarketFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    home_data: dict | None
    sub_data: dict | None
    market_context: str | None
    recommendation: str | None
    risk_level: str | None
    error: str | None


def _should_continue_after_fetch(state: MarketFlowState) -> str:
    if state.get("error"):
        return "advise"
    return "analyze_market"


def _prepare_advisor_context(state: MarketFlowState) -> dict:
    """Bridge node: pack market_context into Advisor's expected format."""
    return {
        "market_context": {"analysis_result": state.get("market_context", "")},
        "item_context": None,
        "scout_context": None,
    }


def build_market_flow(market_api: MarketAPI, model_factory: ModelFactory):
    """Build and compile the market analysis subgraph."""
    graph = StateGraph(MarketFlowState)

    graph.add_node("fetch_market_data", partial(fetch_market_data_node, market_api=market_api))
    graph.add_node("analyze_market", partial(analyze_market_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("fetch_market_data")
    graph.add_conditional_edges(
        "fetch_market_data",
        _should_continue_after_fetch,
        {"analyze_market": "analyze_market", "advise": "advise"},
    )
    graph.add_edge("analyze_market", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_market_flow.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/flows/market_flow.py tests/test_flows/test_market_flow.py
git commit -m "feat: add Market Flow LangGraph subgraph"
```

---

## Task 10: Scout Flow

**Files:**
- Create: `src/csqaq/flows/scout_flow.py`
- Test: `tests/test_flows/test_scout_flow.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_flows/test_scout_flow.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.scout_flow import build_scout_flow
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem


def _make_rank_items(ids: list[int]) -> list[RankItem]:
    return [
        RankItem(
            id=i, name=f"item_{i}", img="", exterior_localized_name=None,
            rarity_localized_name="", buff_sell_price=10*i, buff_sell_num=100,
            buff_buy_price=9*i, buff_buy_num=50, steam_sell_price=1.5*i,
            steam_sell_num=200, yyyp_sell_price=9.5*i, yyyp_sell_num=80,
        )
        for i in ids
    ]


@pytest.mark.asyncio
async def test_scout_flow_produces_result():
    mock_rank_api = AsyncMock()
    # Make items overlap: id=1 appears in all 3 dimensions
    mock_rank_api.get_rank_list.side_effect = [
        _make_rank_items([1, 2, 3]),  # price_change
        _make_rank_items([1, 4, 5]),  # volume
        _make_rank_items([1, 6, 7]),  # sell_count
    ]

    mock_factory = MagicMock()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="item_1量价配合良好，推荐关注")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"recommendation": "推荐关注item_1", "risk_level": "medium"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    mock_factory.create = mock_create

    flow = build_scout_flow(rank_api=mock_rank_api, model_factory=mock_factory)
    result = await flow.ainvoke({
        "messages": [],
        "query": "有什么推荐",
        "rank_data": None,
        "scout_context": None,
        "recommendation": None,
        "risk_level": None,
        "error": None,
    })
    assert result.get("scout_context") is not None
    assert result.get("recommendation") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_scout_flow.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Scout Flow**

Create `src/csqaq/flows/scout_flow.py`:

```python
"""Scout (opportunity discovery) LangGraph subgraph.

Graph: fetch_rank_data → analyze_opportunities → advise → END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.scout import analyze_opportunities_node, fetch_rank_data_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.rank import RankAPI


class ScoutFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    rank_data: dict | None
    scout_context: str | None
    recommendation: str | None
    risk_level: str | None
    error: str | None


def _should_continue_after_fetch(state: ScoutFlowState) -> str:
    if state.get("error"):
        return "advise"
    return "analyze_opportunities"


def _prepare_advisor_context(state: ScoutFlowState) -> dict:
    """Bridge node: pack scout_context into Advisor's expected format."""
    return {
        "scout_context": {"analysis_result": state.get("scout_context", "")},
        "item_context": None,
        "market_context": None,
    }


def build_scout_flow(rank_api: RankAPI, model_factory: ModelFactory):
    """Build and compile the scout subgraph."""
    graph = StateGraph(ScoutFlowState)

    graph.add_node("fetch_rank_data", partial(fetch_rank_data_node, rank_api=rank_api))
    graph.add_node("analyze_opportunities", partial(analyze_opportunities_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("fetch_rank_data")
    graph.add_conditional_edges(
        "fetch_rank_data",
        _should_continue_after_fetch,
        {"analyze_opportunities": "analyze_opportunities", "advise": "advise"},
    )
    graph.add_edge("analyze_opportunities", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_scout_flow.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/flows/scout_flow.py tests/test_flows/test_scout_flow.py
git commit -m "feat: add Scout Flow LangGraph subgraph"
```

---

## Task 11: Refactor Item Flow — Embed Advisor

**Files:**
- Modify: `src/csqaq/flows/item_flow.py`
- Modify: `tests/test_flows/test_item_flow.py`

- [ ] **Step 1: Update Item Flow to embed Advisor**

Modify `src/csqaq/flows/item_flow.py`:
- Add `recommendation`, `risk_level`, `requires_confirmation` fields to `ItemFlowState`
- Add `_prepare_advisor_context` bridge node
- Add `advise` node (reuse `advise_node` from advisor.py)
- Wire: `analyze → prepare_advisor → advise → END`

New state:
```python
class ItemFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    good_id: int | None
    good_name: str | None
    item_detail: dict | None
    chart_data: dict | None
    kline_data: list | None
    indicators: dict | None
    analysis_result: str | None
    # Advisor fields (new)
    item_context: dict | None
    market_context: dict | None
    scout_context: dict | None
    historical_advice: list | None
    recommendation: str | None
    risk_level: str | None
    requires_confirmation: bool
    error: str | None
```

New bridge node + wiring:
```python
def _prepare_advisor_context(state: ItemFlowState) -> dict:
    return {
        "item_context": {
            "analysis_result": state.get("analysis_result", ""),
            "item_detail": state.get("item_detail"),
            "indicators": state.get("indicators"),
        },
        "market_context": None,
        "scout_context": None,
    }


def build_item_flow(item_api: ItemAPI, model_factory: ModelFactory):
    graph = StateGraph(ItemFlowState)

    graph.add_node("resolve_item", partial(resolve_item_node, item_api=item_api))
    graph.add_node("fetch_chart", partial(fetch_chart_node, item_api=item_api))
    graph.add_node("analyze", partial(analyze_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("resolve_item")
    graph.add_conditional_edges(
        "resolve_item", _should_continue,
        {"analyze": "analyze", "fetch_chart": "fetch_chart"},
    )
    graph.add_edge("fetch_chart", "analyze")
    graph.add_edge("analyze", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()
```

- [ ] **Step 2: Update item flow tests**

Update `tests/test_flows/test_item_flow.py` to account for new Advisor fields in initial state and assertions. Add mock for advisor model:

```python
# Initial state needs new fields:
initial_state = {
    "messages": [],
    "good_id": None,
    "good_name": "AK红线",
    "item_detail": None,
    "chart_data": None,
    "kline_data": None,
    "indicators": None,
    "analysis_result": None,
    "item_context": None,
    "market_context": None,
    "scout_context": None,
    "historical_advice": None,
    "recommendation": None,
    "risk_level": None,
    "requires_confirmation": False,
    "error": None,
}

# mock_factory.create needs to return different mocks for analyst vs advisor
```

- [ ] **Step 3: Run tests to verify**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_item_flow.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/csqaq/flows/item_flow.py tests/test_flows/test_item_flow.py
git commit -m "refactor: embed Advisor into Item Flow for self-contained output"
```

---

## Task 12: Router Flow — Main Graph

**Files:**
- Create: `src/csqaq/flows/router_flow.py`
- Test: `tests/test_flows/test_router_flow.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_flows/test_router_flow.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.router_flow import build_router_flow


@pytest.mark.asyncio
async def test_router_dispatches_market_query():
    mock_item_api = AsyncMock()
    mock_market_api = AsyncMock()
    mock_market_api.get_home_data.return_value = MagicMock(
        model_dump=lambda: {"sub_index_data": [{"market_index": 1000}]}
    )
    mock_market_api.get_sub_data.return_value = MagicMock(
        model_dump=lambda: {"count": {"now": 1000, "consecutive_days": 1}}
    )
    mock_rank_api = AsyncMock()

    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"recommendation": "大盘稳定", "risk_level": "low"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_router_flow(
        item_api=mock_item_api,
        market_api=mock_market_api,
        rank_api=mock_rank_api,
        model_factory=mock_factory,
    )
    result = await flow.ainvoke({
        "messages": [],
        "query": "今天大盘怎么样",
        "intent": None,
        "item_name": None,
        "result": None,
        "error": None,
    })
    assert result.get("intent") == "market_query"
    assert result.get("result") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_router_flow.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Router Flow**

Create `src/csqaq/flows/router_flow.py`:

```python
"""Router Flow — main entry graph that dispatches to sub-flows.

Graph: router_node → conditional → item/market/scout subflow → format_result → END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.models.factory import ModelFactory
from csqaq.components.router import route_query
from csqaq.infrastructure.csqaq_client.item import ItemAPI
from csqaq.infrastructure.csqaq_client.market import MarketAPI
from csqaq.infrastructure.csqaq_client.rank import RankAPI


class RouterFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    intent: str | None
    item_name: str | None
    result: str | None
    error: str | None


async def _router_node(state: RouterFlowState, *, model_factory: ModelFactory) -> dict:
    """Node: classify query intent."""
    query = state["query"]
    intent_result = await route_query(query, model_factory)
    return {
        "intent": intent_result.intent,
        "item_name": intent_result.item_name,
    }


def _dispatch(state: RouterFlowState) -> str:
    intent = state.get("intent", "item_query")
    if intent == "market_query":
        return "market_subflow"
    elif intent == "scout_query":
        return "scout_subflow"
    return "item_subflow"


async def _item_subflow_node(
    state: RouterFlowState,
    *,
    item_api: ItemAPI,
    model_factory: ModelFactory,
) -> dict:
    """Node: run item flow and format result."""
    from csqaq.flows.item_flow import build_item_flow

    flow = build_item_flow(item_api=item_api, model_factory=model_factory)
    item_result = await flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": state.get("item_name") or state["query"],
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "item_context": None,
        "market_context": None,
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    parts = []
    if item_result.get("analysis_result"):
        parts.append(f"📊 分析:\n{item_result['analysis_result']}")
    if item_result.get("recommendation"):
        risk = item_result.get("risk_level", "unknown")
        parts.append(f"\n💡 建议 (风险: {risk}):\n{item_result['recommendation']}")

    return {"result": "\n".join(parts) if parts else f"查询失败: {item_result.get('error', '未知错误')}"}


async def _market_subflow_node(
    state: RouterFlowState,
    *,
    market_api: MarketAPI,
    model_factory: ModelFactory,
) -> dict:
    """Node: run market flow and format result."""
    from csqaq.flows.market_flow import build_market_flow

    flow = build_market_flow(market_api=market_api, model_factory=model_factory)
    market_result = await flow.ainvoke({
        "messages": [],
        "query": state["query"],
        "home_data": None,
        "sub_data": None,
        "market_context": None,
        "recommendation": None,
        "risk_level": None,
        "error": None,
    })

    parts = []
    if market_result.get("market_context"):
        parts.append(f"📊 大盘分析:\n{market_result['market_context']}")
    if market_result.get("recommendation"):
        risk = market_result.get("risk_level", "unknown")
        parts.append(f"\n💡 建议 (风险: {risk}):\n{market_result['recommendation']}")

    return {"result": "\n".join(parts) if parts else f"查询失败: {market_result.get('error', '未知错误')}"}


async def _scout_subflow_node(
    state: RouterFlowState,
    *,
    rank_api: RankAPI,
    model_factory: ModelFactory,
) -> dict:
    """Node: run scout flow and format result."""
    from csqaq.flows.scout_flow import build_scout_flow

    flow = build_scout_flow(rank_api=rank_api, model_factory=model_factory)
    scout_result = await flow.ainvoke({
        "messages": [],
        "query": state["query"],
        "rank_data": None,
        "scout_context": None,
        "recommendation": None,
        "risk_level": None,
        "error": None,
    })

    parts = []
    if scout_result.get("scout_context"):
        parts.append(f"🔍 机会发现:\n{scout_result['scout_context']}")
    if scout_result.get("recommendation"):
        risk = scout_result.get("risk_level", "unknown")
        parts.append(f"\n💡 建议 (风险: {risk}):\n{scout_result['recommendation']}")

    return {"result": "\n".join(parts) if parts else f"查询失败: {scout_result.get('error', '未知错误')}"}


def build_router_flow(
    item_api: ItemAPI,
    market_api: MarketAPI,
    rank_api: RankAPI,
    model_factory: ModelFactory,
):
    """Build and compile the main router graph."""
    graph = StateGraph(RouterFlowState)

    graph.add_node("router", partial(_router_node, model_factory=model_factory))
    graph.add_node("item_subflow", partial(_item_subflow_node, item_api=item_api, model_factory=model_factory))
    graph.add_node("market_subflow", partial(_market_subflow_node, market_api=market_api, model_factory=model_factory))
    graph.add_node("scout_subflow", partial(_scout_subflow_node, rank_api=rank_api, model_factory=model_factory))

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        _dispatch,
        {
            "item_subflow": "item_subflow",
            "market_subflow": "market_subflow",
            "scout_subflow": "scout_subflow",
        },
    )
    graph.add_edge("item_subflow", END)
    graph.add_edge("market_subflow", END)
    graph.add_edge("scout_subflow", END)

    return graph.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n CSQAQ pytest tests/test_flows/test_router_flow.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/flows/router_flow.py tests/test_flows/test_router_flow.py
git commit -m "feat: add Router Flow as main entry graph with conditional dispatch"
```

---

## Task 13: Entry Point — main.py + cli.py

**Files:**
- Modify: `src/csqaq/main.py`
- Modify: `src/csqaq/api/cli.py`
- Modify: `src/csqaq/infrastructure/csqaq_client/__init__.py`

- [ ] **Step 1: Update `__init__.py` exports**

Add to `src/csqaq/infrastructure/csqaq_client/__init__.py`:
```python
from .market import MarketAPI
from .rank import RankAPI
```

- [ ] **Step 2: Update `main.py`**

Changes:
1. Add `_market_api` and `_rank_api` to `App.__init__`
2. Initialize them in `App.init()`
3. Add `market_api` and `rank_api` properties with runtime guards
4. Replace `run_item_query` with `run_query`

```python
# In App.__init__:
self._market_api = None
self._rank_api = None

# In App.init():
from csqaq.infrastructure.csqaq_client.market import MarketAPI
from csqaq.infrastructure.csqaq_client.rank import RankAPI
self._market_api = MarketAPI(self._csqaq_client)
self._rank_api = RankAPI(self._csqaq_client)

# New properties:
@property
def market_api(self):
    if self._market_api is None:
        raise RuntimeError("App not initialized — call await app.init() first")
    return self._market_api

@property
def rank_api(self):
    if self._rank_api is None:
        raise RuntimeError("App not initialized — call await app.init() first")
    return self._rank_api

# Replace run_item_query:
async def run_query(app: App, query: str) -> str:
    """Run a query through the router flow."""
    from csqaq.flows.router_flow import build_router_flow

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

- [ ] **Step 3: Update `cli.py`**

Replace all references to `run_item_query` with `run_query`:
```python
from csqaq.main import App, run_query, setup_logging
```

- [ ] **Step 4: Run full test suite**

Run: `conda run -n CSQAQ pytest tests/ -v`
Expected: ALL existing tests PASS (may need to update E2E test in next task)

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/main.py src/csqaq/api/cli.py src/csqaq/infrastructure/csqaq_client/__init__.py
git commit -m "feat: wire MarketAPI + RankAPI into App, replace run_item_query with run_query"
```

---

## Task 14: Update E2E Test + conftest

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_e2e.py`

- [ ] **Step 1: Add mock fixtures to conftest.py**

Add to `tests/conftest.py`:

```python
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, SubData
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem

@pytest.fixture
def mock_market_api():
    api = AsyncMock()
    home = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    sub = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    api.get_home_data.return_value = HomeData.model_validate(home)
    api.get_sub_data.return_value = SubData.model_validate(sub)
    return api

@pytest.fixture
def mock_rank_api():
    api = AsyncMock()
    rank_data = json.loads((FIXTURES / "rank_list_response.json").read_text(encoding="utf-8"))
    api.get_rank_list.return_value = [RankItem.model_validate(item) for item in rank_data["data"]]
    page_data = json.loads((FIXTURES / "page_list_response.json").read_text(encoding="utf-8"))
    from csqaq.infrastructure.csqaq_client.rank_schemas import PageListItem
    api.get_page_list.return_value = [PageListItem.model_validate(item) for item in page_data["data"]]
    return api
```

- [ ] **Step 2: Update E2E test for router-based flow**

Update `tests/test_e2e.py` to use `run_query` instead of `run_item_query`, and add market/scout E2E tests.

- [ ] **Step 3: Run full test suite**

Run: `conda run -n CSQAQ pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_e2e.py
git commit -m "test: update E2E tests for router-based query flow"
```

---

## Task 15: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `conda run -n CSQAQ pytest tests/ -v --tb=short`
Expected: ALL PASS, 0 failures

- [ ] **Step 2: Verify no import errors**

Run: `conda run -n CSQAQ python -c "from csqaq.flows.router_flow import build_router_flow; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Count total tests**

Run: `conda run -n CSQAQ pytest tests/ --co -q`
Expected: Significant increase from Phase 1's ~50 tests

- [ ] **Step 4: Final commit + push**

```bash
git push origin master
```
