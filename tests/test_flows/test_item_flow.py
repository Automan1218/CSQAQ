from unittest.mock import AsyncMock, MagicMock

import pytest

from csqaq.flows.item_flow import build_item_flow, ItemFlowState


@pytest.mark.asyncio
async def test_item_flow_produces_analysis(mock_item_api):
    """Item flow should produce an analysis_result in the final state."""
    from langchain_core.messages import AIMessage

    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="AK-47红线近期表现稳定，价格在83-85元区间震荡。")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "建议持有", "action_detail": "维持现有仓位，观察后续走势。", "risk_level": "low"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    mock_factory = MagicMock()
    mock_factory.create = mock_create

    flow = build_item_flow(item_api=mock_item_api, model_factory=mock_factory)
    initial_state: ItemFlowState = {
        "messages": [],
        "good_id": None,
        "good_name": "AK红线",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
        "item_context": None,
        "market_context": None,
        "scout_context": None,
        "historical_advice": None,
        "summary": None,
        "action_detail": None,
        "risk_level": None,
        "requires_confirmation": False,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is None
    assert result.get("analysis_result") is not None
    assert len(result["analysis_result"]) > 0
    assert result.get("summary") is not None


@pytest.mark.asyncio
async def test_item_flow_handles_search_failure(mock_item_api):
    """When search fails, error should be written to state."""
    mock_item_api.search_suggest.side_effect = Exception("API down")

    mock_factory = MagicMock()
    mock_factory.create.return_value = AsyncMock()

    flow = build_item_flow(item_api=mock_item_api, model_factory=mock_factory)
    initial_state: ItemFlowState = {
        "messages": [],
        "good_id": None,
        "good_name": "不存在的饰品",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
        "item_context": None,
        "market_context": None,
        "scout_context": None,
        "historical_advice": None,
        "summary": None,
        "action_detail": None,
        "risk_level": None,
        "requires_confirmation": False,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is not None
