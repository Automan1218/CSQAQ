"""Inventory Agent — analyzes CS2 skin inventory (存世量) trends.

Three node functions for the inventory analysis LangGraph subgraph:
fetch → analyze → interpret.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from csqaq.components.analysis.inventory_analyzer import analyze_inventory
from csqaq.rules import load_inventory_rules

if TYPE_CHECKING:
    from csqaq.components.models.factory import ModelFactory
    from csqaq.infrastructure.csqaq_client.item import ItemAPI

logger = logging.getLogger(__name__)

INVENTORY_INTERPRET_SYSTEM_PROMPT = """你是 CS2 饰品存世量分析专家。根据以下规则库和分析数据，判断当前饰品的存世量趋势含义。

## 规则库
{rules_text}

## 分析数据
{inventory_report}

## 价格参考（如果有）
{item_context}

请根据数据判断哪些规则适用，给出你的解读。如果没有规则匹配，给出你基于数据的独立判断。使用中文回答。"""


async def fetch_inventory_node(state: dict, *, item_api: ItemAPI) -> dict:
    """Node: fetch 90-day inventory data from API."""
    if state.get("error"):
        return {}

    good_id = state.get("good_id")
    if not good_id:
        return {}

    try:
        stats = await item_api.get_item_statistic(good_id)
        return {"inventory_stats": [s.model_dump() for s in stats]}
    except Exception as e:
        logger.warning("fetch_inventory_node failed: %s", e)
        return {"inventory_stats": None}


def analyze_inventory_node(state: dict) -> dict:
    """Node: pure computation — analyze inventory time series."""
    stats = state.get("inventory_stats")
    if not stats:
        return {}

    values = [s["statistic"] for s in stats]
    report = analyze_inventory(values)
    return {"inventory_report": asdict(report)}


async def interpret_inventory_node(state: dict, *, model_factory: ModelFactory) -> dict:
    """Node: LLM interprets inventory analysis against YAML rules."""
    report = state.get("inventory_report")
    if not report:
        return {}

    # Load rules
    rules = load_inventory_rules()
    rules_text = "\n".join(f"- {r['name']}: {r['description']}" for r in rules)

    # Item context (price info if available)
    item_ctx = state.get("item_context")
    item_context_str = json.dumps(item_ctx, ensure_ascii=False, indent=2) if item_ctx else "无价格数据"

    # Build prompt
    report_str = json.dumps(report, ensure_ascii=False, indent=2)
    system_prompt = INVENTORY_INTERPRET_SYSTEM_PROMPT.format(
        rules_text=rules_text,
        inventory_report=report_str,
        item_context=item_context_str,
    )

    llm = model_factory.create("analyst")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请分析当前饰品的存世量趋势并给出判断。"},
    ]
    response = await llm.ainvoke(messages)
    return {"inventory_context": response.content}
