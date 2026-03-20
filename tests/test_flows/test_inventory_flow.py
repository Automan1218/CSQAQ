import pytest
from unittest.mock import AsyncMock, MagicMock
from csqaq.flows.inventory_flow import build_inventory_flow


@pytest.mark.asyncio
async def test_inventory_flow_end_to_end(mock_item_api):
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "存世量下降，关注吸货", "action_detail": "小额建仓", "risk_level": "medium"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_inventory_flow(item_api=mock_item_api, model_factory=model_factory)
    result = await flow.ainvoke({
        "messages": [], "query": "AK-47 红线存世量",
        "good_name": "AK-47 红线",
        "good_id": None, "item_detail": None,
        "inventory_stats": None, "inventory_report": None,
        "inventory_context": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False,
        "error": None,
    })

    assert result.get("summary") is not None
    assert result.get("inventory_context") is not None or result.get("error") is not None
