"""Item Agent — analyzes a single CS2 skin's price, trend, and technical indicators.

Node functions for the Item Flow LangGraph subgraph.
"""
from __future__ import annotations

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

from csqaq.infrastructure.analysis.indicators import TechnicalIndicators

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.item import ItemAPI

logger = logging.getLogger(__name__)

ITEM_ANALYST_SYSTEM_PROMPT = """你是一个专业的 CS2 饰品市场分析师。你会收到一个饰品的详细数据（多平台价格、涨跌幅、技术指标等），你的任务是：

1. 总结当前价格状态（各平台价格、价差情况）
2. 分析近期趋势（日/周/月涨跌幅、均线位置、波动率）
3. 指出值得关注的信号（异常价差、放量/缩量、趋势转折等）
4. 给出简短的技术面总结

使用中文回答。基于数据说话，不要凭空猜测。"""


async def resolve_item_node(state: dict, *, item_api: ItemAPI) -> dict:
    """Node: resolve item name to good_id via search, then fetch detail."""
    try:
        good_id = state.get("good_id")
        good_name = state.get("good_name", "")

        # If no good_id, search by name
        if good_id is None and good_name:
            results = await item_api.search_suggest(good_name)
            if not results:
                return {"error": f"未找到饰品: {good_name}"}
            good_id = results[0].good_id

        if good_id is None:
            return {"error": "无法确定饰品 ID"}

        # Fetch detail
        detail = await item_api.get_item_detail(good_id)
        return {
            "good_id": good_id,
            "item_detail": detail.model_dump(),
        }
    except Exception as e:
        logger.error("resolve_item_node failed: %s", e)
        return {"error": f"获取饰品信息失败: {e}"}


async def fetch_chart_node(state: dict, *, item_api: ItemAPI) -> dict:
    """Node: fetch chart data and compute technical indicators."""
    if state.get("error"):
        return {}

    good_id = state.get("good_id")
    if good_id is None:
        return {}

    try:
        chart = await item_api.get_item_chart(good_id, platform="buff", period="30d")
        chart_dict = chart.model_dump()

        # Compute indicators if we have enough data
        indicators: dict[str, Any] = {}
        if chart.points and len(chart.points) >= 3:
            prices = [p.price for p in chart.points]
            volumes = [p.volume for p in chart.points]

            ma_7 = TechnicalIndicators.moving_average(prices, window=7)
            latest_ma7 = next((v for v in reversed(ma_7) if v is not None), None)

            indicators = {
                "current_price": prices[-1],
                "MA_7": round(latest_ma7, 2) if latest_ma7 else None,
                "volatility": round(TechnicalIndicators.volatility(prices, window=min(len(prices), 30)), 2),
                "momentum_7d": round(TechnicalIndicators.price_momentum(prices, period=min(len(prices) - 1, 7)), 2),
                "volume_trend": TechnicalIndicators.volume_trend(volumes, window=min(len(volumes) // 2, 7) or 1),
                "price_range": f"{min(prices):.2f} - {max(prices):.2f}",
            }

        return {"chart_data": chart_dict, "indicators": indicators}
    except Exception as e:
        logger.warning("fetch_chart_node failed: %s", e)
        return {"chart_data": None, "indicators": None}


async def analyze_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM analyzes collected data and produces analysis_result."""
    if state.get("error"):
        return {"analysis_result": f"分析失败: {state['error']}"}

    detail = state.get("item_detail")
    indicators = state.get("indicators")
    if detail is None:
        return {"analysis_result": "无数据可分析"}

    # Build context for LLM
    data_summary = json.dumps(
        {"item_detail": detail, "indicators": indicators},
        ensure_ascii=False,
        indent=2,
    )

    llm_or_coro = model_factory.create("analyst")
    llm = await llm_or_coro if inspect.isawaitable(llm_or_coro) else llm_or_coro
    messages = [
        {"role": "system", "content": ITEM_ANALYST_SYSTEM_PROMPT},
        {"role": "user", "content": f"请分析以下饰品数据:\n\n{data_summary}"},
    ]
    response = await llm.ainvoke(messages)
    return {"analysis_result": response.content}
