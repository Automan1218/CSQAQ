# Inventory Trend Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 90-day inventory trend analysis with a natural-language YAML rule engine to detect whale behavior (吸货/控盘/抛压) in CS2 skin markets.

**Architecture:** Independent Inventory Agent with 3 nodes (fetch → analyze → interpret), integrated as a 4th parallel branch in `parallel_item_flow` and as a standalone `inventory_flow` for dedicated inventory queries. A YAML rule library stores natural-language rules that the LLM interprets against analysis results.

**Tech Stack:** Python 3.11+, Pydantic v2, LangGraph StateGraph, pytest-asyncio, PyYAML

**Spec:** `docs/superpowers/specs/2026-03-20-inventory-trend-analysis-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/csqaq/infrastructure/csqaq_client/inventory_schemas.py` | `InventoryStat` Pydantic model |
| `src/csqaq/components/analysis/inventory_analyzer.py` | `InventoryReport` dataclass, `analyze_inventory()` — pure computation |
| `src/csqaq/components/agents/inventory.py` | 3 node functions: fetch, analyze, interpret |
| `src/csqaq/rules/inventory_rules.yaml` | Natural-language rule library |
| `src/csqaq/rules/__init__.py` | Rule loading utility |
| `src/csqaq/flows/inventory_flow.py` | Standalone inventory query subgraph |
| `tests/fixtures/statistic_response.json` | Fixture: 90-day inventory API response |
| `tests/test_infrastructure/test_inventory_schemas.py` | Schema validation tests |
| `tests/test_components/test_analysis/test_inventory_analyzer.py` | Inventory analysis unit tests |
| `tests/test_components/test_inventory_agent.py` | Inventory agent node tests |
| `tests/test_flows/test_inventory_flow.py` | Standalone inventory flow integration test |

### Modified Files

| File | Change |
|------|--------|
| `src/csqaq/infrastructure/csqaq_client/item.py` | Add `get_item_statistic()` method |
| `src/csqaq/components/analysis/__init__.py` | Export `InventoryReport`, `analyze_inventory` |
| `src/csqaq/components/router.py` | Add `inventory_query` intent + keywords |
| `src/csqaq/components/agents/advisor.py` | Add `inventory_context` to prompt and context builder |
| `src/csqaq/flows/parallel_item_flow.py` | Extract resolve to `prepare_queries`, add inventory branch |
| `src/csqaq/flows/router_flow.py` | Add `inventory_subflow` routing, update `_item_subflow_node` initial state |
| `src/csqaq/main.py` | Wire `inventory_flow` dependencies |
| `tests/conftest.py` | Add `mock_item_api.get_item_statistic` fixture |

---

### Task 1: InventoryStat Schema + ItemAPI Extension

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/inventory_schemas.py`
- Create: `tests/fixtures/statistic_response.json`
- Create: `tests/test_infrastructure/test_inventory_schemas.py`
- Modify: `src/csqaq/infrastructure/csqaq_client/item.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Create test fixture**

Create `tests/fixtures/statistic_response.json` with realistic 90-day inventory data:

```json
[
  {"statistic": 30000, "created_at": "2025-12-21T00:00:00"},
  {"statistic": 29950, "created_at": "2025-12-22T00:00:00"},
  {"statistic": 29900, "created_at": "2025-12-23T00:00:00"},
  {"statistic": 29800, "created_at": "2025-12-24T00:00:00"},
  {"statistic": 29750, "created_at": "2025-12-25T00:00:00"},
  {"statistic": 29700, "created_at": "2025-12-26T00:00:00"},
  {"statistic": 29680, "created_at": "2025-12-27T00:00:00"},
  {"statistic": 29600, "created_at": "2025-12-28T00:00:00"},
  {"statistic": 29500, "created_at": "2025-12-29T00:00:00"},
  {"statistic": 29450, "created_at": "2025-12-30T00:00:00"},
  {"statistic": 29400, "created_at": "2025-12-31T00:00:00"},
  {"statistic": 29350, "created_at": "2026-01-01T00:00:00"},
  {"statistic": 29300, "created_at": "2026-01-02T00:00:00"},
  {"statistic": 29250, "created_at": "2026-01-03T00:00:00"},
  {"statistic": 29200, "created_at": "2026-01-04T00:00:00"},
  {"statistic": 29150, "created_at": "2026-01-05T00:00:00"},
  {"statistic": 29100, "created_at": "2026-01-06T00:00:00"},
  {"statistic": 29000, "created_at": "2026-01-07T00:00:00"},
  {"statistic": 28950, "created_at": "2026-01-08T00:00:00"},
  {"statistic": 28900, "created_at": "2026-01-09T00:00:00"},
  {"statistic": 28850, "created_at": "2026-01-10T00:00:00"},
  {"statistic": 28800, "created_at": "2026-01-11T00:00:00"},
  {"statistic": 28750, "created_at": "2026-01-12T00:00:00"},
  {"statistic": 28700, "created_at": "2026-01-13T00:00:00"},
  {"statistic": 28650, "created_at": "2026-01-14T00:00:00"},
  {"statistic": 28600, "created_at": "2026-01-15T00:00:00"},
  {"statistic": 28500, "created_at": "2026-01-16T00:00:00"},
  {"statistic": 28450, "created_at": "2026-01-17T00:00:00"},
  {"statistic": 28400, "created_at": "2026-01-18T00:00:00"},
  {"statistic": 28300, "created_at": "2026-01-19T00:00:00"}
]
```

