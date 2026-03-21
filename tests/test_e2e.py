"""End-to-end test: query -> item flow -> advisor flow -> recommendation."""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.components.models.factory import ModelFactory
from csqaq.flows.item_flow import build_item_flow
from csqaq.flows.parallel_item_flow import build_parallel_item_flow


@pytest.mark.asyncio
async def test_full_item_to_advisor_pipeline(mock_item_api):
    """Complete pipeline: search item -> analyze -> advise (advisor now embedded in item flow)."""
    factory = ModelFactory()

    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(
        content="AK-47红线当前Buff售价85.5元，买价82元，价差4.3%。Steam售价12.35美元。"
        "日涨幅1.25%，周跌2.3%，月涨5.6%。近30日价格在83-85.5元区间震荡，波动较小。"
        "成交量稳定，流动性良好。技术面偏中性。"
    )
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "AK-47红线近期价格稳定，月度仍有5.6%涨幅。建议持有观望。",'
        ' "action_detail": "不建议追高。如回调至82元以下可小额加仓。", "risk_level": "low"}'
    )

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    factory.create = mock_create

    item_flow = build_item_flow(item_api=mock_item_api, model_factory=factory)
    result = await item_flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": "AK红线",
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "ta_report": None,
        "indicators": None,
        "analysis_result": None,
        "item_context": None,
        "market_context": None,
        "scout_context": None,
        "historical_advice": None,
        "summary": None,
        "action_detail": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    assert result.get("error") is None
    assert result["good_id"] == 7310
    assert result["analysis_result"] is not None
    assert "AK-47" in result["analysis_result"]
    assert result["summary"] is not None
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_full_market_pipeline(mock_market_api):
    factory = ModelFactory()
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

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    factory.create = mock_create

    from csqaq.flows.market_flow import build_market_flow
    flow = build_market_flow(market_api=mock_market_api, model_factory=factory)
    result = await flow.ainvoke({
        "messages": [], "query": "大盘怎么样",
        "home_data": None, "sub_data": None, "index_ta_report": None, "market_context": None,
        "item_context": None, "scout_context": None, "historical_advice": None,
        "summary": None, "action_detail": None, "risk_level": None,
        "requires_confirmation": False, "error": None,
    })
    assert result["summary"] is not None
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_full_parallel_item_pipeline(mock_item_api, mock_market_api, mock_rank_api, mock_vol_api):
    """Complete parallel pipeline: item + market + scout in parallel -> single advisor."""
    factory = ModelFactory()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="分析完成")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "综合分析：大盘偏强，AK红线可持有", "action_detail": "建议持有观望", "risk_level": "low"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    factory.create = mock_create

    flow = build_parallel_item_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=factory,
    )
    result = await flow.ainvoke({
        "messages": [], "query": "AK红线", "good_name": "AK红线",
        "good_id": None, "item_detail": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "inventory_context": None,
        "item_error": None, "market_error": None, "scout_error": None,
        "inventory_error": None,
        "risk_level": None, "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    # At least one context populated
    has_context = (
        result.get("item_context") is not None
        or result.get("market_context") is not None
        or result.get("scout_context") is not None
    )
    assert has_context
    assert result.get("summary") is not None


@pytest.mark.asyncio
async def test_hitl_high_risk_result(mock_item_api):
    """Verify high-risk advisor output sets requires_confirmation."""
    factory = ModelFactory()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="价格暴跌分析")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "AK红线暴跌20%", "action_detail": "建议立即清仓", "risk_level": "high"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    factory.create = mock_create

    item_flow = build_item_flow(item_api=mock_item_api, model_factory=factory)
    result = await item_flow.ainvoke({
        "messages": [], "good_id": None, "good_name": "AK红线",
        "item_detail": None, "chart_data": None, "kline_data": None,
        "ta_report": None, "indicators": None, "analysis_result": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "historical_advice": None, "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False, "error": None,
    })

    assert result["risk_level"] == "high"
    assert result["requires_confirmation"] is True
    assert result["summary"] is not None
    assert result["action_detail"] is not None


@pytest.mark.asyncio
async def test_full_inventory_pipeline(mock_item_api):
    """Complete inventory pipeline: resolve -> fetch inventory -> analyze -> interpret -> advise."""
    factory = ModelFactory()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="存世量持续下降，疑似吸货行为")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "存世量下降，符合吸货模式", "action_detail": "可小额建仓试探", "risk_level": "medium"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    factory.create = mock_create

    from csqaq.flows.inventory_flow import build_inventory_flow
    flow = build_inventory_flow(item_api=mock_item_api, model_factory=factory)
    result = await flow.ainvoke({
        "messages": [], "query": "AK红线存世量趋势",
        "good_name": "AK红线",
        "good_id": None, "item_detail": None,
        "inventory_stats": None, "inventory_report": None,
        "inventory_context": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False,
        "error": None,
    })

    assert result.get("summary") is not None
    assert result.get("risk_level") == "medium"
    assert result.get("inventory_context") is not None
