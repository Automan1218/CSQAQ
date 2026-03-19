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