This is 30 entries with a steadily decreasing trend (~1100 over 30 days).

- [ ] **Step 2: Write failing tests**

Create `tests/test_infrastructure/test_inventory_schemas.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_infrastructure/test_inventory_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'csqaq.infrastructure.csqaq_client.inventory_schemas'`

- [ ] **Step 4: Implement InventoryStat schema**

Create `src/csqaq/infrastructure/csqaq_client/inventory_schemas.py`:

```python
"""Inventory (存世量) data schemas."""
from __future__ import annotations

from pydantic import BaseModel


class InventoryStat(BaseModel):
    """Single day inventory data point from /info/good/statistic endpoint."""

    statistic: int      # 当日存世量
    created_at: str     # ISO datetime, e.g. "2025-06-20T00:00:00"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_infrastructure/test_inventory_schemas.py -v`
Expected: 2 passed

- [ ] **Step 6: Write failing test for ItemAPI.get_item_statistic**

Add to `tests/test_infrastructure/test_item_endpoints.py`, following existing `respx` pattern (NOT the conftest mock pattern):

```python
@respx.mock
@pytest.mark.asyncio
async def test_get_item_statistic(item_api):
    data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
    respx.get(f"{BASE}/info/good/statistic").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": data})
    )
    stats = await item_api.get_item_statistic(7310)
    assert len(stats) > 0
    from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat
    assert isinstance(stats[0], InventoryStat)
```

Add the `InventoryStat` import at the top of the file.

- [ ] **Step 7: Implement get_item_statistic in ItemAPI**

Add to `src/csqaq/infrastructure/csqaq_client/item.py`:

```python
from .inventory_schemas import InventoryStat
from datetime import datetime, timedelta

async def get_item_statistic(self, good_id: int) -> list[InventoryStat]:
    """Get 90-day inventory trend. GET /info/good/statistic

    Note: This is the only GET method in ItemAPI — all others use POST.
    This matches the external API spec for this endpoint.
    """
    data = await self._client.get("/info/good/statistic", params={"id": str(good_id)})
    if not isinstance(data, list):
        return []
    stats = [InventoryStat.model_validate(item) for item in data]
    # Truncate to last 90 days by date
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    return [s for s in stats if s.created_at >= cutoff]
```

- [ ] **Step 8: Update conftest.py mock_item_api fixture**

Add `get_item_statistic` mock to the existing `mock_item_api` fixture in `tests/conftest.py`:

```python
from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat

# Inside mock_item_api fixture, after existing mocks:
stat_data = json.loads((FIXTURES / "statistic_response.json").read_text(encoding="utf-8"))
api.get_item_statistic.return_value = [InventoryStat.model_validate(s) for s in stat_data]
```

- [ ] **Step 9: Run all tests to verify**

Run: `python -m pytest tests/test_infrastructure/test_inventory_schemas.py tests/test_infrastructure/test_item_endpoints.py -v`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add src/csqaq/infrastructure/csqaq_client/inventory_schemas.py src/csqaq/infrastructure/csqaq_client/item.py tests/fixtures/statistic_response.json tests/test_infrastructure/test_inventory_schemas.py tests/conftest.py
git commit -m "feat: add InventoryStat schema and ItemAPI.get_item_statistic"
```

---

### Task 2: Inventory Analyzer — Pure Computation

**Files:**
- Create: `src/csqaq/components/analysis/inventory_analyzer.py`
- Create: `tests/test_components/test_analysis/test_inventory_analyzer.py`
- Modify: `src/csqaq/components/analysis/__init__.py`

**Context:** This module analyzes inventory time series data using MA, volatility, and momentum from `TechnicalIndicators`. It does NOT use RSI, MACD, or Bollinger Bands (those are price-specific). It also detects inventory-specific signals (acceleration, sudden drop, inflection point). Produces an `InventoryReport` dataclass.

- [ ] **Step 1: Write failing tests**

Create `tests/test_components/test_analysis/test_inventory_analyzer.py`:

```python
import pytest

from csqaq.components.analysis.inventory_analyzer import (
    InventoryReport,
    analyze_inventory,
    detect_acceleration,
    detect_sudden_change,
    detect_inflection,
)
from csqaq.components.analysis.signals import Signal


class TestAnalyzeInventory:
    def test_decreasing_trend(self):
        """Steadily decreasing inventory should report 'decreasing' trend."""
        values = [30000 - i * 50 for i in range(30)]
        report = analyze_inventory(values)
        assert isinstance(report, InventoryReport)
        assert report.trend_direction == "decreasing"
        assert report.velocity < 0  # negative = decreasing
        assert report.summary  # non-empty

    def test_increasing_trend(self):
        values = [20000 + i * 30 for i in range(30)]
        report = analyze_inventory(values)
        assert report.trend_direction == "increasing"
        assert report.velocity > 0

    def test_stable_trend(self):
        values = [25000 + (i % 3 - 1) * 5 for i in range(30)]
        report = analyze_inventory(values)
        assert report.trend_direction == "stable"

    def test_insufficient_data(self):
        report = analyze_inventory([100, 99])
        assert report.trend_direction == "unknown"
        assert "数据不足" in report.summary

    def test_empty_data(self):
        report = analyze_inventory([])
        assert report.trend_direction == "unknown"

    def test_signals_populated(self):
        """Strong decreasing trend should produce signals."""
        values = [30000 - i * 100 for i in range(30)]
        report = analyze_inventory(values)
        assert all(isinstance(s, Signal) for s in report.signals)

    def test_indicators_present(self):
        values = [30000 - i * 50 for i in range(30)]
        report = analyze_inventory(values)
        assert "ma7" in report.indicators
        assert "ma30" in report.indicators or "ma20" in report.indicators
        assert "volatility" in report.indicators
        assert "velocity" in report.indicators


