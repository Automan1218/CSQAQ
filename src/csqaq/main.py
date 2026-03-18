# src/csqaq/main.py
"""Application entry point and dependency wiring."""
from __future__ import annotations

import asyncio
import logging
import sys

from rich.logging import RichHandler

from csqaq.config import Settings


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


class App:
    """Application container — holds all initialized services."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._csqaq_client = None
        self._item_api = None
        self._model_factory = None
        self._database = None

    async def init(self) -> None:
        from csqaq.components.models.factory import ModelFactory
        from csqaq.infrastructure.csqaq_client.client import CSQAQClient
        from csqaq.infrastructure.csqaq_client.item import ItemAPI
        from csqaq.infrastructure.database.connection import Database

        # CSQAQ Client
        self._csqaq_client = CSQAQClient(
            base_url=self.settings.csqaq_base_url,
            api_token=self.settings.csqaq_api_token,
            rate_limit=self.settings.csqaq_rate_limit,
        )
        self._item_api = ItemAPI(self._csqaq_client)

        # LLM Factory
        self._model_factory = ModelFactory()
        self._model_factory.register("router", provider="openai", model=self.settings.router_model, temperature=0.0)
        self._model_factory.register("analyst", provider="openai", model=self.settings.analyst_model, temperature=0.3)
        self._model_factory.register("advisor", provider="openai", model=self.settings.advisor_model, temperature=0.5)

        # Database
        self._database = Database(self.settings.database_url)
        await self._database.init()

    @property
    def item_api(self):
        return self._item_api

    @property
    def model_factory(self):
        return self._model_factory

    @property
    def database(self):
        return self._database

    async def close(self) -> None:
        if self._csqaq_client:
            await self._csqaq_client.close()
        if self._database:
            await self._database.close()


async def run_item_query(app: App, query: str) -> str:
    """Run a single item analysis query end-to-end."""
    from csqaq.flows.advisor_flow import build_advisor_flow
    from csqaq.flows.item_flow import build_item_flow

    # Build flows
    item_flow = build_item_flow(item_api=app.item_api, model_factory=app.model_factory)
    advisor_flow = build_advisor_flow(model_factory=app.model_factory)

    # Run item analysis
    item_result = await item_flow.ainvoke({
        "messages": [],
        "good_id": None,
        "good_name": query,
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "analysis_result": None,
        "error": None,
    })

    if item_result.get("error") and not item_result.get("analysis_result"):
        return f"查询失败: {item_result['error']}"

    # Run advisor
    advisor_result = await advisor_flow.ainvoke({
        "messages": [],
        "market_context": None,
        "item_context": {
            "analysis_result": item_result.get("analysis_result", ""),
            "item_detail": item_result.get("item_detail"),
            "indicators": item_result.get("indicators"),
        },
        "scout_context": None,
        "historical_advice": None,
        "recommendation": None,
        "risk_level": None,
        "requires_confirmation": False,
        "error": None,
    })

    # Format output
    parts = []
    if item_result.get("analysis_result"):
        parts.append(f"📊 分析:\n{item_result['analysis_result']}")
    if advisor_result.get("recommendation"):
        risk = advisor_result.get("risk_level", "unknown")
        parts.append(f"\n💡 建议 (风险: {risk}):\n{advisor_result['recommendation']}")

    return "\n".join(parts) if parts else "未能生成分析结果"


def cli_entry() -> None:
    """Entry point for the `csqaq` CLI command."""
    from csqaq.api.cli import app as typer_app
    typer_app()
