# src/csqaq/main.py
"""Application entry point and dependency wiring."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from rich.logging import RichHandler

from csqaq.config import Settings


@dataclass
class RunQueryResult:
    """Structured result returned by run_query."""

    summary: str
    action_detail: str
    risk_level: str
    requires_confirmation: bool

    def full_text(self) -> str:
        return f"{self.summary}\n\n{self.action_detail}"

    def summary_text(self) -> str:
        return self.summary


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
        self._market_api = None
        self._rank_api = None
        self._vol_api = None
        self._model_factory = None
        self._database = None

    async def init(self) -> None:
        from csqaq.components.models.factory import ModelFactory
        from csqaq.infrastructure.csqaq_client.client import CSQAQClient
        from csqaq.infrastructure.csqaq_client.item import ItemAPI
        from csqaq.infrastructure.csqaq_client.market import MarketAPI
        from csqaq.infrastructure.csqaq_client.rank import RankAPI
        from csqaq.infrastructure.csqaq_client.vol import VolAPI
        from csqaq.infrastructure.database.connection import Database

        # CSQAQ Client
        self._csqaq_client = CSQAQClient(
            base_url=self.settings.csqaq_base_url,
            api_token=self.settings.csqaq_api_token,
            rate_limit=self.settings.csqaq_rate_limit,
        )
        self._item_api = ItemAPI(self._csqaq_client)
        self._market_api = MarketAPI(self._csqaq_client)
        self._rank_api = RankAPI(self._csqaq_client)
        self._vol_api = VolAPI(self._csqaq_client)

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
        if self._item_api is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._item_api

    @property
    def market_api(self):
        if self._market_api is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._market_api

    @property
    def rank_api(self):
        if self._rank_api is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._rank_api

    @property
    def vol_api(self):
        if self._vol_api is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._vol_api

    @property
    def model_factory(self):
        if self._model_factory is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._model_factory

    @property
    def database(self):
        if self._database is None:
            raise RuntimeError("App not initialized — call await app.init() first")
        return self._database

    async def close(self) -> None:
        if self._csqaq_client:
            await self._csqaq_client.close()
        if self._database:
            await self._database.close()


async def run_query(app: App, query: str) -> RunQueryResult:
    """Run any query through the router flow, returning a structured result."""
    from csqaq.flows.router_flow import build_router_flow

    router_flow = build_router_flow(
        item_api=app.item_api, market_api=app.market_api,
        rank_api=app.rank_api, vol_api=app.vol_api,
        model_factory=app.model_factory,
    )
    r = await router_flow.ainvoke({
        "messages": [], "query": query, "intent": None,
        "item_name": None, "result": None, "error": None,
        "requires_confirmation": False, "risk_level": None,
        "summary": None, "action_detail": None,
    })
    if r.get("error") and not r.get("summary"):
        error_msg = f"查询失败: {r['error']}"
        return RunQueryResult(
            summary=error_msg,
            action_detail="",
            risk_level="unknown",
            requires_confirmation=False,
        )
    return RunQueryResult(
        summary=r.get("summary") or r.get("result") or "查询完成",
        action_detail=r.get("action_detail") or "",
        risk_level=r.get("risk_level") or "unknown",
        requires_confirmation=r.get("requires_confirmation", False),
    )


def cli_entry() -> None:
    """Entry point for the `csqaq` CLI command."""
    from csqaq.api.cli import app as typer_app
    typer_app()
