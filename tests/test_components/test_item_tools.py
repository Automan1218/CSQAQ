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

    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    kline_data = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
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