class TestDetectAcceleration:
    def test_accelerating_decrease(self):
        """Inventory decreasing faster in recent period vs earlier."""
        early = [30000 - i * 20 for i in range(15)]
        late = [early[-1] - i * 80 for i in range(1, 16)]
        values = early + late
        signal = detect_acceleration(values)
        assert signal is not None
        assert signal.direction == "bearish"  # accelerating decrease = supply shrinking fast
        assert signal.name == "inventory_acceleration"

    def test_no_acceleration(self):
        values = [30000 - i * 50 for i in range(30)]  # constant rate
        signal = detect_acceleration(values)
        assert signal is None  # no acceleration


class TestDetectSuddenChange:
    def test_sudden_drop(self):
        values = [30000] * 25 + [28000, 27000, 26000, 25500, 25000]
        signal = detect_sudden_change(values)
        assert signal is not None
        assert signal.name == "inventory_sudden_change"

    def test_no_sudden_change(self):
        values = [30000 - i * 50 for i in range(30)]
        signal = detect_sudden_change(values)
        assert signal is None


class TestDetectInflection:
    def test_inflection_decrease_to_increase(self):
        decreasing = [30000 - i * 100 for i in range(15)]
        increasing = [decreasing[-1] + i * 80 for i in range(1, 16)]
        values = decreasing + increasing
        signal = detect_inflection(values)
        assert signal is not None
        assert signal.name == "inventory_inflection"

    def test_no_inflection(self):
        values = [30000 - i * 50 for i in range(30)]
        signal = detect_inflection(values)
        assert signal is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components/test_analysis/test_inventory_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement inventory_analyzer.py**

Create `src/csqaq/components/analysis/inventory_analyzer.py`:

Key elements:
- `InventoryReport` dataclass: `signals: list[Signal]`, `indicators: dict`, `trend_direction: str` ("increasing"|"decreasing"|"stable"|"unknown"), `velocity: float` (units/day), `summary: str`
- `analyze_inventory(values: list[int]) -> InventoryReport`: Main function. Computes MA7, MA30 (or MA20 if < 30 points), volatility, velocity (linear slope of recent 7 days). Trend direction from velocity thresholds. Runs 3 signal detectors. Builds Chinese summary.
- `detect_acceleration(values) -> Signal | None`: Compare velocity of first half vs second half. If ratio > 2x, signal "accelerating" change.
- `detect_sudden_change(values) -> Signal | None`: If any single-day change exceeds 3× the average daily change, flag it.
- `detect_inflection(values) -> Signal | None`: Compare MA direction of first half vs second half. If opposite directions, flag trend reversal.

All detectors return `Signal` dataclass instances (reusing from `signals.py`). Minimum data requirement: 5 data points for basic analysis, fewer returns `trend_direction="unknown"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components/test_analysis/test_inventory_analyzer.py -v`
Expected: All pass

- [ ] **Step 5: Update __init__.py exports**

Add to `src/csqaq/components/analysis/__init__.py`:

```python
from csqaq.components.analysis.inventory_analyzer import InventoryReport, analyze_inventory
```

And update `__all__` to include them.

- [ ] **Step 6: Run full analysis test suite**

Run: `python -m pytest tests/test_components/test_analysis/ -v`
Expected: All pass (existing + new)

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/components/analysis/inventory_analyzer.py src/csqaq/components/analysis/__init__.py tests/test_components/test_analysis/test_inventory_analyzer.py
git commit -m "feat: add inventory trend analyzer with signal detectors"
```

---

### Task 3: YAML Rule Library + Loader

**Files:**
- Create: `src/csqaq/rules/__init__.py`
- Create: `src/csqaq/rules/inventory_rules.yaml`

- [ ] **Step 1: Write failing test**

Add to a new section at the bottom of `tests/test_components/test_analysis/test_inventory_analyzer.py` (or create `tests/test_components/test_rules.py`):

```python
from csqaq.rules import load_inventory_rules


class TestRuleLoader:
    def test_load_rules(self):
        rules = load_inventory_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 4  # initial rule set has 4 rules
        assert all("name" in r and "description" in r for r in rules)

    def test_rules_have_required_fields(self):
        rules = load_inventory_rules()
        for rule in rules:
            assert isinstance(rule["name"], str)
            assert isinstance(rule["description"], str)
            assert len(rule["description"]) > 10  # meaningful descriptions

    def test_rules_format_as_prompt(self):
        """Rules should be formattable into a prompt string."""
        rules = load_inventory_rules()
        prompt_text = "\n".join(f"- {r['name']}: {r['description']}" for r in rules)
        assert "吸货" in prompt_text
        assert "控盘" in prompt_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_components/test_rules.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create YAML rule file**

