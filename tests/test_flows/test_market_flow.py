from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.market_flow import build_market_flow


@pytest.mark.asyncio
async def test_market_flow_produces_result():
    mock_market_api = AsyncMock()
    mock_market_api.get_home_data.return_value = MagicMock(
        model_dump=lambda: {"sub_index_data": [{"market_index": 1052.3}]}
    )
    mock_market_api.get_sub_data.return_value = MagicMock(
        model_dump=lambda: {"count": {"now": 1052.3, "consecutive_days": 3}}
    )

    mock_factory = MagicMock()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="大盘偏强，连涨3天")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "大盘偏强，可适度加仓", "action_detail": "建议适度增加仓位，控制单次买入金额。", "risk_level": "low"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    mock_factory.create = mock_create

    flow = build_market_flow(market_api=mock_market_api, model_factory=mock_factory)
    result = await flow.ainvoke({
        "messages": [],
        "query": "大盘怎么样",
        "home_data": None,
        "sub_data": None,
        "market_context": None,
        "item_context": None,
        "scout_context": None,
        "historical_advice": None,
        "summary": None,
        "action_detail": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })
    assert result.get("summary") is not None
    assert result.get("market_context") is not None
