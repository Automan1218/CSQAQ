import json
from pathlib import Path

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.vol import VolAPI
from csqaq.infrastructure.csqaq_client.vol_schemas import VolItem

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASE = "https://api.csqaq.com/api/v1"


@pytest.fixture
def client():
    return CSQAQClient(base_url=BASE, api_token="test", rate_limit=100.0)


@pytest.fixture
def vol_api(client):
    return VolAPI(client)


def test_vol_item_parse():
    data = {
        "id": 150, "good_id": 14675, "name": "梦魇武器箱",
        "img": "https://example.com/img.png", "group": "其他",
        "statistic": 7908, "updated_at": "2026-03-18T15:00:18",
        "avg_price": 5.643, "sum_price": 44624.8, "special": 0,
    }
    item = VolItem.model_validate(data)
    assert item.good_id == 14675
    assert item.statistic == 7908
    assert item.avg_price == 5.643


@respx.mock
@pytest.mark.asyncio
async def test_get_vol_data(vol_api):
    data = json.loads((FIXTURES / "vol_data_response.json").read_text(encoding="utf-8"))
    respx.post(f"{BASE}/info/vol_data_info").mock(
        return_value=httpx.Response(200, json={"code": 200, "msg": "Success", "data": data})
    )
    items = await vol_api.get_vol_data()
    assert len(items) == 2
    assert isinstance(items[0], VolItem)
    assert items[0].statistic == 7908
    assert items[1].name == "AK-47 | 二西莫夫 (久经沙场)"
