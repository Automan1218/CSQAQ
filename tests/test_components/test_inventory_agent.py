import pytest
from unittest.mock import AsyncMock, MagicMock

from csqaq.components.agents.inventory import (
    fetch_inventory_node,
    analyze_inventory_node,
    interpret_inventory_node,
)
from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat


def _make_stats(count: int = 30, start: int = 30000, delta: int = -50) -> list[InventoryStat]:
    """Generate test inventory stats."""
    return [
        InventoryStat(statistic=start + i * delta, created_at=f"2026-01-{i+1:02d}T00:00:00")
        for i in range(count)
    ]


class TestFetchInventoryNode:
    @pytest.mark.asyncio
    async def test_success(self):
        item_api = AsyncMock()
        stats = _make_stats()
        item_api.get_item_statistic.return_value = stats

        state = {"good_id": 7310, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)

        assert "inventory_stats" in result
        assert len(result["inventory_stats"]) == 30
        item_api.get_item_statistic.assert_called_once_with(7310)

    @pytest.mark.asyncio
    async def test_skip_on_error(self):
        item_api = AsyncMock()
        state = {"good_id": 7310, "error": "previous error"}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result == {}
        item_api.get_item_statistic.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_good_id(self):
        item_api = AsyncMock()
        state = {"good_id": None, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result == {}

    @pytest.mark.asyncio
    async def test_api_failure(self):
        item_api = AsyncMock()
        item_api.get_item_statistic.side_effect = Exception("API error")
        state = {"good_id": 7310, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result.get("inventory_stats") is None


class TestAnalyzeInventoryNode:
    def test_produces_report(self):
        state = {
            "inventory_stats": [
                {"statistic": 30000 - i * 50, "created_at": f"2026-01-{i+1:02d}T00:00:00"}
                for i in range(30)
            ],
        }
        result = analyze_inventory_node(state)
        assert "inventory_report" in result
        assert result["inventory_report"]["trend_direction"] == "decreasing"

    def test_skip_without_stats(self):
        state = {"inventory_stats": None}
        result = analyze_inventory_node(state)
        assert result == {}


class TestInterpretInventoryNode:
    @pytest.mark.asyncio
    async def test_produces_context(self):
        model_factory = MagicMock()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="存世量持续下降，疑似有盘主在吸货。")
        model_factory.create.return_value = mock_llm

        state = {
            "inventory_report": {
                "trend_direction": "decreasing",
                "velocity": -50.0,
                "signals": [],
                "indicators": {"ma7": 28500},
                "summary": "存世量下降",
            },
            "item_context": {"item_detail": {"name": "AK-47 红线"}},
        }
        result = await interpret_inventory_node(state, model_factory=model_factory)

        assert "inventory_context" in result
        assert isinstance(result["inventory_context"], str)
        model_factory.create.assert_called_once_with("analyst")

    @pytest.mark.asyncio
    async def test_skip_without_report(self):
        model_factory = MagicMock()
        state = {"inventory_report": None}
        result = await interpret_inventory_node(state, model_factory=model_factory)
        assert result == {}
