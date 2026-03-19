from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.router_flow import build_router_flow


@pytest.mark.asyncio
async def test_router_dispatches_item_query(mock_item_api, mock_market_api, mock_rank_api, mock_vol_api):
    """Item query should dispatch to parallel_item_flow via item_subflow node."""
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"summary": "AK红线短期偏空", "action_detail": "建议观望。", "risk_level": "low"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_router_flow(
        item_api=mock_item_api,
        market_api=mock_market_api,
        rank_api=mock_rank_api,
        vol_api=mock_vol_api,
        model_factory=mock_factory,
    )
    result = await flow.ainvoke({
        "messages": [],
        "query": "AK红线最近怎么样",
        "intent": None,
        "item_name": None,
        "result": None,
        "error": None,
    })
    assert result.get("intent") == "item_query"
    assert result.get("result") is not None


@pytest.mark.asyncio
async def test_router_dispatches_market_query():
    mock_item_api = AsyncMock()
    mock_market_api = AsyncMock()
    mock_market_api.get_home_data.return_value = MagicMock(
        model_dump=lambda: {"sub_index_data": [{"market_index": 1000}]}
    )
    mock_market_api.get_sub_data.return_value = MagicMock(
        model_dump=lambda: {"count": {"now": 1000, "consecutive_days": 1}}
    )
    mock_rank_api = AsyncMock()
    mock_vol_api = AsyncMock()

    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"summary": "大盘稳定", "action_detail": "维持现有仓位，短期无需操作。", "risk_level": "low"}'
    )
    mock_factory.create.return_value = mock_llm

    flow = build_router_flow(
        item_api=mock_item_api,
        market_api=mock_market_api,
        rank_api=mock_rank_api,
        vol_api=mock_vol_api,
        model_factory=mock_factory,
    )
    result = await flow.ainvoke({
        "messages": [],
        "query": "今天大盘怎么样",
        "intent": None,
        "item_name": None,
        "result": None,
        "error": None,
    })
    assert result.get("intent") == "market_query"
    assert result.get("result") is not None
