import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

from csqaq.components.agents.scout import (
    cross_filter_ranks, fetch_rank_data_node, analyze_opportunities_node,
)
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem
from csqaq.infrastructure.csqaq_client.vol_schemas import VolItem


def _make_rank_item(id: int, name: str = "test") -> dict:
    return RankItem(
        id=id, name=name, img="", exterior_localized_name=None,
        rarity_localized_name="", buff_sell_price=0, buff_sell_num=0,
        buff_buy_price=0, buff_buy_num=0, steam_sell_price=0, steam_sell_num=0,
        yyyp_sell_price=0, yyyp_sell_num=0,
    ).model_dump()


class TestCrossFilter:
    def test_items_in_both_lists(self):
        price_ids = [1, 2, 3, 4, 5]
        vol_ids = [3, 4, 5, 6, 7]
        result = cross_filter_ranks(price_ids, vol_ids, top_n=10, min_overlap=2)
        # id=3,4,5 appear in both
        assert 3 in result
        assert 4 in result
        assert 5 in result

    def test_backfill_when_insufficient(self):
        price_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        vol_ids = [11, 12, 13]
        # No overlap, so backfill from price_ids
        result = cross_filter_ranks(price_ids, vol_ids, top_n=5, min_overlap=2)
        assert len(result) == 5
        assert result[:5] == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_fetch_rank_data_node():
    mock_rank_api = AsyncMock()
    mock_rank_api.get_rank_list.return_value = [
        RankItem.model_validate({
            "id": 1, "name": "test", "img": "", "exterior_localized_name": None,
            "rarity_localized_name": "", "buff_sell_price": 10, "buff_sell_num": 100,
            "buff_buy_price": 9, "buff_buy_num": 50, "steam_sell_price": 1.5,
            "steam_sell_num": 200, "yyyp_sell_price": 9.5, "yyyp_sell_num": 80,
        })
    ]
    mock_vol_api = AsyncMock()
    mock_vol_api.get_vol_data.return_value = [
        VolItem.model_validate({
            "id": 10, "good_id": 1, "name": "test", "img": "",
            "group": "步枪", "statistic": 500, "updated_at": "2026-03-18",
            "avg_price": 10.0, "sum_price": 5000.0, "special": 0,
        })
    ]
    state = {"query": "有什么推荐", "rank_data": None, "error": None}
    result = await fetch_rank_data_node(state, rank_api=mock_rank_api, vol_api=mock_vol_api)
    assert result["rank_data"] is not None
    assert "price_change" in result["rank_data"]
    assert "volume" in result["rank_data"]


@pytest.mark.asyncio
async def test_analyze_opportunities_node():
    mock_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="推荐关注AK红线，量价配合良好")
    mock_factory.create.return_value = mock_llm

    state = {
        "rank_data": {
            "price_change": [_make_rank_item(1, "AK红线")],
            "volume": [{"good_id": 1, "name": "AK红线", "statistic": 500}],
        },
        "scout_context": None,
        "error": None,
    }
    result = await analyze_opportunities_node(state, model_factory=mock_factory)
    assert result["scout_context"] is not None
