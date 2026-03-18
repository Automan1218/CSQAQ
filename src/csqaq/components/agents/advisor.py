"""Advisor Agent — synthesizes analysis data into investment recommendations.

Uses GPT-5 for deep reasoning. Outputs structured JSON with recommendation + risk_level.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory

logger = logging.getLogger(__name__)

ADVISOR_SYSTEM_PROMPT = """你是一位经验丰富的 CS2 饰品投资顾问。你的任务是根据分析数据给出投资建议。

你会收到以下上下文（部分可能为空）：
- item_context: 单品分析结果
- market_context: 大盘分析结果
- scout_context: 机会发现结果
- historical_advice: 历史分析参考

请综合分析后，输出严格 JSON 格式：
{
  "recommendation": "详细的投资建议（中文，100-300字）",
  "risk_level": "low" | "medium" | "high"
}

风险等级标准：
- low: 观望、小额建仓、长期持有
- medium: 加仓、减仓、平台间套利
- high: 大额买入、清仓、追涨杀跌

基于数据说话，给出理由。如果数据不足，标注数据缺失并给出保守建议。"""


async def advise_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM produces investment recommendation."""
    context_parts = []

    if state.get("item_context"):
        context_parts.append(f"## 单品分析\n{json.dumps(state['item_context'], ensure_ascii=False, indent=2)}")
    if state.get("market_context"):
        context_parts.append(f"## 大盘分析\n{json.dumps(state['market_context'], ensure_ascii=False, indent=2)}")
    if state.get("scout_context"):
        context_parts.append(f"## 机会发现\n{json.dumps(state['scout_context'], ensure_ascii=False, indent=2)}")

    if not context_parts:
        return {
            "recommendation": "数据不足，无法给出建议。请先查询具体饰品或大盘数据。",
            "risk_level": "low",
            "requires_confirmation": False,
        }

    context = "\n\n".join(context_parts)

    try:
        llm = model_factory.create("advisor")

        messages = [
            {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"请基于以下数据给出投资建议:\n\n{context}"},
        ]
        response = await llm.ainvoke(messages)

        # Parse structured output
        try:
            parsed = json.loads(response.content)
            recommendation = parsed.get("recommendation", response.content)
            risk_level = parsed.get("risk_level", "low")
        except json.JSONDecodeError:
            recommendation = response.content
            risk_level = "low"

        if risk_level not in ("low", "medium", "high"):
            risk_level = "medium"

        return {
            "recommendation": recommendation,
            "risk_level": risk_level,
            "requires_confirmation": risk_level == "high",
        }
    except Exception as e:
        logger.error("advise_node failed: %s", e)
        return {
            "recommendation": f"分析出错: {e}",
            "risk_level": "low",
            "requires_confirmation": False,
            "error": str(e),
        }
