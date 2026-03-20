"""Inventory (存世量) data schemas."""
from __future__ import annotations

from pydantic import BaseModel


class InventoryStat(BaseModel):
    """Single day inventory data point from /info/good/statistic endpoint."""

    statistic: int      # 当日存世量
    created_at: str     # ISO datetime, e.g. "2025-06-20T00:00:00"
