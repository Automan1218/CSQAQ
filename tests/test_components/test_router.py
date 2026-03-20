import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

from csqaq.components.router import IntentResult, classify_intent_by_keywords, classify_intent_by_llm, route_query


class TestKeywordRouter:
    def test_market_keywords(self):
        result = classify_intent_by_keywords("今天大盘怎么样")
        assert result is not None
        assert result.intent == "market_query"
        assert result.confidence == 1.0

    def test_market_keyword_指数(self):
        result = classify_intent_by_keywords("饰品指数走势如何")
        assert result is not None
        assert result.intent == "market_query"

    def test_scout_keywords(self):
        result = classify_intent_by_keywords("有什么值得买的")
        assert result is not None
        assert result.intent == "scout_query"

    def test_scout_keyword_排行(self):
        result = classify_intent_by_keywords("涨幅排行前十")
        assert result is not None
        assert result.intent == "scout_query"

    def test_no_match_returns_none(self):
        result = classify_intent_by_keywords("AK红线能入吗")
        assert result is None

    def test_market_priority_over_scout(self):
        result = classify_intent_by_keywords("大盘行情中有什么值得买的")
        assert result is not None
        assert result.intent == "market_query"


class TestInventoryIntent:
    def test_keyword_inventory(self):
        result = classify_intent_by_keywords("AK47红线的存世量趋势")
        assert result is not None
        assert result.intent == "inventory_query"

    def test_keyword_absorption(self):
        result = classify_intent_by_keywords("有没有人在吸货")
        assert result is not None
        assert result.intent == "inventory_query"

    def test_keyword_control(self):
        result = classify_intent_by_keywords("这个饰品有控盘嫌疑吗")
        assert result is not None
        assert result.intent == "inventory_query"

    @pytest.mark.asyncio
    async def test_llm_inventory_intent(self):
        model_factory = MagicMock()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"intent": "inventory_query", "item_name": "AK-47 红线"}'
        )
        model_factory.create.return_value = mock_llm

        result = await classify_intent_by_llm("AK47红线的存世量变化怎么样", model_factory)
        assert result.intent == "inventory_query"
        assert result.item_name == "AK-47 红线"


@pytest.mark.asyncio
async def test_route_query_keyword_shortcut():
    """route_query returns keyword result without calling LLM."""
    mock_factory = MagicMock()
    result = await route_query("今天大盘怎么样", mock_factory)
    assert result.intent == "market_query"
    mock_factory.create.assert_not_called()


@pytest.mark.asyncio
async def test_llm_fallback_item_query():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='{"intent": "item_query", "item_name": "AK红线"}'
    )
    mock_factory.create.return_value = mock_llm

    result = await route_query("AK红线能入吗", mock_factory)
    assert result.intent == "item_query"
    assert result.item_name == "AK红线"
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_llm_failure_defaults_to_item():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("LLM error")
    mock_factory.create.return_value = mock_llm

    result = await route_query("随便问个啥", mock_factory)
    assert result.intent == "item_query"
    assert result.confidence == 0.5
