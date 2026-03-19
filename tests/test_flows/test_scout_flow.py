from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from csqaq.flows.scout_flow import build_scout_flow
from csqaq.infrastructure.csqaq_client.rank_schemas import RankItem
from csqaq.infrastructure.csqaq_client.vol_schemas import VolItem


def _make_rank_items(ids: list[int]) -> list[RankItem]:
    return [
        RankItem(
            id=i, name=f"item_{i}", img="", exterior_localized_name=None,
            rarity_localized_name="", buff_sell_price=10*i, buff_sell_num=100,
            buff_buy_price=9*i, buff_buy_num=50, steam_sell_price=1.5*i,
            steam_sell_num=200, yyyp_sell_price=9.5*i, yyyp_sell_num=80,
        )
        for i in ids
    ]


def _make_vol_items(good_ids: list[int]) -> list[VolItem]:
    return [
        VolItem(
            id=100+gid, good_id=gid, name=f"item_{gid}", img="",
            group="步枪", statistic=500-gid*10, updated_at="2026-03-18",
            avg_price=10.0*gid, sum_price=5000.0, special=0,
        )
        for gid in good_ids
    ]


@pytest.mark.asyncio
async def test_scout_flow_produces_result():
    mock_rank_api = AsyncMock()
    mock_rank_api.get_rank_list.return_value = _make_rank_items([1, 2, 3])
    mock_vol_api = AsyncMock()
    mock_vol_api.get_vol_data.return_value = _make_vol_items([1, 4, 5])

    mock_factory = MagicMock()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="item_1量价配合良好")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "推荐关注item_1", "action_detail": "item_1量价配合良好，可小额建仓试探。", "risk_level": "medium"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    mock_factory.create = mock_create

    flow = build_scout_flow(
        rank_api=mock_rank_api, vol_api=mock_vol_api, model_factory=mock_factory,
    )
    result = await flow.ainvoke({
        "messages": [],
        "query": "有什么推荐",
        "rank_data": None,
        "scout_context": None,
        "item_context": None,
        "market_context": None,
        "historical_advice": None,
        "summary": None,
        "action_detail": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })
    assert result.get("scout_context") is not None
    assert result.get("summary") is not None