Create `src/csqaq/rules/inventory_rules.yaml`:

```yaml
rules:
  - name: 盘主吸货
    description: >
      存世量持续减少（近30天下降超过3%），但价格保持稳定或微涨（涨幅不超过5%）。
      这种模式说明有大资金在持续买入吸筹，看多信号。建议关注后续价格突破。

  - name: 控盘风险
    description: >
      存世量持续减少且价格快速上涨（涨幅超过10%），说明该饰品已被庄家控盘。
      此时追高风险极大，T+7冷却期内价格可能被砸盘。高风险信号。

  - name: 抛压信号
    description: >
      存世量持续增加，同时价格下跌。可能是大量开箱导致供给增加，
      或者持有者集中抛售。看空信号，建议回避或减仓。

  - name: 异常扫货
    description: >
      存世量在短时间内（1-3天）出现大幅突降（单日降幅超过日均变化的3倍），
      说明有大单集中扫货。需密切关注后续价格变动，可能是拉升前兆。
```

- [ ] **Step 4: Create rule loader**

Create `src/csqaq/rules/__init__.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_components/test_rules.py -v`
Expected: All pass

- [ ] **Step 6: Verify PyYAML is available**

Run: `python -c "import yaml; print(yaml.__version__)"`
If not installed: `pip install pyyaml`

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/rules/__init__.py src/csqaq/rules/inventory_rules.yaml tests/test_components/test_rules.py
git commit -m "feat: add YAML inventory rule library with loader"
```

---

### Task 4: Inventory Agent — 3 Node Functions

**Files:**
- Create: `src/csqaq/components/agents/inventory.py`
- Create: `tests/test_components/test_inventory_agent.py`

**Context:** Three node functions following the same pattern as `item.py` and `market.py` agents. Each takes `state: dict` + injected dependencies via `*` keyword args.

- [ ] **Step 1: Write failing tests**

Create `tests/test_components/test_inventory_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from csqaq.components.agents.inventory import (
    fetch_inventory_node,
    analyze_inventory_node,
    interpret_inventory_node,
)
from csqaq.infrastructure.csqaq_client.inventory_schemas import InventoryStat


def _make_stats(count: int = 30, start: int = 30000, delta: int = -50) -> list[InventoryStat]:
    """Generate test inventory stats."""
    return [
        InventoryStat(statistic=start + i * delta, created_at=f"2026-01-{i+1:02d}T00:00:00")
        for i in range(count)
    ]


class TestFetchInventoryNode:
    @pytest.mark.asyncio
    async def test_success(self):
        item_api = AsyncMock()
        stats = _make_stats()
        item_api.get_item_statistic.return_value = stats

        state = {"good_id": 7310, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)

        assert "inventory_stats" in result
        assert len(result["inventory_stats"]) == 30
        item_api.get_item_statistic.assert_called_once_with(7310)

    @pytest.mark.asyncio
    async def test_skip_on_error(self):
        item_api = AsyncMock()
        state = {"good_id": 7310, "error": "previous error"}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result == {}
        item_api.get_item_statistic.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_good_id(self):
        item_api = AsyncMock()
        state = {"good_id": None, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result == {}

    @pytest.mark.asyncio
    async def test_api_failure(self):
        item_api = AsyncMock()
        item_api.get_item_statistic.side_effect = Exception("API error")
        state = {"good_id": 7310, "error": None}
        result = await fetch_inventory_node(state, item_api=item_api)
        assert result.get("inventory_stats") is None


class TestAnalyzeInventoryNode:
    def test_produces_report(self):
        # analyze_inventory_node is sync (pure computation)
        state = {
            "inventory_stats": [{"statistic": 30000 - i * 50, "created_at": f"2026-01-{i+1:02d}T00:00:00"} for i in range(30)],
        }
        result = analyze_inventory_node(state)
        assert "inventory_report" in result
        assert result["inventory_report"]["trend_direction"] == "decreasing"

    def test_skip_without_stats(self):
        state = {"inventory_stats": None}
        result = analyze_inventory_node(state)
        assert result == {}


class TestInterpretInventoryNode:
    @pytest.mark.asyncio
    async def test_produces_context(self):
        model_factory = MagicMock()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="存世量持续下降，疑似有盘主在吸货。")
        model_factory.create.return_value = mock_llm

        state = {
            "inventory_report": {
                "trend_direction": "decreasing",
                "velocity": -50.0,
                "signals": [],
                "indicators": {"ma7": 28500},
                "summary": "存世量下降",
            },
            "item_context": {"item_detail": {"name": "AK-47 红线"}},
        }
        result = await interpret_inventory_node(state, model_factory=model_factory)

        assert "inventory_context" in result
        assert isinstance(result["inventory_context"], str)
        model_factory.create.assert_called_once_with("analyst")

    @pytest.mark.asyncio
    async def test_skip_without_report(self):
        model_factory = MagicMock()
        state = {"inventory_report": None}
        result = await interpret_inventory_node(state, model_factory=model_factory)
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components/test_inventory_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement inventory agent**

Create `src/csqaq/components/agents/inventory.py`:

