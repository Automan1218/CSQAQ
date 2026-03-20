import pytest
from unittest.mock import AsyncMock, MagicMock
from csqaq.components.agents.advisor import advise_node


@pytest.mark.asyncio
async def test_advisor_returns_summary_and_action_detail():
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "大盘偏弱", "action_detail": "建议减仓50%", "risk_level": "high"}'
    )
    model_factory.create.return_value = mock_llm

    state = {"item_context": {"analysis_result": "test data"}}
    result = await advise_node(state, model_factory=model_factory)

    assert "summary" in result
    assert "action_detail" in result
    assert result["risk_level"] == "high"
    assert result["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_advisor_empty_context():
    model_factory = MagicMock()
    result = await advise_node({}, model_factory=model_factory)
    assert "summary" in result
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_advisor_with_inventory_context():
    """Advisor should include inventory_context when present."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "存世量下降，疑似吸货", "action_detail": "建议小额建仓", "risk_level": "medium"}'
    )
    model_factory.create.return_value = mock_llm

    state = {
        "item_context": {"analysis_result": "价格稳定"},
        "market_context": None,
        "scout_context": None,
        "inventory_context": "存世量近30天持续下降约5%，符合盘主吸货模式。",
    }

    result = await advise_node(state, model_factory=model_factory)
    assert result["summary"] == "存世量下降，疑似吸货"

    # Verify inventory context was included in the LLM prompt
    call_args = mock_llm.ainvoke.call_args[0][0]
    user_msg = call_args[1]["content"]
    assert "存世量" in user_msg
