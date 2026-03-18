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
    assert items[0].name == "蝴蝶刀 | 蓝钢 (崭新出厂)"
