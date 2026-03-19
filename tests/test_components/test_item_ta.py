import pytest
from unittest.mock import AsyncMock, MagicMock
from csqaq.components.agents.item import fetch_chart_node


@pytest.mark.asyncio
async def test_fetch_chart_includes_ta_report(mock_item_api):
    state = {"good_id": 123, "error": None}
    result = await fetch_chart_node(state, item_api=mock_item_api)
    assert "ta_report" in result
    ta = result["ta_report"]
    assert "signals" in ta
    assert "overall_direction" in ta
    assert "indicators" in ta
