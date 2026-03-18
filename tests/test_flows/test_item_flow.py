import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.flows.item_flow import build_item_flow, ItemFlowState
from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ItemDetail,
    SuggestItem,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_item_api():
    api = AsyncMock()
    suggest_data = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    api.search_suggest.return_value = [SuggestItem.model_validate(s) for s in suggest_data]

    detail_data = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    api.get_item_detail.return_value = ItemDetail.model_validate(detail_data)

    chart_data = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    api.get_item_chart.return_value = ChartData.model_validate(chart_data)

    api.get_item_kline.return_value = []
    return api


@pytest.mark.asyncio
async def test_item_flow_produces_analysis(mock_item_api):
    """Item flow should produce an analysis_result in the final state."""
    from langchain_core.messages import AIMessage

    mock_factory = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="AK-47红线近期表现稳定，价格在83-85元区间震荡。")
    mock_factory.create.return_value = mock_llm

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
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is None
    assert result.get("analysis_result") is not None
    assert len(result["analysis_result"]) > 0


@pytest.mark.asyncio
async def test_item_flow_handles_search_failure(mock_item_api):
    """When search fails, error should be written to state."""
    mock_item_api.search_suggest.side_effect = Exception("API down")

    mock_factory = AsyncMock()
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
    }
    result = await flow.ainvoke(initial_state)
    assert result.get("error") is not None
