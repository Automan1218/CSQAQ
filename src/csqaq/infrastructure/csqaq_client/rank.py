from __future__ import annotations

from typing import TYPE_CHECKING

from .rank_schemas import PageListItem, RankItem

if TYPE_CHECKING:
    from .client import CSQAQClient


class RankAPI:
    """CSQAQ ranking and page-list API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def get_rank_list(
        self,
        filter: dict,
        page: int = 1,
        size: int = 20,
        search: str = "",
        show_recently_price: bool = False,
    ) -> list[RankItem]:
        """Get ranking list. POST /api/v1/info/get_rank_list"""
        body: dict = {
            "page_index": page,
            "page_size": size,
            "filter": filter,
            "show_recently_price": show_recently_price,
        }
        if search:
            body["search"] = search
        data = await self._client.post("/info/get_rank_list", json=body)
        items = data.get("data", []) if isinstance(data, dict) else []
        return [RankItem.model_validate(item) for item in items]

    async def get_page_list(
        self,
        page: int = 1,
        size: int = 20,
        search: str = "",
        filter: dict | None = None,
    ) -> list[PageListItem]:
        """Get item page list. POST /api/v1/info/get_page_list"""
        body: dict = {
            "page_index": page,
            "page_size": size,
        }
        if search:
            body["search"] = search
        if filter:
            body["filter"] = filter
        data = await self._client.post("/info/get_page_list", json=body)
        items = data.get("data", []) if isinstance(data, dict) else []
        return [PageListItem.model_validate(item) for item in items]
