from __future__ import annotations

from typing import TYPE_CHECKING

from .vol_schemas import VolItem

if TYPE_CHECKING:
    from .client import CSQAQClient


class VolAPI:
    """CSQAQ trading volume API endpoint."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def get_vol_data(self) -> list[VolItem]:
        """Get trading volume data. POST /api/v1/info/vol_data_info"""
        data = await self._client.post("/info/vol_data_info", json={})
        if isinstance(data, list):
            return [VolItem.model_validate(item) for item in data]
        return []
