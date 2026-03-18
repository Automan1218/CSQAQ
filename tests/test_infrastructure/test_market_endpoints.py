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
    result = await market_api.get_sub_data(sub_id=1, data_type="daily")
    assert isinstance(result, SubData)
    assert result.count.now == 1052.3
    assert result.count.consecutive_days == 3
    assert len(result.main_data) == 3
