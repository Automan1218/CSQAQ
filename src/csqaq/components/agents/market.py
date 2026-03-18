"""Market Agent -- analyzes overall market index and sentiment."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.market import MarketAPI

logger = logging.getLogger(__name__)

MARKET_ANALYST_PROMPT = """你是一个专业的 CS2 饰品市场分析师。基于大盘指数数据：

1. 总结当前大盘状态（指数值、涨跌幅、连涨/跌天数）
2. 分析涨跌分布（上涨/下跌/持平家数比例）
3. 判断市场情绪（结合情绪指标和在线人数）
4. 给出大盘方向判断（偏多/偏空/震荡）

使用中文回答。基于数据说话，不要凭空猜测。"""


async def fetch_market_data_node(state: dict, *, market_api: "MarketAPI") -> dict:
    """Node: fetch home data and sub-index detail."""
    try:
        home_data = await market_api.get_home_data()
        sub_data = await market_api.get_sub_data(sub_id=1)
        return {
            "home_data": home_data.model_dump(),
            "sub_data": sub_data.model_dump(),
        }
    except Exception as e:
        logger.error("fetch_market_data_node failed: %s", e)
        return {"error": f"获取大盘数据失败: {e}"}


async def analyze_market_node(state: dict, *, model_factory: "ModelFactory") -> dict:
    """Node: LLM analyzes market data and produces market_context."""
    if state.get("error"):
        return {"market_context": f"数据不足: {state['error']}"}

    home_data = state.get("home_data")
    sub_data = state.get("sub_data")
    if not home_data:
        return {"market_context": "无大盘数据可分析"}

    data_summary = json.dumps(
        {"home_data": home_data, "sub_data": sub_data},
        ensure_ascii=False, indent=2,
    )

    try:
        llm = model_factory.create("analyst")
        messages = [
            {"role": "system", "content": MARKET_ANALYST_PROMPT},
            {"role": "user", "content": f"请分析以下大盘数据:\n\n{data_summary}"},
        ]
        response = await llm.ainvoke(messages)
        return {"market_context": response.content}
    except Exception as e:
        logger.error("analyze_market_node failed: %s", e)
        return {"market_context": f"大盘分析出错: {e}"}
