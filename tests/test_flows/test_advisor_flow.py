from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.advisor_flow import AdvisorFlowState, build_advisor_flow


@pytest.mark.asyncio
async def test_advisor_produces_recommendation():
    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"recommendation": "建议持有观望，近期价格稳定", "risk_level": "low"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_advisor_flow(model_factory=mock_factory)
    initial_state: AdvisorFlowState = {
        "messages": [],
        "market_context": None,
        "item_context": {"analysis_result": "AK-47红线近期价格稳定在83-85元区间"},
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("recommendation") is not None
    assert result.get("risk_level") in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_advisor_sets_confirmation_for_high_risk():
    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"recommendation": "建议立即清仓AK红线", "risk_level": "high"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_advisor_flow(model_factory=mock_factory)
    initial_state: AdvisorFlowState = {
        "messages": [],
        "market_context": None,
        "item_context": {"analysis_result": "AK-47红线暴跌15%"},
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("risk_level") == "high"
    assert result.get("requires_confirmation") is True
