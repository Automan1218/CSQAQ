import pytest
from unittest.mock import AsyncMock
from csqaq.components.agents.market import fetch_market_data_node


@pytest.mark.asyncio
async def test_fetch_market_includes_index_kline_ta(mock_market_api):
    state = {}
    result = await fetch_market_data_node(state, market_api=mock_market_api)
    assert "index_ta_report" in result
    ta = result["index_ta_report"]
    assert "overall_direction" in ta
