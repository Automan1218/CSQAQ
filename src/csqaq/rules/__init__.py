"""Rule library loader."""
from __future__ import annotations

from pathlib import Path

import yaml


_RULES_DIR = Path(__file__).parent


def load_inventory_rules() -> list[dict]:
    """Load inventory rules from YAML file."""
    path = _RULES_DIR / "inventory_rules.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])
