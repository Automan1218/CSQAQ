import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, IndexKlineBar, SubData
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem
from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    KlineBar,
    SuggestItem,
)
from csqaq.infrastructure.csqaq_client.vol_schemas import VolItem

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_dir():
    return FIXTURES


@pytest.fixture
def mock_item_api():
    """Fully mocked ItemAPI with fixture data."""
    api = AsyncMock()

    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
    api.get_item_kline.return_value = [KlineBar.model_validate(k) for k in kline_data]

    stat_data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
    api.get_item_statistic.return_value = [InventoryStat.model_validate(s) for s in stat_data]

    return api


@pytest.fixture
def mock_market_api():
    api = AsyncMock()
    home = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    sub = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    api.get_home_data.return_value = HomeData.model_validate(home)
    api.get_sub_data.return_value = SubData.model_validate(sub)
    index_kline = json.loads((FIXTURES / "index_kline_response.json").read_text(encoding="utf-8"))
    api.get_index_kline.return_value = [IndexKlineBar.model_validate(k) for k in index_kline]
    return api


@pytest.fixture
def mock_rank_api():
    api = AsyncMock()
    rank = json.loads((FIXTURES / "rank_list_response.json").read_text(encoding="utf-8"))
    api.get_rank_list.return_value = [RankItem.model_validate(i) for i in rank["data"]]
    return api


@pytest.fixture
def mock_vol_api():
    api = AsyncMock()
    vol = json.loads((FIXTURES / "vol_data_response.json").read_text(encoding="utf-8"))
    api.get_vol_data.return_value = [VolItem.model_validate(i) for i in vol]
    return api
