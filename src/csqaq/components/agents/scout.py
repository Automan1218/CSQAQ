"""Scout Agent -- discovers investment opportunities from rankings + volume."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.rank import RankAPI
    from csqaq.infrastructure.csqaq_client.vol import VolAPI

from csqaq.infrastructure.csqaq_client.rank_filters import RANK_FILTERS

logger = logging.getLogger(__name__)

PRICE_CHANGE_FILTER = {"排序": ["价格_近1天价格变动率_降序(BUFF)"]}

SCOUT_ANALYST_PROMPT = """你是一个专业的 CS2 饰品市场分析师。你会收到从排行榜和成交量交叉筛选出的饰品列表
（在涨跌幅排行和成交量排行中同时出现的饰品），你的任务是：

1. 总结每个推荐饰品的关键数据（价格、涨跌幅、成交量）
2. 分析为什么这些饰品值得关注（量价配合、异动信号等）
3. 按推荐优先级排序
4. 给出简短的投资建议

使用中文回答。基于数据说话，不要凭空猜测。"""


def cross_filter_ranks(
    *id_lists: list[int],
    top_n: int = 10,
    min_overlap: int = 2,
) -> list[int]:
    """Cross-filter items appearing in N ranking lists.

    Returns list of good_ids sorted by overlap count (descending).
    If fewer than 5 results, backfills from the first list.
    """
    counter: Counter[int] = Counter()
    for id_list in id_lists:
        counter.update(id_list)

    filtered = [gid for gid, count in counter.most_common() if count >= min_overlap]

    if len(filtered) == 0 and id_lists:
        seen: set[int] = set()
        for id_list in id_lists:
            for gid in id_list:
                if gid not in seen:
                    filtered.append(gid)
                    seen.add(gid)
                if len(filtered) >= top_n:
                    break
            if len(filtered) >= top_n:
                break

    return filtered[:top_n]


async def fetch_rank_data_node(state: dict, *, rank_api: RankAPI, vol_api: VolAPI) -> dict:
    """Node: fetch 6 ranking dimensions + trading volume data concurrently."""
    try:
        price_task = rank_api.get_rank_list(filter=RANK_FILTERS["price_up_7d"], page=1, size=50)
        stock_task = rank_api.get_rank_list(filter=RANK_FILTERS["stock_asc"], page=1, size=50)
        sell_task = rank_api.get_rank_list(filter=RANK_FILTERS["sell_decrease_7d"], page=1, size=50)
        buy_task = rank_api.get_rank_list(filter=RANK_FILTERS["buy_increase_7d"], page=1, size=50)
        cap_task = rank_api.get_rank_list(filter=RANK_FILTERS["market_cap_desc"], page=1, size=50)
        vol_task = vol_api.get_vol_data()

        price_items, stock_items, sell_items, buy_items, cap_items, vol_items = await asyncio.gather(
            price_task, stock_task, sell_task, buy_task, cap_task, vol_task,
        )

        return {
            "rank_data": {
                "price_change": [item.model_dump() for item in price_items],
                "volume": [item.model_dump() for item in vol_items],
                "stock": [item.model_dump() for item in stock_items],
                "sell_decrease": [item.model_dump() for item in sell_items],
                "buy_increase": [item.model_dump() for item in buy_items],
                "market_cap": [item.model_dump() for item in cap_items],
            }
        }
    except Exception as e:
        logger.error("fetch_rank_data_node failed: %s", e)
        return {"error": f"获取排行数据失败: {e}"}


async def analyze_opportunities_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: cross-filter + LLM analysis of opportunities."""
    if state.get("error"):
        return {"scout_context": f"数据不足: {state['error']}"}

    rank_data = state.get("rank_data")
    if not rank_data:
        return {"scout_context": "无排行数据可分析"}

    # Extract IDs: rank_list uses "id", vol_data uses "good_id"
    price_ids = [item["id"] for item in rank_data.get("price_change", [])]
    vol_ids = [item["good_id"] for item in rank_data.get("volume", [])]
    stock_ids = [item["id"] for item in rank_data.get("stock", [])]
    sell_ids = [item["id"] for item in rank_data.get("sell_decrease", [])]
    buy_ids = [item["id"] for item in rank_data.get("buy_increase", [])]
    cap_ids = [item["id"] for item in rank_data.get("market_cap", [])]
    top_ids = cross_filter_ranks(price_ids, vol_ids, stock_ids, sell_ids, buy_ids, cap_ids)

    # Collect full data for top items from all dimension maps
    price_map = {item["id"]: item for item in rank_data.get("price_change", [])}
    vol_map = {item["good_id"]: item for item in rank_data.get("volume", [])}
    stock_map = {item["id"]: item for item in rank_data.get("stock", [])}
    sell_map = {item["id"]: item for item in rank_data.get("sell_decrease", [])}
    buy_map = {item["id"]: item for item in rank_data.get("buy_increase", [])}
    cap_map = {item["id"]: item for item in rank_data.get("market_cap", [])}

    top_items = []
    for gid in top_ids:
        entry = {}
        if gid in price_map:
            entry["price_change"] = price_map[gid]
        if gid in vol_map:
            entry["vol_data"] = vol_map[gid]
        if gid in stock_map:
            entry["stock"] = stock_map[gid]
        if gid in sell_map:
            entry["sell_decrease"] = sell_map[gid]
        if gid in buy_map:
            entry["buy_increase"] = buy_map[gid]
        if gid in cap_map:
            entry["market_cap"] = cap_map[gid]
        if entry:
            top_items.append(entry)

    if not top_items:
        return {"scout_context": "未找到符合条件的推荐饰品"}

    data_summary = json.dumps(top_items, ensure_ascii=False, indent=2)

    try:
        llm = model_factory.create("analyst")
        messages = [
            {"role": "system", "content": SCOUT_ANALYST_PROMPT},
            {"role": "user", "content": f"以下是交叉筛选出的饰品:\n\n{data_summary}"},
        ]
        response = await llm.ainvoke(messages)
        return {"scout_context": response.content}
    except Exception as e:
        logger.error("analyze_opportunities_node failed: %s", e)
        return {"scout_context": f"机会分析出错: {e}"}