Key elements:
- `fetch_inventory_node(state, *, item_api)` — Calls `item_api.get_item_statistic(good_id)`. Returns `{"inventory_stats": [stat.model_dump() for stat in stats]}`. Skips if `state["error"]` or no `good_id`. Catches exceptions gracefully.
- `analyze_inventory_node(state)` — Sync node (no LLM). Extracts int values via `values = [s["statistic"] for s in state["inventory_stats"]]`, calls `analyze_inventory(values)`, returns `{"inventory_report": asdict(report)}`. Skips if no stats.
- `interpret_inventory_node(state, *, model_factory)` — LLM node. Loads YAML rules via `load_inventory_rules()`. Builds system prompt with rules + inventory report + item_context (if available). Uses `model_factory.create("analyst")`. Returns `{"inventory_context": response.content}`.

System prompt for interpret node:

```
你是 CS2 饰品存世量分析专家。根据以下规则库和分析数据，判断当前饰品的存世量趋势含义。

## 规则库
{rules_text}

## 分析数据
{inventory_report}

## 价格参考（如果有）
{item_context}

请根据数据判断哪些规则适用，给出你的解读。如果没有规则匹配，给出你基于数据的独立判断。使用中文回答。
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components/test_inventory_agent.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/agents/inventory.py tests/test_components/test_inventory_agent.py
git commit -m "feat: add Inventory Agent with fetch/analyze/interpret nodes"
```

---

### Task 5: Router — Add inventory_query Intent

**Files:**
- Modify: `src/csqaq/components/router.py`
- Modify: `tests/test_components/test_router.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_components/test_router.py`:

```python
class TestInventoryIntent:
    def test_keyword_inventory(self):
        result = classify_intent_by_keywords("AK47红线的存世量趋势")
        assert result is not None
        assert result.intent == "inventory_query"

    def test_keyword_absorption(self):
        result = classify_intent_by_keywords("有没有人在吸货")
        assert result is not None
        assert result.intent == "inventory_query"

    def test_keyword_control(self):
        result = classify_intent_by_keywords("这个饰品有控盘嫌疑吗")
        assert result is not None
        assert result.intent == "inventory_query"

    @pytest.mark.asyncio
    async def test_llm_inventory_intent(self):
        model_factory = MagicMock()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"intent": "inventory_query", "item_name": "AK-47 红线"}'
        )
        model_factory.create.return_value = mock_llm

        result = await classify_intent_by_llm("AK47红线的存世量变化怎么样", model_factory)
        assert result.intent == "inventory_query"
        assert result.item_name == "AK-47 红线"
```

**Note:** Add `classify_intent_by_llm` to the import line at the top of `test_router.py` (currently only `classify_intent_by_keywords` is imported).
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components/test_router.py::TestInventoryIntent -v`
Expected: FAIL — "inventory_query" not in keyword rules

- [ ] **Step 3: Implement router changes**

Modify `src/csqaq/components/router.py`:

1. Add inventory keywords to `_KEYWORD_RULES`:
   ```python
   ("inventory_query", ["存世量", "库存趋势", "吸货", "控盘", "持有量", "存量"]),
   ```
   Place BEFORE `scout_query` so inventory keywords take priority.

2. Update `IntentResult` docstring: `"item_query" | "market_query" | "scout_query" | "inventory_query"`

3. Update `ROUTER_SYSTEM_PROMPT` to include fourth intent:
   ```
   - inventory_query: 询问某个饰品的存世量趋势、是否有人吸货/控盘
   ```

4. Update validation in `classify_intent_by_llm`:
   ```python
   if intent not in ("item_query", "market_query", "scout_query", "inventory_query"):
       intent = "item_query"
   ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components/test_router.py -v`
Expected: All pass (old + new)

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/router.py tests/test_components/test_router.py
git commit -m "feat: add inventory_query intent to router"
```

---

### Task 6: Advisor — Add inventory_context Support

**Files:**
- Modify: `src/csqaq/components/agents/advisor.py`
- Modify: `tests/test_components/test_advisor_output.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_components/test_advisor_output.py`:

```python
@pytest.mark.asyncio
async def test_advisor_with_inventory_context():
    """Advisor should include inventory_context when present."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "存世量下降，疑似吸货", "action_detail": "建议小额建仓", "risk_level": "medium"}'
    )
    model_factory.create.return_value = mock_llm

    state = {
        "item_context": {"analysis_result": "价格稳定"},
        "market_context": None,
        "scout_context": None,
        "inventory_context": "存世量近30天持续下降约5%，符合盘主吸货模式。",
    }

    result = await advise_node(state, model_factory=model_factory)
    assert result["summary"] == "存世量下降，疑似吸货"

    # Verify inventory context was included in the LLM prompt
    call_args = mock_llm.ainvoke.call_args[0][0]
    user_msg = call_args[1]["content"]
    assert "存世量" in user_msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_components/test_advisor_output.py::test_advisor_with_inventory_context -v`
Expected: FAIL — inventory_context not included in prompt

- [ ] **Step 3: Implement advisor changes**

Modify `src/csqaq/components/agents/advisor.py`:

1. Add `inventory_context` to `ADVISOR_SYSTEM_PROMPT`:
   ```
   - inventory_context: 存世量趋势分析（库存变化趋势、庄家行为判断等）
   ```

