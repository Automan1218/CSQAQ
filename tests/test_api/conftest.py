# tests/test_api/conftest.py
"""Shared fixtures for API route tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
