import pytest

from csqaq.components.tools.item_tools import create_item_tools


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