2. Add to `advise_node` context construction (after scout_context block):
   ```python
   if state.get("inventory_context"):
       context_parts.append(f"## 存世量分析\n{state['inventory_context']}")
   ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components/test_advisor_output.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/components/agents/advisor.py tests/test_components/test_advisor_output.py
git commit -m "feat: add inventory_context support to Advisor"
```

---

### Task 7: Refactor parallel_item_flow — Extract resolve_item to prepare_queries

**Files:**
- Modify: `src/csqaq/flows/parallel_item_flow.py`
- Modify: `tests/test_flows/test_parallel_item_flow.py`

**Context:** This is the most complex change. `prepare_queries` becomes async and calls `search_suggest` + `get_item_detail` to resolve `good_id` and `item_detail` before the parallel fork. `_run_item_branch` no longer calls `resolve_item_node` — it reads `good_id` and `item_detail` from its input.

- [ ] **Step 1: Write test for new prepare_queries behavior**

Add to `tests/test_flows/test_parallel_item_flow.py`:

```python
@pytest.mark.asyncio
async def test_prepare_queries_resolves_good_id(mock_item_api):
    """prepare_queries should resolve good_name to good_id via search_suggest."""
    from csqaq.flows.parallel_item_flow import prepare_queries

    state = {"good_name": "AK-47 红线", "query": "AK-47 红线", "good_id": None, "item_detail": None}
    result = await prepare_queries(state, item_api=mock_item_api)

    assert result["good_id"] is not None
    assert result["item_detail"] is not None
    mock_item_api.search_suggest.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flows/test_parallel_item_flow.py::test_prepare_queries_resolves_good_id -v`
Expected: FAIL — `prepare_queries` is sync, doesn't take `item_api`, doesn't return `good_id`

- [ ] **Step 3: Refactor parallel_item_flow.py**

Key changes to `src/csqaq/flows/parallel_item_flow.py`:

1. Add `good_id: int | None`, `item_detail: dict | None`, `inventory_context: str | None` (str, not dict — LLM text output), `inventory_error: str | None` to `ParallelItemFlowState`

2. Refactor `prepare_queries` to async, accept `item_api`:
   ```python
   async def prepare_queries(state: ParallelItemFlowState, *, item_api: ItemAPI) -> dict:
       good_name = state.get("good_name") or state.get("query")
       good_id = state.get("good_id")
       item_detail = state.get("item_detail")

       if good_id is None and good_name:
           results = await item_api.search_suggest(good_name)
           if results:
               good_id = results[0].good_id

       if good_id is not None and item_detail is None:
           detail = await item_api.get_item_detail(good_id)
           item_detail = detail.model_dump()

       return {"good_name": good_name, "good_id": good_id, "item_detail": item_detail}
   ```

3. Refactor `_run_item_branch` to accept `good_id: int` and `item_detail: dict` instead of `good_name`, skip `resolve_item_node`:
   ```python
   async def _run_item_branch(good_id: int, item_detail: dict, *, item_api: ItemAPI, model_factory: ModelFactory) -> dict:
       item_state = {
           "good_id": good_id, "item_detail": item_detail,
           "chart_data": None, "kline_data": None, "indicators": None,
           "ta_report": None, "analysis_result": None, "error": None,
       }
       # Step 1: fetch_chart (no more resolve)
       chart_result = await fetch_chart_node(item_state, item_api=item_api)
       item_state.update(chart_result)
       # Step 2: analyze
       analyze_result = await analyze_node(item_state, model_factory=model_factory)
       item_state.update(analyze_result)
       ...
   ```

4. Update `run_parallel` to read `good_id` and `item_detail` from state, with guard for `good_id=None`:
   ```python
   good_id = state.get("good_id")
   item_detail = state.get("item_detail")

   # Guard: if resolve failed, item branch returns error instead of crashing
   if good_id is not None:
       item_task = _run_item_branch(good_id, item_detail, item_api=item_api, model_factory=model_factory)
   else:
       async def _noop_item():
           return {"item_error": "饰品解析失败，无法获取数据", "item_context": None}
       item_task = _noop_item()
   ```

5. Update `build_parallel_item_flow` to bind `item_api` to `prepare_queries` via `partial`

- [ ] **Step 4: Update existing tests**

Update `tests/test_flows/test_parallel_item_flow.py` initial state dicts to include `good_id: None` and `item_detail: None` and `inventory_context: None`, `inventory_error: None`.

- [ ] **Step 5: Run tests to verify**

Run: `python -m pytest tests/test_flows/test_parallel_item_flow.py -v`
Expected: All pass

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest -v`
Expected: All pass (no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/csqaq/flows/parallel_item_flow.py tests/test_flows/test_parallel_item_flow.py
git commit -m "refactor: extract resolve_item to prepare_queries, add good_id to shared state"
```

---

### Task 8: Inventory Branch in parallel_item_flow

**Files:**
- Modify: `src/csqaq/flows/parallel_item_flow.py`
- Modify: `tests/test_flows/test_parallel_item_flow.py`

**Context:** Add `_run_inventory_branch` as 4th parallel branch in `run_parallel`. Uses `good_id` from shared state, calls inventory agent nodes sequentially.

- [ ] **Step 1: Write failing test**

Add to `tests/test_flows/test_parallel_item_flow.py`:

