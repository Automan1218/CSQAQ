"""Router -- keyword + LLM intent classification."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    intent: str          # "item_query" | "market_query" | "scout_query"
    confidence: float    # 1.0 for keyword, 0.8 for LLM
    item_name: str | None


_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("market_query", ["大盘", "指数", "行情", "市场", "涨跌分布"]),
    ("scout_query", ["排行", "推荐", "值得买", "值得入", "机会", "捡漏", "热门"]),
]


def classify_intent_by_keywords(query: str) -> IntentResult | None:
    """Try to classify intent by keyword matching. Returns None if no match."""
    for intent, keywords in _KEYWORD_RULES:
        for kw in keywords:
            if kw in query:
                return IntentResult(intent=intent, confidence=1.0, item_name=None)
    return None


ROUTER_SYSTEM_PROMPT = """你是一个查询意图分类器。将用户查询分为三类:
- item_query: 询问某个具体饰品的价格、走势、是否值得入手
- market_query: 询问大盘、市场整体行情、指数
- scout_query: 询问推荐、排行、值得关注的饰品

输出严格 JSON: {"intent": "...", "item_name": "饰品名或null"}"""


async def classify_intent_by_llm(query: str, model_factory: ModelFactory) -> IntentResult:
    """Classify intent using LLM as fallback."""
    try:
        llm = model_factory.create("router")
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        response = await llm.ainvoke(messages)
        parsed = json.loads(response.content)
        intent = parsed.get("intent", "item_query")
        if intent not in ("item_query", "market_query", "scout_query"):
            intent = "item_query"
        return IntentResult(
            intent=intent,
            confidence=0.8,
            item_name=parsed.get("item_name"),
        )
    except Exception as e:
        logger.warning("LLM router failed: %s, defaulting to item_query", e)
        return IntentResult(intent="item_query", confidence=0.5, item_name=query)


async def route_query(query: str, model_factory: ModelFactory) -> IntentResult:
    """Route a query: keyword match first, LLM fallback."""
    result = classify_intent_by_keywords(query)
    if result is not None:
        return result
    return await classify_intent_by_llm(query, model_factory)
