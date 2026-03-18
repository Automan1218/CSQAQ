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

    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
    api.get_item_kline.return_value = [KlineBar.model_validate(k) for k in kline_data]

    return api