```python
@pytest.mark.asyncio
async def test_parallel_flow_includes_inventory(
    mock_item_api, mock_market_api, mock_rank_api, mock_vol_api,
):
    """Parallel flow should produce inventory_context."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "综合分析含存世量", "action_detail": "建议观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_parallel_item_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [], "query": "AK-47 红线", "good_name": "AK-47 红线",
        "good_id": None, "item_detail": None,
        "item_context": None, "market_context": None,
        "scout_context": None, "inventory_context": None,
        "item_error": None, "market_error": None,
        "scout_error": None, "inventory_error": None,
        "risk_level": None, "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    assert result.get("inventory_context") is not None or result.get("inventory_error") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flows/test_parallel_item_flow.py::test_parallel_flow_includes_inventory -v`
Expected: FAIL — no inventory branch yet

- [ ] **Step 3: Implement inventory branch**

Add to `src/csqaq/flows/parallel_item_flow.py`:

1. Import inventory agent nodes:
   ```python
   from csqaq.components.agents.inventory import (
       fetch_inventory_node, analyze_inventory_node, interpret_inventory_node,
   )
   ```

2. Add `_run_inventory_branch`:
   ```python
   async def _run_inventory_branch(
       good_id: int, item_context: dict | None,
       *, item_api: ItemAPI, model_factory: ModelFactory,
   ) -> dict:
       inv_state = {"good_id": good_id, "error": None, "inventory_stats": None,
                     "inventory_report": None, "item_context": item_context}
       fetch_result = await fetch_inventory_node(inv_state, item_api=item_api)
       inv_state.update(fetch_result)
       if inv_state.get("inventory_stats"):
           analyze_result = analyze_inventory_node(inv_state)
           inv_state.update(analyze_result)
       if inv_state.get("inventory_report"):
           interpret_result = await interpret_inventory_node(inv_state, model_factory=model_factory)
           inv_state.update(interpret_result)
       return {
           "inventory_context": inv_state.get("inventory_context"),
           "inventory_error": None,
       }
   ```

3. Update `run_parallel` to add inventory task to `asyncio.gather`:
   ```python
   good_id = state.get("good_id")
   # ... existing 3 tasks ...
   if good_id is not None:
       inventory_task = _run_inventory_branch(good_id, None, item_api=item_api, model_factory=model_factory)
   else:
       async def _noop_inventory():
           return {"inventory_context": None, "inventory_error": "no good_id"}
       inventory_task = _noop_inventory()
   # Note: do NOT use asyncio.coroutine — it was removed in Python 3.11
   results = await asyncio.gather(item_task, market_task, scout_task, inventory_task, return_exceptions=True)
   ```

4. Update merged dict and loop to handle 4th result.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flows/test_parallel_item_flow.py -v`
Expected: All pass

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/csqaq/flows/parallel_item_flow.py tests/test_flows/test_parallel_item_flow.py
git commit -m "feat: add inventory branch to parallel_item_flow"
```

---

### Task 9: Standalone inventory_flow Subgraph

**Files:**
- Create: `src/csqaq/flows/inventory_flow.py`
- Create: `tests/test_flows/test_inventory_flow.py`

**Context:** Standalone subgraph for `inventory_query` intent: resolve_item → fetch_inventory → analyze_inventory → interpret_inventory → advisor → END. Note: the spec mentions a separate `fetch_item_detail` step, but `resolve_item_node` already fetches `item_detail` internally (via `get_item_detail`), so we consolidate them into a single node.

- [ ] **Step 1: Write failing test**

Create `tests/test_flows/test_inventory_flow.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from csqaq.flows.inventory_flow import build_inventory_flow


@pytest.mark.asyncio
async def test_inventory_flow_end_to_end(mock_item_api):
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "存世量下降，关注吸货", "action_detail": "小额建仓", "risk_level": "medium"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_inventory_flow(item_api=mock_item_api, model_factory=model_factory)
    result = await flow.ainvoke({
        "messages": [], "query": "AK-47 红线存世量",
        "good_name": "AK-47 红线",
        "good_id": None, "item_detail": None,
        "inventory_stats": None, "inventory_report": None,
        "inventory_context": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False,
        "error": None,
    })

    assert result.get("summary") is not None
    assert result.get("inventory_context") is not None or result.get("error") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flows/test_inventory_flow.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement inventory_flow.py**

Create `src/csqaq/flows/inventory_flow.py`:

```python
"""Inventory analysis LangGraph subgraph.

Graph: resolve_item → fetch_inventory → analyze_inventory → interpret_inventory → prepare_advisor → advise → END
"""
```

Key elements:
- `InventoryFlowState` TypedDict with relevant fields
- Reuse `resolve_item_node` from item agent
- Use inventory agent's 3 nodes
- `_prepare_advisor_context`: packs `inventory_context` for advisor
- `advise_node` from advisor agent
- `build_inventory_flow(item_api, model_factory)` function

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flows/test_inventory_flow.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/flows/inventory_flow.py tests/test_flows/test_inventory_flow.py
git commit -m "feat: add standalone inventory_flow subgraph"
```

---

### Task 10: Router Flow — Wire inventory_subflow

**Files:**
- Modify: `src/csqaq/flows/router_flow.py`
- Modify: `tests/test_flows/test_router_flow.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_flows/test_router_flow.py`:

