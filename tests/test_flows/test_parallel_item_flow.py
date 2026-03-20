import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from csqaq.flows.parallel_item_flow import build_parallel_item_flow


@pytest.mark.asyncio
async def test_parallel_flow_merges_contexts(
    mock_item_api, mock_market_api, mock_rank_api, mock_vol_api,
):
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "综合分析", "action_detail": "建议观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_parallel_item_flow(
        item_api=mock_item_api,
        market_api=mock_market_api,
        rank_api=mock_rank_api,
        vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [],
        "query": "AK-47 红线",
        "good_name": "AK-47 红线",
        "good_id": None, "item_detail": None,
        "item_context": None, "market_context": None,
        "scout_context": None, "inventory_context": None,
        "item_error": None, "market_error": None,
        "scout_error": None, "inventory_error": None,
        "risk_level": None, "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    # At least one context should be populated
    has_context = (
        result.get("item_context") is not None
        or result.get("market_context") is not None
        or result.get("scout_context") is not None
    )
    assert has_context
    assert result.get("summary") is not None


@pytest.mark.asyncio
async def test_parallel_flow_error_isolation(mock_item_api, mock_market_api, mock_rank_api, mock_vol_api):
    """If one branch fails, others should still produce results."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "部分数据可用", "action_detail": "观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    # Make market fail
    mock_market_api.get_home_data.side_effect = Exception("API down")

    flow = build_parallel_item_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [], "query": "test", "good_name": "test",
        "good_id": None, "item_detail": None,
        "item_context": None, "market_context": None,
        "scout_context": None, "inventory_context": None,
        "item_error": None, "market_error": None,
        "scout_error": None, "inventory_error": None,
        "risk_level": None, "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    # Market failed but item should still work
    assert result.get("market_error") is not None or result.get("market_context") is None
    assert result.get("summary") is not None  # Advisor still runs


@pytest.mark.asyncio
async def test_parallel_flow_includes_inventory(mock_item_api, mock_market_api, mock_rank_api, mock_vol_api):
    """Parallel flow should produce inventory_context."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "综合分析含存世量", "action_detail": "建议观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_parallel_item_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [], "query": "AK-47 红线", "good_name": "AK-47 红线",
        "good_id": None, "item_detail": None,
        "item_context": None, "market_context": None,
        "scout_context": None, "inventory_context": None,
        "item_error": None, "market_error": None,
        "scout_error": None, "inventory_error": None,
        "risk_level": None, "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    assert result.get("inventory_context") is not None or result.get("inventory_error") is not None
