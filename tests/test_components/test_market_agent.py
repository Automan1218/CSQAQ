import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.components.agents.market import fetch_market_data_node, analyze_market_node
from csqaq.infrastructure.csqaq_client.market_schemas import HomeData, SubData

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_market_api():
    api = AsyncMock()
    home = json.loads((FIXTURES / "home_data_response.json").read_text(encoding="utf-8"))
    sub = json.loads((FIXTURES / "sub_data_response.json").read_text(encoding="utf-8"))
    api.get_home_data.return_value = HomeData.model_validate(home)
    api.get_sub_data.return_value = SubData.model_validate(sub)
    return api


@pytest.mark.asyncio
async def test_fetch_market_data_node(mock_market_api):
    state = {"query": "大盘怎么样", "home_data": None, "sub_data": None, "error": None}
    result = await fetch_market_data_node(state, market_api=mock_market_api)
    assert result["home_data"] is not None
    assert result["sub_data"] is not None
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_fetch_market_data_node_error():
    api = AsyncMock()
    api.get_home_data.side_effect = Exception("API down")
    state = {"query": "大盘怎么样", "home_data": None, "sub_data": None, "error": None}
    result = await fetch_market_data_node(state, market_api=api)
    assert result.get("error") is not None


@pytest.mark.asyncio
async def test_analyze_market_node():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="大盘整体偏强，BUFF指数连涨3天")
    mock_factory.create.return_value = mock_llm

    state = {
        "home_data": {"sub_index_data": [{"market_index": 1052.3, "chg_rate": 0.24}]},
        "sub_data": {"count": {"now": 1052.3, "consecutive_days": 3}},
        "market_context": None,
        "error": None,
    }
    result = await analyze_market_node(state, model_factory=mock_factory)
    assert result["market_context"] is not None
    assert "大盘" in result["market_context"]
