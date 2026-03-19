import pytest
from unittest.mock import AsyncMock

from csqaq.components.agents.scout import cross_filter_ranks, fetch_rank_data_node


class TestCrossFilterRanksVariadic:
    def test_two_lists_overlap(self):
        price_ids = [1, 2, 3, 4, 5]
        vol_ids = [3, 4, 5, 6, 7]
        result = cross_filter_ranks(price_ids, vol_ids, min_overlap=2)
        assert 3 in result
        assert 4 in result
        assert 5 in result

    def test_three_lists_overlap(self):
        list_a = [1, 2, 3, 4, 5]
        list_b = [3, 4, 5, 6, 7]
        list_c = [4, 5, 8, 9, 10]
        result = cross_filter_ranks(list_a, list_b, list_c, min_overlap=3)
        assert 4 in result
        assert 5 in result
        assert 3 not in result  # only in 2 lists

    def test_min_overlap_2_with_backfill(self):
        list_a = [1, 2, 3]
        list_b = [4, 5, 6]
        # No overlap at min_overlap=2, should backfill from first list
        result = cross_filter_ranks(list_a, list_b, min_overlap=2)
        assert len(result) >= 5  # backfill ensures at least 5

    def test_single_list(self):
        result = cross_filter_ranks([1, 2, 3, 4, 5], min_overlap=1)
        assert result == [1, 2, 3, 4, 5]

    def test_empty_lists(self):
        result = cross_filter_ranks([], [], min_overlap=2)
        assert result == []


@pytest.mark.asyncio
async def test_fetch_multi_dimension():
    rank_api = AsyncMock()
    vol_api = AsyncMock()

    # Mock rank_api to return items with id field for each filter call
    rank_api.get_rank_list.return_value = [
        type("Item", (), {"id": i, "model_dump": lambda self=None, i=i: {"id": i}})()
        for i in range(1, 6)
    ]
    vol_api.get_vol_data.return_value = [
        type("Vol", (), {"good_id": i, "model_dump": lambda self=None, i=i: {"good_id": i}})()
        for i in range(3, 8)
    ]

    result = await fetch_rank_data_node({}, rank_api=rank_api, vol_api=vol_api)
    rank_data = result["rank_data"]

    # Should have multiple dimension keys
    assert "price_change" in rank_data
    assert "volume" in rank_data
    assert "stock" in rank_data
    assert "sell_decrease" in rank_data
    assert "buy_increase" in rank_data
    assert "market_cap" in rank_data

    # rank_api.get_rank_list should be called 5 times (once per filter dimension)
    assert rank_api.get_rank_list.call_count == 5
    # Verify different filters were passed
    filter_args = [call.kwargs.get("filter") or call.args[0] for call in rank_api.get_rank_list.call_args_list]
    filter_strs = [str(f) for f in filter_args]
    assert any("价格" in s for s in filter_strs)
    assert any("存世量" in s for s in filter_strs)
    assert any("在售数量" in s for s in filter_strs)
