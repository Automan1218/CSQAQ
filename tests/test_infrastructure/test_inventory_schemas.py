import json
from pathlib import Path

import pytest

from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestInventoryStat:
    def test_parse_single(self):
        raw = {"statistic": 29346, "created_at": "2025-06-20T00:00:00"}
        stat = InventoryStat.model_validate(raw)
        assert stat.statistic == 29346
        assert stat.created_at == "2025-06-20T00:00:00"

    def test_parse_fixture(self):
        data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
        stats = [InventoryStat.model_validate(item) for item in data]
        assert len(stats) == 30
        assert all(isinstance(s.statistic, int) for s in stats)
