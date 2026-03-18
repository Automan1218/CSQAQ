"""End-to-end test: query -> item flow -> advisor flow -> recommendation."""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.components.models.factory import ModelFactory
from csqaq.flows.advisor_flow import build_advisor_flow
from csqaq.flows.item_flow import build_item_flow


@pytest.mark.asyncio
async def test_full_item_to_advisor_pipeline(mock_item_api):
    """Complete pipeline: search item -> analyze -> advise."""
    # Set up model factory with mock LLMs
    factory = ModelFactory()

    # Mock analyst LLM
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(
        content="AK-47红线当前Buff售价85.5元，买价82元，价差4.3%。Steam售价12.35美元。"
        "日涨幅1.25%，周跌2.3%，月涨5.6%。近30日价格在83-85.5元区间震荡，波动较小。"
        "成交量稳定，流动性良好。技术面偏中性。"
    )

    # Mock advisor LLM
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"recommendation": "AK-47红线近期价格稳定，月度仍有5.6%涨幅。'
        '建议持有观望，不建议追高。如回调至82元以下可小额加仓。", "risk_level": "low"}'
    )

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    # Override create to return our mocks
    original_create = factory.create

    def mock_create(role):
        if role == "analyst":
            return mock_analyst
        elif role == "advisor":
            return mock_advisor
        return original_create(role)

    factory.create = mock_create

    # Build flows
    item_flow = build_item_flow(item_api=mock_item_api, model_factory=factory)
    advisor_flow = build_advisor_flow(model_factory=factory)

    # Run item flow
    item_result = await item_flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": "AK红线",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    })

    assert item_result.get("error") is None
    assert item_result["good_id"] == 7310
    assert item_result["analysis_result"] is not None
    assert "AK-47" in item_result["analysis_result"]

    # Run advisor flow with item context
    advisor_result = await advisor_flow.ainvoke({
        "messages": [],
        "market_context": None,
        "item_context": {
            "analysis_result": item_result["analysis_result"],
            "item_detail": item_result.get("item_detail"),
            "indicators": item_result.get("indicators"),
        },
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    assert advisor_result["recommendation"] is not None
    assert advisor_result["risk_level"] == "low"
    assert advisor_result["requires_confirmation"] is False
    assert "AK-47" in advisor_result["recommendation"]