```python
from langchain_core.messages import AIMessage

@pytest.mark.asyncio
async def test_router_dispatches_inventory_query(
    mock_item_api, mock_market_api, mock_rank_api, mock_vol_api,
):
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    # Router returns inventory_query intent; follow existing pattern using AIMessage
    mock_llm.ainvoke.side_effect = [
        AIMessage(content='{"intent": "inventory_query", "item_name": "AK-47 红线"}'),
        # Subsequent calls for analyst/advisor
        AIMessage(content="存世量分析结果"),
        AIMessage(content='{"summary": "存世量下降", "action_detail": "观望", "risk_level": "low"}'),
    ]
    model_factory.create.return_value = mock_llm

    flow = build_router_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [], "query": "AK-47红线的存世量趋势",
        "intent": None, "item_name": None, "result": None, "error": None,
        "requires_confirmation": False, "risk_level": None,
        "summary": None, "action_detail": None,
    })

    assert result.get("intent") == "inventory_query"
    assert result.get("summary") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flows/test_router_flow.py::test_router_dispatches_inventory_query -v`
Expected: FAIL — no `inventory_subflow` node

- [ ] **Step 3: Implement router_flow changes**

Modify `src/csqaq/flows/router_flow.py`:

1. Add `_inventory_subflow_node` (similar to `_market_subflow_node`):
   ```python
   async def _inventory_subflow_node(state, *, item_api, model_factory):
       from csqaq.flows.inventory_flow import build_inventory_flow
       flow = build_inventory_flow(item_api=item_api, model_factory=model_factory)
       r = await flow.ainvoke({...initial state from router state...})
       return {
           "result": ..., "summary": r.get("summary"),
           "action_detail": r.get("action_detail"),
           "risk_level": r.get("risk_level"),
           "requires_confirmation": r.get("requires_confirmation", False),
       }
   ```

2. Update `_dispatch` to handle `inventory_query`:
   ```python
   elif intent == "inventory_query":
       return "inventory_subflow"
   ```

3. Add node and edges in `build_router_flow`:
   ```python
   graph.add_node("inventory_subflow", partial(_inventory_subflow_node, item_api=item_api, model_factory=model_factory))
   ```
   Update conditional edges map and add `graph.add_edge("inventory_subflow", END)`.

4. Update `_item_subflow_node` initial state dict to include new fields: `good_id: None`, `inventory_context: None`, `inventory_error: None`, `item_detail: None`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_flows/test_router_flow.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/flows/router_flow.py tests/test_flows/test_router_flow.py
git commit -m "feat: wire inventory_subflow into router flow"
```

---

### Task 11: Update main.py + E2E Tests

**Files:**
- Modify: `src/csqaq/main.py`
- Modify: `tests/test_e2e.py`

- [ ] **Step 1: Update main.py run_query**

The `run_query` function in `main.py` calls `build_router_flow()` — since router_flow was already updated in Task 10, `run_query` should work for inventory queries automatically. Verify the initial state dict passed to `router_flow.ainvoke()` doesn't need new fields (it shouldn't — router flow state doesn't include inventory-specific fields).

- [ ] **Step 2: Update E2E test**

Add to `tests/test_e2e.py`:

```python
@pytest.mark.asyncio
async def test_full_inventory_pipeline(mock_item_api):
    """Complete inventory pipeline: resolve -> fetch inventory -> analyze -> interpret -> advise."""
    factory = ModelFactory()
    mock_analyst = AsyncMock()
    mock_analyst.ainvoke.return_value = AIMessage(content="存世量持续下降，疑似吸货行为")
    mock_advisor = AsyncMock()
    mock_advisor.ainvoke.return_value = AIMessage(
        content='{"summary": "存世量下降，符合吸货模式", "action_detail": "可小额建仓试探", "risk_level": "medium"}'
    )

    def mock_create(role):
        if role == "advisor":
            return mock_advisor
        return mock_analyst

    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    factory.create = mock_create

    from csqaq.flows.inventory_flow import build_inventory_flow
    flow = build_inventory_flow(item_api=mock_item_api, model_factory=factory)
    result = await flow.ainvoke({
        "messages": [], "query": "AK红线存世量趋势",
        "good_name": "AK红线",
        "good_id": None, "item_detail": None,
        "inventory_stats": None, "inventory_report": None,
        "inventory_context": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False,
        "error": None,
    })

    assert result.get("summary") is not None
    assert result.get("risk_level") == "medium"
    assert result.get("inventory_context") is not None
```

Also add the `build_inventory_flow` import at the top of the file.

- [ ] **Step 3: Run E2E tests**

Run: `python -m pytest tests/test_e2e.py -v`
Expected: All pass

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest -v`
Expected: All pass, no regressions

- [ ] **Step 5: Commit**

```bash
git add src/csqaq/main.py tests/test_e2e.py
git commit -m "test: add E2E test for inventory query flow"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run complete test suite**

Run: `python -m pytest -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Verify test count increased**

Starting from 141 tests (Phase 3 end), expect ~165+ tests total.

- [ ] **Step 3: Verify no import cycles**

Run: `python -c "from csqaq.flows.inventory_flow import build_inventory_flow; print('OK')"`
Run: `python -c "from csqaq.rules import load_inventory_rules; print('OK')"`

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -A && git commit -m "chore: final cleanup for inventory trend analysis"
```
