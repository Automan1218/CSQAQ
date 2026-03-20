import json
from pathlib import Path

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.item import ItemAPI
from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat
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
    data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
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
    data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/good").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    detail = await item_api.get_item_detail(7310)
    assert isinstance(detail, ItemDetail)
    assert detail.buff_sell_price == 85.50


@respx.mock
@pytest.mark.asyncio
async def test_get_item_chart(item_api):
    data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/chart").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    chart = await item_api.get_item_chart(7310, platform="buff", period="30d")
    assert isinstance(chart, ChartData)
    assert len(chart.points) == 3


@respx.mock
@pytest.mark.asyncio
async def test_get_item_kline(item_api):
    data = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/simple/chartAll").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    bars = await item_api.get_item_kline(7310, platform="buff", periods="30d")
    assert len(bars) == 2
    assert isinstance(bars[0], KlineBar)


@respx.mock
@pytest.mark.asyncio
async def test_get_item_statistic(item_api):
    data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
    respx.get(f"{BASE}/info/good/statistic").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    stats = await item_api.get_item_statistic(7310)
    assert len(stats) > 0
    assert isinstance(stats[0], InventoryStat)
