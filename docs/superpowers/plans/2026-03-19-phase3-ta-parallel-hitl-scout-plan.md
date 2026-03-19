# Phase 3: 技术分析 · 并行子图 · HITL · Scout 全维度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring stock-market technical analysis methods to CS2 skin investment, add parallel context gathering, HITL safety gate, and multi-dimension Scout scanning.

**Architecture:** Independent `components/analysis/` module for TA (indicators → signals → report). Parallel item flow uses `asyncio.gather` to fork item/market/scout branches. HITL is CLI-layer gating on flow output. Scout extends existing `cross_filter_ranks` to N-list variadic.

**Tech Stack:** Python 3.13, LangGraph, Pydantic v2, httpx, pytest-asyncio, respx

**Spec:** `docs/superpowers/specs/2026-03-19-phase3-ta-parallel-hitl-scout-design.md`

**Domain constraint:** CS2 skins are T+7 (7-day trade hold). Hourly signals get 0.4× strength multiplier. Volume-price divergence is highest-weight signal.

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `src/csqaq/components/analysis/__init__.py` | Module exports: `TechnicalIndicators`, `Signal`, `TAReport`, `analyze_kline`, `analyze_index_kline` |
| `src/csqaq/components/analysis/indicators.py` | Pure math: SMA, EMA, RSI, MACD, Bollinger, + migrated methods |
| `src/csqaq/components/analysis/signals.py` | `Signal` dataclass + 5 detection functions |
| `src/csqaq/components/analysis/analyzer.py` | `TAReport` dataclass + `analyze_kline()` / `analyze_index_kline()` entry points |
| `src/csqaq/infrastructure/csqaq_client/rank_filters.py` | `RANK_FILTERS` dict constant |
| `src/csqaq/flows/parallel_item_flow.py` | `ParallelItemFlowState` + `build_parallel_item_flow()` |
| `tests/test_components/test_analysis/__init__.py` | Package init |
| `tests/test_components/test_analysis/test_indicators.py` | Unit tests for all indicator functions |
| `tests/test_components/test_analysis/test_signals.py` | Unit tests for signal detection |
| `tests/test_components/test_analysis/test_analyzer.py` | Integration tests for TAReport generation |
| `tests/test_components/test_scout_multi_dimension.py` | Tests for variadic `cross_filter_ranks` |
| `tests/test_flows/test_parallel_item_flow.py` | Parallel flow integration tests |
| `tests/test_flows/test_hitl_gate.py` | HITL gate behavior tests |
| `tests/fixtures/index_kline_response.json` | Index K-line fixture data |

### Modified files

| File | Change |
|------|--------|
| `src/csqaq/infrastructure/csqaq_client/market_schemas.py` | Add `IndexKlineBar` model |
| `src/csqaq/infrastructure/csqaq_client/market.py` | Add `get_index_kline()` method |
| `src/csqaq/infrastructure/csqaq_client/__init__.py` | Export `IndexKlineBar` |
| `src/csqaq/infrastructure/analysis/indicators.py` | Re-export shim |
| `src/csqaq/components/agents/advisor.py` | Two-part output (summary + action_detail) |
| `src/csqaq/components/agents/market.py` | Integrate TA for index kline |
| `src/csqaq/components/agents/item.py` | Integrate TA for item kline |
| `src/csqaq/components/agents/scout.py` | Multi-dimension fetch + variadic cross_filter |
| `src/csqaq/flows/item_flow.py` | Add `summary`/`action_detail` to state |
| `src/csqaq/flows/market_flow.py` | Add `summary`/`action_detail` to state |
| `src/csqaq/flows/scout_flow.py` | Add `summary`/`action_detail` to state |
| `src/csqaq/flows/router_flow.py` | Route item_query to parallel_item_flow, update output formatting |
| `src/csqaq/main.py` | Wire new dependencies |
| `src/csqaq/api/cli.py` | HITL confirmation prompt |
| `tests/conftest.py` | Add `mock_market_api.get_index_kline` fixture |
| `docs/PROBLEMS.md` | Correct inventory ranking info |
| `docs/TODO.md` | Update Phase 3 status |

---

### Task 1: Indicators — migrate + add EMA

**Files:**
- Create: `src/csqaq/components/analysis/__init__.py`
- Create: `src/csqaq/components/analysis/indicators.py`
- Create: `tests/test_components/test_analysis/__init__.py`
- Create: `tests/test_components/test_analysis/test_indicators.py`
- Modify: `src/csqaq/infrastructure/analysis/indicators.py`

- [ ] **Step 1: Write failing tests for migrated methods + EMA**

```python
# tests/test_components/test_analysis/test_indicators.py
from csqaq.components.analysis.indicators import TechnicalIndicators


class TestMovingAverage:
    def test_basic(self):
        prices = [10, 20, 30, 40, 50]
        result = TechnicalIndicators.moving_average(prices, window=3)
        assert result == [None, None, 20.0, 30.0, 40.0]

    def test_window_larger_than_data(self):
        result = TechnicalIndicators.moving_average([1, 2], window=5)
        assert result == [None, None]


class TestEMA:
    def test_basic(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        result = TechnicalIndicators.exponential_moving_average(prices, window=3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] is not None  # first EMA at index window-1
        # EMA should be between min and max of window
        for v in result[2:]:
            assert 10.0 <= v <= 16.0

    def test_window_larger_than_data(self):
        result = TechnicalIndicators.exponential_moving_average([1.0, 2.0], window=5)
        assert all(v is None for v in result)


class TestVolatility:
    def test_basic(self):
        prices = [100.0, 102.0, 98.0, 101.0, 99.0]
        vol = TechnicalIndicators.volatility(prices, window=5)
        assert vol > 0

    def test_single_value(self):
        assert TechnicalIndicators.volatility([100.0], window=5) == 0.0


class TestPriceMomentum:
    def test_basic(self):
        prices = [100.0, 105.0, 110.0]
        assert TechnicalIndicators.price_momentum(prices, period=2) == 10.0


class TestPlatformSpread:
    def test_basic(self):
        spread = TechnicalIndicators.platform_spread(110.0, 100.0)
        assert spread == 10.0

    def test_zero_denominator(self):
        assert TechnicalIndicators.platform_spread(50.0, 0) == 0.0


class TestVolumeTrend:
    def test_increasing(self):
        vols = [100, 100, 100, 200, 200, 200]
        assert TechnicalIndicators.volume_trend(vols, window=3) == "increasing"

    def test_stable(self):
        vols = [100, 100, 100, 105, 100, 95]
        assert TechnicalIndicators.volume_trend(vols, window=3) == "stable"
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_indicators.py -v --tb=short
```

- [ ] **Step 3: Create analysis module with indicators**

Create `src/csqaq/components/analysis/__init__.py` (empty for now).

Create `src/csqaq/components/analysis/indicators.py`:
- Copy all 5 existing methods from `src/csqaq/infrastructure/analysis/indicators.py`
- Add `exponential_moving_average(prices, window, smoothing=2)` static method
- EMA formula: `multiplier = smoothing / (window + 1)`, first EMA = SMA of first `window` values, then `EMA = price * multiplier + prev_EMA * (1 - multiplier)`

- [ ] **Step 4: Convert old indicators.py to re-export shim**

Replace contents of `src/csqaq/infrastructure/analysis/indicators.py` with:
```python
from csqaq.components.analysis.indicators import TechnicalIndicators

__all__ = ["TechnicalIndicators"]
```

- [ ] **Step 5: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_indicators.py -v --tb=short
```

- [ ] **Step 6: Run full test suite to verify no regressions**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

All 83 existing tests must still pass.

- [ ] **Step 7: Commit**

```
git add src/csqaq/components/analysis/__init__.py src/csqaq/components/analysis/indicators.py src/csqaq/infrastructure/analysis/indicators.py tests/test_components/test_analysis/__init__.py tests/test_components/test_analysis/test_indicators.py
git commit -m "feat: migrate TechnicalIndicators to components/analysis, add EMA"
```

---

### Task 2: Indicators — add RSI, MACD, Bollinger Bands

**Files:**
- Modify: `src/csqaq/components/analysis/indicators.py`
- Modify: `tests/test_components/test_analysis/test_indicators.py`

- [ ] **Step 1: Write failing tests for RSI, MACD, Bollinger**

Append to `tests/test_components/test_analysis/test_indicators.py`:

```python
class TestRSI:
    def test_basic_uptrend(self):
        # Steadily rising prices → RSI should be high (>50)
        prices = [float(i) for i in range(20)]  # 0,1,2,...,19
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert 90 <= rsi <= 100  # pure uptrend

    def test_basic_downtrend(self):
        prices = [float(20 - i) for i in range(20)]  # 20,19,...,1
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert 0 <= rsi <= 10  # pure downtrend

    def test_insufficient_data(self):
        prices = [10.0, 11.0, 10.5]
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert rsi == 50.0  # default neutral


class TestMACD:
    def test_returns_named_tuple(self):
        # 40 data points for MACD(12,26,9)
        prices = [100.0 + i * 0.5 for i in range(40)]
        result = TechnicalIndicators.macd(prices)
        assert hasattr(result, "macd_line")
        assert hasattr(result, "signal_line")
        assert hasattr(result, "histogram")

    def test_uptrend_positive_macd(self):
        prices = [100.0 + i * 1.0 for i in range(40)]
        result = TechnicalIndicators.macd(prices)
        assert result.macd_line > 0  # uptrend → positive MACD

    def test_insufficient_data(self):
        prices = [10.0, 11.0]
        result = TechnicalIndicators.macd(prices)
        assert result.macd_line == 0.0


class TestBollingerBands:
    def test_returns_named_tuple(self):
        prices = [100.0 + (i % 5) for i in range(25)]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert hasattr(result, "upper")
        assert hasattr(result, "middle")
        assert hasattr(result, "lower")

    def test_band_ordering(self):
        prices = [100.0 + (i % 5) for i in range(25)]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert result.lower < result.middle < result.upper

    def test_insufficient_data(self):
        prices = [10.0, 11.0]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert result.upper == 0.0
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_indicators.py -v --tb=short
```

- [ ] **Step 3: Implement RSI, MACD, Bollinger**

Add to `TechnicalIndicators` class in `src/csqaq/components/analysis/indicators.py`:

- `rsi(prices, period=14)` → float. Calculate average gain/loss over period. If insufficient data return 50.0 (neutral).
- `macd(prices, fast=12, slow=26, signal=9)` → `MACDResult(macd_line, signal_line, histogram)`. Use EMA internally. If insufficient data return all zeros.
- `bollinger_bands(prices, window=20, num_std=2)` → `BollingerResult(upper, middle, lower)`. Middle = SMA, upper/lower = middle ± num_std * stdev. If insufficient data return all zeros.

Define `MACDResult` and `BollingerResult` as `NamedTuple` at module level.

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_indicators.py -v --tb=short
```

- [ ] **Step 5: Commit**

```
git add src/csqaq/components/analysis/indicators.py tests/test_components/test_analysis/test_indicators.py
git commit -m "feat: add RSI, MACD, Bollinger Bands to indicators"
```

---

### Task 3: Signal detection module

**Files:**
- Create: `src/csqaq/components/analysis/signals.py`
- Create: `tests/test_components/test_analysis/test_signals.py`

- [ ] **Step 1: Write failing tests for all 5 signal detectors**

```python
# tests/test_components/test_analysis/test_signals.py
from csqaq.components.analysis.signals import (
    Signal,
    detect_bollinger_breakout,
    detect_ma_crossover,
    detect_macd_crossover,
    detect_rsi_extreme,
    detect_volume_price_divergence,
)


class TestMACrossover:
    def test_golden_cross(self):
        # Prices that cause MA5 to cross above MA20
        # 20 flat values then 5 rising values
        prices = [100.0] * 20 + [110.0, 115.0, 120.0, 125.0, 130.0]
        sig = detect_ma_crossover(prices, short=5, long=20)
        assert sig is not None
        assert sig.direction == "bullish"
        assert sig.name == "ma_crossover"

    def test_death_cross(self):
        prices = [100.0] * 20 + [90.0, 85.0, 80.0, 75.0, 70.0]
        sig = detect_ma_crossover(prices, short=5, long=20)
        assert sig is not None
        assert sig.direction == "bearish"

    def test_no_cross(self):
        prices = [100.0] * 25
        sig = detect_ma_crossover(prices, short=5, long=20)
        assert sig is None or sig.direction == "neutral"

    def test_insufficient_data(self):
        sig = detect_ma_crossover([10.0, 11.0], short=5, long=20)
        assert sig is None


class TestRSIExtreme:
    def test_overbought(self):
        prices = [float(i) for i in range(20)]  # pure uptrend
        sig = detect_rsi_extreme(prices, period=14)
        assert sig is not None
        assert sig.direction == "bearish"  # overbought = bearish signal

    def test_oversold(self):
        prices = [float(20 - i) for i in range(20)]  # pure downtrend
        sig = detect_rsi_extreme(prices, period=14)
        assert sig is not None
        assert sig.direction == "bullish"  # oversold = bullish signal

    def test_neutral(self):
        # Oscillating prices → RSI near 50
        prices = [100.0, 101.0, 100.0, 101.0, 100.0] * 4
        sig = detect_rsi_extreme(prices, period=14)
        assert sig is None  # no extreme


class TestMACDCrossover:
    def test_bullish_crossover(self):
        # Shift from downtrend to uptrend
        prices = [100.0 - i * 0.5 for i in range(20)] + [80.0 + i * 1.5 for i in range(20)]
        sig = detect_macd_crossover(prices)
        assert sig is not None
        assert sig.direction == "bullish"

    def test_insufficient_data(self):
        sig = detect_macd_crossover([10.0, 11.0])
        assert sig is None


class TestBollingerBreakout:
    def test_upper_breakout(self):
        # Stable then sudden spike
        prices = [100.0] * 20 + [100.0, 100.0, 100.0, 100.0, 120.0]
        sig = detect_bollinger_breakout(prices)
        assert sig is not None
        assert sig.direction == "bearish"  # above upper band = overbought

    def test_insufficient_data(self):
        sig = detect_bollinger_breakout([10.0, 11.0])
        assert sig is None


class TestVolumePriceDivergence:
    def test_price_up_volume_down(self):
        prices = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0]
        volumes = [1000, 950, 900, 850, 800, 750, 700, 650, 600, 550]
        sig = detect_volume_price_divergence(prices, volumes)
        assert sig is not None
        assert sig.direction == "bearish"  # price up but volume down = weak rally

    def test_price_down_volume_up(self):
        prices = [118.0, 116.0, 114.0, 112.0, 110.0, 108.0, 106.0, 104.0, 102.0, 100.0]
        volumes = [550, 600, 650, 700, 750, 800, 850, 900, 950, 1000]
        sig = detect_volume_price_divergence(prices, volumes)
        assert sig is not None
        assert sig.direction == "bullish"  # price down but volume up = accumulation

    def test_insufficient_data(self):
        sig = detect_volume_price_divergence([10.0], [100])
        assert sig is None
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_signals.py -v --tb=short
```

- [ ] **Step 3: Implement signals.py**

Create `src/csqaq/components/analysis/signals.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from csqaq.components.analysis.indicators import TechnicalIndicators


@dataclass
class Signal:
    name: str           # e.g. "ma_crossover"
    direction: str      # "bullish" | "bearish" | "neutral"
    strength: float     # 0.0 ~ 1.0
    description: str    # Chinese description


def detect_ma_crossover(prices: list[float], short: int = 5, long: int = 20) -> Signal | None:
    """Detect MA golden/death cross. Returns None if insufficient data."""
    ...

def detect_rsi_extreme(prices: list[float], period: int = 14) -> Signal | None:
    """Detect RSI > 70 (overbought/bearish) or < 30 (oversold/bullish)."""
    ...

def detect_macd_crossover(prices: list[float]) -> Signal | None:
    """Detect MACD line crossing signal line."""
    ...

def detect_bollinger_breakout(prices: list[float]) -> Signal | None:
    """Detect price breaking above upper or below lower Bollinger band."""
    ...

def detect_volume_price_divergence(prices: list[float], volumes: list[int]) -> Signal | None:
    """Detect divergence between price trend and volume trend."""
    ...
```

Each function:
1. Check minimum data length, return None if insufficient
2. Call `TechnicalIndicators` methods
3. Evaluate condition
4. Return `Signal(name, direction, strength, description)` or None

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_signals.py -v --tb=short
```

- [ ] **Step 5: Commit**

```
git add src/csqaq/components/analysis/signals.py tests/test_components/test_analysis/test_signals.py
git commit -m "feat: add signal detection module with 5 detectors"
```

---

### Task 4: TA Analyzer (TAReport)

**Files:**
- Create: `src/csqaq/components/analysis/analyzer.py`
- Create: `tests/test_components/test_analysis/test_analyzer.py`
- Modify: `src/csqaq/components/analysis/__init__.py`

- [ ] **Step 1: Write failing tests for analyzer**

```python
# tests/test_components/test_analysis/test_analyzer.py
from csqaq.components.analysis.analyzer import TAReport, analyze_kline
from csqaq.infrastructure.csqaq_client.schemas import KlineBar


def _make_bars(closes: list[float], volume: int = 100) -> list[KlineBar]:
    """Helper: build KlineBar list from close prices."""
    bars = []
    for i, c in enumerate(closes):
        bars.append(KlineBar(
            timestamp=1700000000 + i * 86400,
            open=c - 0.5, close=c, high=c + 1.0, low=c - 1.0, volume=volume,
        ))
    return bars


class TestAnalyzeKline:
    def test_uptrend_report(self):
        closes = [100.0 + i * 1.0 for i in range(40)]
        bars = _make_bars(closes)
        report = analyze_kline(bars, period="1day")
        assert isinstance(report, TAReport)
        assert report.overall_direction in ("bullish", "bearish", "neutral")
        assert len(report.signals) > 0
        assert "ma5" in report.indicators or "rsi" in report.indicators
        assert report.summary  # non-empty

    def test_insufficient_data(self):
        bars = _make_bars([100.0, 101.0, 102.0])
        report = analyze_kline(bars, period="1day")
        assert report.overall_direction == "neutral"
        assert "数据不足" in report.summary

    def test_hourly_strength_penalty(self):
        closes = [100.0 + i * 1.0 for i in range(40)]
        bars = _make_bars(closes)
        daily_report = analyze_kline(bars, period="1day")
        hourly_report = analyze_kline(bars, period="1hour")
        # Hourly signals should have lower strength
        if hourly_report.signals and daily_report.signals:
            max_hourly = max(s.strength for s in hourly_report.signals)
            max_daily = max(s.strength for s in daily_report.signals)
            assert max_hourly <= max_daily
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_analyzer.py -v --tb=short
```

- [ ] **Step 3: Implement analyzer.py**

Create `src/csqaq/components/analysis/analyzer.py`:

- `TAReport` dataclass: `signals: list[Signal]`, `indicators: dict`, `overall_direction: str`, `summary: str`
- `analyze_kline(bars: list[KlineBar], period: str = "1day") -> TAReport`:
  1. Extract `closes` and `volumes` from bars
  2. Run all 5 signal detectors, collect non-None signals
  3. If `period` starts with "1hour" or "4hour", multiply each signal's strength by 0.4
  4. Compute `overall_direction` via weighted vote: `sum(bullish_strengths)` vs `sum(bearish_strengths)`, diff < 0.1 = neutral
  5. Build `indicators` dict with all raw values (ma5, ma20, rsi, macd, bollinger, etc.)
  6. Generate `summary` string
  7. If fewer than 2 signals, prepend "数据不足，部分指标未生效" to summary
- `analyze_index_kline(bars, period)` → same but skip volume_price_divergence

Update `src/csqaq/components/analysis/__init__.py` to export everything.

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_analysis/test_analyzer.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/analysis/analyzer.py src/csqaq/components/analysis/__init__.py tests/test_components/test_analysis/test_analyzer.py
git commit -m "feat: add TA analyzer with TAReport and weighted signal voting"
```

---

### Task 5: IndexKlineBar schema + MarketAPI.get_index_kline()

**Files:**
- Modify: `src/csqaq/infrastructure/csqaq_client/market_schemas.py`
- Modify: `src/csqaq/infrastructure/csqaq_client/market.py`
- Create: `tests/fixtures/index_kline_response.json`
- Modify: `tests/conftest.py`
- Modify: existing market schema tests

- [ ] **Step 1: Write failing test for IndexKlineBar and get_index_kline**

```python
# tests/test_infrastructure/test_index_kline.py
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.infrastructure.csqaq_client.market_schemas import IndexKlineBar


class TestIndexKlineBar:
    def test_parse(self):
        data = {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0}
        bar = IndexKlineBar.model_validate(data)
        assert bar.o == 1402.74
        assert bar.c == 1385.55
        assert bar.v == 0
        assert bar.timestamp_int == 1700150400000  # validator converts t to int

    def test_parse_list(self):
        data = [
            {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0},
            {"t": "1700236800000", "o": 1385.55, "c": 1374.73, "h": 1386.72, "l": 1374.73, "v": 0},
        ]
        bars = [IndexKlineBar.model_validate(d) for d in data]
        assert len(bars) == 2
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_infrastructure/test_index_kline.py -v --tb=short
```

- [ ] **Step 3: Create fixture file + implement schema + API method**

Create `tests/fixtures/index_kline_response.json`:
```json
[
  {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0},
  {"t": "1700236800000", "o": 1385.55, "c": 1374.73, "h": 1386.72, "l": 1374.73, "v": 0},
  {"t": "1700323200000", "o": 1374.73, "c": 1370.56, "h": 1377.00, "l": 1369.76, "v": 0},
  {"t": "1700409600000", "o": 1370.56, "c": 1370.81, "h": 1373.53, "l": 1369.27, "v": 0},
  {"t": "1700496000000", "o": 1370.81, "c": 1373.98, "h": 1374.20, "l": 1370.81, "v": 0}
]
```

Add to `src/csqaq/infrastructure/csqaq_client/market_schemas.py`:
```python
class IndexKlineBar(BaseModel):
    t: str
    o: float
    c: float
    h: float
    l: float
    v: int

    @property
    def timestamp_int(self) -> int:
        return int(self.t)
```

Add to `src/csqaq/infrastructure/csqaq_client/market.py`:
```python
from .market_schemas import HomeData, IndexKlineBar, SubData

async def get_index_kline(self, sub_id: int = 1, period: str = "1day") -> list[IndexKlineBar]:
    """GET /api/v1/sub/kline"""
    data = await self._client.get("/sub/kline", params={"id": str(sub_id), "type": period})
    if isinstance(data, list):
        return [IndexKlineBar.model_validate(bar) for bar in data]
    return []
```

Add mock to `tests/conftest.py` in `mock_market_api` fixture:
```python
index_kline = json.loads((FIXTURES / "index_kline_response.json").read_text(encoding="utf-8"))
api.get_index_kline.return_value = [IndexKlineBar.model_validate(k) for k in index_kline]
```

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_infrastructure/test_index_kline.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/infrastructure/csqaq_client/market_schemas.py src/csqaq/infrastructure/csqaq_client/market.py tests/fixtures/index_kline_response.json tests/test_infrastructure/test_index_kline.py tests/conftest.py
git commit -m "feat: add IndexKlineBar schema and MarketAPI.get_index_kline()"
```

---

### Task 6: Rank filter constants

**Files:**
- Create: `src/csqaq/infrastructure/csqaq_client/rank_filters.py`

- [ ] **Step 1: Create rank_filters.py with constants**

```python
# src/csqaq/infrastructure/csqaq_client/rank_filters.py
"""Rank list filter presets for the CSQAQ ranking API."""

RANK_FILTERS: dict[str, dict] = {
    "price_up_7d": {"排序": ["价格_价格上升(百分比)_近7天"]},
    "price_down_7d": {"排序": ["价格_价格下降(百分比)_近7天"]},
    "volume": {"排序": ["成交量_Steam日成交量"]},
    "stock_asc": {"排序": ["存世量_存世量_升序"]},
    "sell_decrease_7d": {"排序": ["在售数量_数量减少_近7天"]},
    "buy_increase_7d": {"排序": ["求购数量_数量增多_近7天"]},
    "market_cap_desc": {"排序": ["饰品总市值_总市值降序"]},
}
```

No test needed — it's a constant dict. But verify import works:

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -c "from csqaq.infrastructure.csqaq_client.rank_filters import RANK_FILTERS; print(len(RANK_FILTERS))"
```

Expected: `7`

- [ ] **Step 2: Commit**

```
git add src/csqaq/infrastructure/csqaq_client/rank_filters.py
git commit -m "feat: add RANK_FILTERS constants for Scout multi-dimension"
```

---

### Task 7: Scout multi-dimension cross_filter_ranks

**Files:**
- Modify: `src/csqaq/components/agents/scout.py`
- Create: `tests/test_components/test_scout_multi_dimension.py`

- [ ] **Step 1: Write failing tests for variadic cross_filter_ranks**

```python
# tests/test_components/test_scout_multi_dimension.py
from csqaq.components.agents.scout import cross_filter_ranks


class TestCrossFilterRanksVariadic:
    def test_two_lists_overlap(self):
        price_ids = [1, 2, 3, 4, 5]
        vol_ids = [3, 4, 5, 6, 7]
        result = cross_filter_ranks(price_ids, vol_ids, min_overlap=2)
        assert 3 in result
        assert 4 in result
        assert 5 in result

    def test_three_lists_overlap(self):
        list_a = [1, 2, 3, 4, 5]
        list_b = [3, 4, 5, 6, 7]
        list_c = [4, 5, 8, 9, 10]
        result = cross_filter_ranks(list_a, list_b, list_c, min_overlap=3)
        assert 4 in result
        assert 5 in result
        assert 3 not in result  # only in 2 lists

    def test_min_overlap_2_with_backfill(self):
        list_a = [1, 2, 3]
        list_b = [4, 5, 6]
        # No overlap at min_overlap=2, should backfill from first list
        result = cross_filter_ranks(list_a, list_b, min_overlap=2)
        assert len(result) >= 5  # backfill ensures at least 5

    def test_single_list(self):
        result = cross_filter_ranks([1, 2, 3, 4, 5], min_overlap=1)
        assert result == [1, 2, 3, 4, 5]

    def test_empty_lists(self):
        result = cross_filter_ranks([], [], min_overlap=2)
        assert result == []
```

- [ ] **Step 2: Run tests — expect FAIL** (old signature doesn't accept variadic)

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_scout_multi_dimension.py -v --tb=short
```

- [ ] **Step 3: Update cross_filter_ranks to variadic signature**

In `src/csqaq/components/agents/scout.py`, change:

```python
# OLD
def cross_filter_ranks(price_ids: list[int], vol_ids: list[int], top_n=10, min_overlap=2):

# NEW
def cross_filter_ranks(*id_lists: list[int], top_n: int = 10, min_overlap: int = 2) -> list[int]:
    counter: Counter[int] = Counter()
    for id_list in id_lists:
        counter.update(id_list)

    filtered = [gid for gid, count in counter.most_common() if count >= min_overlap]

    if len(filtered) < 5 and id_lists:
        seen = set(filtered)
        for gid in id_lists[0]:
            if gid not in seen:
                filtered.append(gid)
                seen.add(gid)
            if len(filtered) >= top_n:
                break

    return filtered[:top_n]
```

Also update the caller in `analyze_opportunities_node` (line 86):
```python
# OLD
top_ids = cross_filter_ranks(price_ids, vol_ids)
# NEW (same positional args, still works)
top_ids = cross_filter_ranks(price_ids, vol_ids)
```

No change needed for the caller — positional args work with `*id_lists`.

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_scout_multi_dimension.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/agents/scout.py tests/test_components/test_scout_multi_dimension.py
git commit -m "feat: upgrade cross_filter_ranks to variadic N-list signature"
```

---

### Task 8: Scout multi-dimension fetch

**Files:**
- Modify: `src/csqaq/components/agents/scout.py`

- [ ] **Step 1: Write failing test for multi-dimension fetch**

```python
# Append to tests/test_components/test_scout_multi_dimension.py
import pytest
from unittest.mock import AsyncMock
from csqaq.components.agents.scout import fetch_rank_data_node


@pytest.mark.asyncio
async def test_fetch_multi_dimension():
    rank_api = AsyncMock()
    vol_api = AsyncMock()

    # Mock rank_api to return items with id field for each filter call
    rank_api.get_rank_list.return_value = [
        type("Item", (), {"id": i, "model_dump": lambda self=None, i=i: {"id": i}})()
        for i in range(1, 6)
    ]
    vol_api.get_vol_data.return_value = [
        type("Vol", (), {"good_id": i, "model_dump": lambda self=None, i=i: {"good_id": i}})()
        for i in range(3, 8)
    ]

    result = await fetch_rank_data_node({}, rank_api=rank_api, vol_api=vol_api)
    rank_data = result["rank_data"]

    # Should have multiple dimension keys
    assert "price_change" in rank_data
    assert "volume" in rank_data
    assert "stock" in rank_data
    assert "sell_decrease" in rank_data
    assert "buy_increase" in rank_data
    assert "market_cap" in rank_data

    # rank_api.get_rank_list should be called multiple times (once per filter)
    assert rank_api.get_rank_list.call_count >= 5
```

- [ ] **Step 2: Run test — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_scout_multi_dimension.py::test_fetch_multi_dimension -v --tb=short
```

- [ ] **Step 3: Update fetch_rank_data_node to fetch all dimensions**

In `src/csqaq/components/agents/scout.py`, update `fetch_rank_data_node`:

```python
import asyncio
from csqaq.infrastructure.csqaq_client.rank_filters import RANK_FILTERS

async def fetch_rank_data_node(state: dict, *, rank_api: RankAPI, vol_api: VolAPI) -> dict:
    try:
        # Fetch all rank dimensions in parallel
        price_task = rank_api.get_rank_list(filter=RANK_FILTERS["price_up_7d"], page=1, size=50)
        stock_task = rank_api.get_rank_list(filter=RANK_FILTERS["stock_asc"], page=1, size=50)
        sell_task = rank_api.get_rank_list(filter=RANK_FILTERS["sell_decrease_7d"], page=1, size=50)
        buy_task = rank_api.get_rank_list(filter=RANK_FILTERS["buy_increase_7d"], page=1, size=50)
        cap_task = rank_api.get_rank_list(filter=RANK_FILTERS["market_cap_desc"], page=1, size=50)
        vol_task = vol_api.get_vol_data()

        price_items, stock_items, sell_items, buy_items, cap_items, vol_items = await asyncio.gather(
            price_task, stock_task, sell_task, buy_task, cap_task, vol_task,
        )

        return {
            "rank_data": {
                "price_change": [item.model_dump() for item in price_items],
                "volume": [item.model_dump() for item in vol_items],
                "stock": [item.model_dump() for item in stock_items],
                "sell_decrease": [item.model_dump() for item in sell_items],
                "buy_increase": [item.model_dump() for item in buy_items],
                "market_cap": [item.model_dump() for item in cap_items],
            }
        }
    except Exception as e:
        logger.error("fetch_rank_data_node failed: %s", e)
        return {"error": f"获取排行数据失败: {e}"}
```

Also update `analyze_opportunities_node` to use all dimensions:

```python
# Extract IDs from all dimensions
price_ids = [item["id"] for item in rank_data.get("price_change", [])]
vol_ids = [item["good_id"] for item in rank_data.get("volume", [])]
stock_ids = [item["id"] for item in rank_data.get("stock", [])]
sell_ids = [item["id"] for item in rank_data.get("sell_decrease", [])]
buy_ids = [item["id"] for item in rank_data.get("buy_increase", [])]
cap_ids = [item["id"] for item in rank_data.get("market_cap", [])]
top_ids = cross_filter_ranks(price_ids, vol_ids, stock_ids, sell_ids, buy_ids, cap_ids)
```

Update the data collection section to merge all dimension maps.

- [ ] **Step 4: Run test — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_scout_multi_dimension.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/agents/scout.py tests/test_components/test_scout_multi_dimension.py
git commit -m "feat: Scout fetches 6 ranking dimensions with asyncio.gather"
```

---

### Task 9: Advisor two-part output (summary + action_detail)

**Files:**
- Modify: `src/csqaq/components/agents/advisor.py`
- Modify: `src/csqaq/flows/item_flow.py`
- Modify: `src/csqaq/flows/market_flow.py`
- Modify: `src/csqaq/flows/scout_flow.py`

- [ ] **Step 1: Write failing test for new Advisor output**

```python
# tests/test_components/test_advisor_output.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from csqaq.components.agents.advisor import advise_node


@pytest.mark.asyncio
async def test_advisor_returns_summary_and_action_detail():
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "大盘偏弱", "action_detail": "建议减仓50%", "risk_level": "high"}'
    )
    model_factory.create.return_value = mock_llm

    state = {"item_context": {"analysis_result": "test data"}}
    result = await advise_node(state, model_factory=model_factory)

    assert "summary" in result
    assert "action_detail" in result
    assert result["risk_level"] == "high"
    assert result["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_advisor_empty_context():
    model_factory = MagicMock()
    result = await advise_node({}, model_factory=model_factory)
    assert "summary" in result
    assert result["risk_level"] == "low"
```

- [ ] **Step 2: Run test — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_advisor_output.py -v --tb=short
```

- [ ] **Step 3: Update advisor.py**

In `src/csqaq/components/agents/advisor.py`:
1. Update `ADVISOR_SYSTEM_PROMPT` to ask for `{"summary": ..., "action_detail": ..., "risk_level": ...}` JSON format
2. Update the return dict to use `summary` + `action_detail` instead of `recommendation`
3. For empty context, return `{"summary": "数据不足...", "action_detail": "", "risk_level": "low", ...}`

Update flow state TypedDicts in item_flow.py, market_flow.py, scout_flow.py:
- Add `summary: str | None` and `action_detail: str | None` fields
- Remove `recommendation` field references

Update router_flow.py output formatting (lines 64-69, 86-91, 109-114) to use `summary` + `action_detail` instead of `recommendation`.

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_advisor_output.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/agents/advisor.py src/csqaq/flows/item_flow.py src/csqaq/flows/market_flow.py src/csqaq/flows/scout_flow.py src/csqaq/flows/router_flow.py tests/test_components/test_advisor_output.py
git commit -m "refactor: Advisor output to summary + action_detail, deprecate recommendation"
```

---

### Task 10: Integrate TA into Item Agent

**Files:**
- Modify: `src/csqaq/components/agents/item.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_components/test_item_ta.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from csqaq.components.agents.item import fetch_chart_node


@pytest.mark.asyncio
async def test_fetch_chart_includes_ta_report(mock_item_api):
    state = {"good_id": 123, "error": None}
    result = await fetch_chart_node(state, item_api=mock_item_api)
    assert "ta_report" in result
    ta = result["ta_report"]
    assert "signals" in ta
    assert "overall_direction" in ta
    assert "indicators" in ta
```

- [ ] **Step 2: Run test — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_item_ta.py -v --tb=short
```

- [ ] **Step 3: Update fetch_chart_node to include TA**

In `src/csqaq/components/agents/item.py`, update `fetch_chart_node`:
1. After fetching chart data, also call `item_api.get_item_kline(good_id)`
2. If kline data available, call `analyze_kline(kline_bars, period="30d")`
3. Add `ta_report` to return dict (serialized as dict via `dataclasses.asdict`)

Update `ItemFlowState` in `src/csqaq/flows/item_flow.py` to include `ta_report: dict | None`.

Update `_prepare_advisor_context` in item_flow.py to include `ta_report` in `item_context`.

- [ ] **Step 4: Run test — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_item_ta.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/agents/item.py src/csqaq/flows/item_flow.py tests/test_components/test_item_ta.py
git commit -m "feat: integrate TA report into Item Agent fetch_chart_node"
```

---

### Task 11: Integrate TA into Market Agent

**Files:**
- Modify: `src/csqaq/components/agents/market.py`
- Modify: `src/csqaq/flows/market_flow.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_components/test_market_ta.py
import pytest
from unittest.mock import AsyncMock
from csqaq.components.agents.market import fetch_market_data_node


@pytest.mark.asyncio
async def test_fetch_market_includes_index_kline_ta(mock_market_api):
    state = {}
    result = await fetch_market_data_node(state, market_api=mock_market_api)
    assert "index_ta_report" in result
    ta = result["index_ta_report"]
    assert "overall_direction" in ta
```

- [ ] **Step 2: Run test — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_market_ta.py -v --tb=short
```

- [ ] **Step 3: Update fetch_market_data_node**

In `src/csqaq/components/agents/market.py`:
1. Import `analyze_index_kline` from `csqaq.components.analysis.analyzer`
2. In `fetch_market_data_node`, after fetching home_data and sub_data, also call `market_api.get_index_kline()`
3. Run `analyze_index_kline(bars, period="1day")`
4. Add `index_ta_report` to return dict

Update `MarketFlowState` to include `index_ta_report: dict | None`.

Update `_prepare_advisor_context` in market_flow.py to include `index_ta_report` in `market_context`.

- [ ] **Step 4: Run test — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_components/test_market_ta.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/components/agents/market.py src/csqaq/flows/market_flow.py tests/test_components/test_market_ta.py
git commit -m "feat: integrate index K-line TA into Market Agent"
```

---

### Task 12: Parallel Item Flow

**Files:**
- Create: `src/csqaq/flows/parallel_item_flow.py`
- Create: `tests/test_flows/test_parallel_item_flow.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_flows/test_parallel_item_flow.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from csqaq.flows.parallel_item_flow import build_parallel_item_flow


@pytest.mark.asyncio
async def test_parallel_flow_merges_contexts(
    mock_item_api, mock_market_api, mock_rank_api, mock_vol_api,
):
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "综合分析", "action_detail": "建议观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    flow = build_parallel_item_flow(
        item_api=mock_item_api,
        market_api=mock_market_api,
        rank_api=mock_rank_api,
        vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [],
        "query": "AK-47 红线",
        "good_name": "AK-47 红线",
        "item_context": None, "market_context": None, "scout_context": None,
        "item_error": None, "market_error": None, "scout_error": None,
        "recommendation": None, "risk_level": None,
        "requires_confirmation": False,
        "summary": None, "action_detail": None,
    })

    # At least one context should be populated
    has_context = (
        result.get("item_context") is not None
        or result.get("market_context") is not None
        or result.get("scout_context") is not None
    )
    assert has_context
    assert result.get("summary") is not None


@pytest.mark.asyncio
async def test_parallel_flow_error_isolation(mock_item_api, mock_market_api, mock_rank_api, mock_vol_api):
    """If one branch fails, others should still produce results."""
    model_factory = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"summary": "部分数据可用", "action_detail": "观望", "risk_level": "low"}'
    )
    model_factory.create.return_value = mock_llm

    # Make market fail
    mock_market_api.get_home_data.side_effect = Exception("API down")

    flow = build_parallel_item_flow(
        item_api=mock_item_api, market_api=mock_market_api,
        rank_api=mock_rank_api, vol_api=mock_vol_api,
        model_factory=model_factory,
    )

    result = await flow.ainvoke({
        "messages": [], "query": "test", "good_name": "test",
        "item_context": None, "market_context": None, "scout_context": None,
        "item_error": None, "market_error": None, "scout_error": None,
        "recommendation": None, "risk_level": None,
        "requires_confirmation": False, "summary": None, "action_detail": None,
    })

    # Market failed but item should still work
    assert result.get("market_error") is not None or result.get("market_context") is None
    assert result.get("summary") is not None  # Advisor still runs
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_flows/test_parallel_item_flow.py -v --tb=short
```

- [ ] **Step 3: Implement parallel_item_flow.py**

Create `src/csqaq/flows/parallel_item_flow.py`:
- `ParallelItemFlowState` TypedDict (as in spec Section 3.3)
- `prepare_queries(state)` — pass-through, extracts good_name
- `run_parallel(state, *, item_flow, market_flow, scout_flow)` — `asyncio.gather` with `return_exceptions=True`
- `merge_contexts(state)` — pack non-None contexts into advisor format
- `build_parallel_item_flow(item_api, market_api, rank_api, vol_api, model_factory)`:
  - Build and compile the three sub-flows
  - Graph: `prepare_queries → run_parallel → merge_contexts → advise → END`

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_flows/test_parallel_item_flow.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/flows/parallel_item_flow.py tests/test_flows/test_parallel_item_flow.py
git commit -m "feat: add parallel_item_flow with asyncio.gather fork-join"
```

---

### Task 13: Wire Router to parallel_item_flow

**Files:**
- Modify: `src/csqaq/flows/router_flow.py`
- Modify: `src/csqaq/main.py`

- [ ] **Step 1: Update router_flow.py**

In `src/csqaq/flows/router_flow.py`:
1. Replace `_item_subflow_node` implementation to use `build_parallel_item_flow` instead of `build_item_flow`
2. Update output formatting to use `summary` + `action_detail` instead of `recommendation` for all three subflows
3. Update `build_router_flow` signature to accept `rank_api` and `vol_api` for the parallel flow

The `_item_subflow_node` changes:
```python
async def _item_subflow_node(
    state: RouterFlowState,
    *, item_api, market_api, rank_api, vol_api, model_factory,
) -> dict:
    from csqaq.flows.parallel_item_flow import build_parallel_item_flow
    flow = build_parallel_item_flow(
        item_api=item_api, market_api=market_api,
        rank_api=rank_api, vol_api=vol_api, model_factory=model_factory,
    )
    r = await flow.ainvoke({...})
    # Format output using summary + action_detail
```

- [ ] **Step 2: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 3: Commit**

```
git add src/csqaq/flows/router_flow.py src/csqaq/main.py
git commit -m "feat: wire Router to parallel_item_flow for item_query intent"
```

---

### Task 14: HITL CLI gate

**Files:**
- Modify: `src/csqaq/api/cli.py`
- Modify: `src/csqaq/main.py`
- Create: `tests/test_flows/test_hitl_gate.py`

- [ ] **Step 1: Write failing test for HITL behavior**

```python
# tests/test_flows/test_hitl_gate.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from csqaq.main import run_query, RunQueryResult


class TestRunQueryResult:
    def test_low_risk_no_confirmation(self):
        r = RunQueryResult(
            summary="大盘平稳", action_detail="可以建仓",
            risk_level="low", requires_confirmation=False,
        )
        assert r.requires_confirmation is False
        assert r.full_text() == "大盘平稳\n\n可以建仓"

    def test_high_risk_needs_confirmation(self):
        r = RunQueryResult(
            summary="大盘暴跌", action_detail="建议清仓",
            risk_level="high", requires_confirmation=True,
        )
        assert r.requires_confirmation is True
        assert r.summary_text() == "大盘暴跌"
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_flows/test_hitl_gate.py -v --tb=short
```

- [ ] **Step 3: Implement RunQueryResult and CLI gate**

In `src/csqaq/main.py`:
- Add `RunQueryResult` dataclass: `summary, action_detail, risk_level, requires_confirmation`
- Methods: `full_text()`, `summary_text()`
- Change `run_query()` to return `RunQueryResult` instead of `str`

In `src/csqaq/api/cli.py`:
- Update `_single_query` and `_interactive_mode` to handle `RunQueryResult`
- If `result.requires_confirmation`:
  1. Print summary + `[⚠ HIGH RISK]` warning
  2. Prompt: "输入'继续'查看操作建议，其他任意键取消"
  3. If confirmed, print action_detail
  4. Else print "已取消，建议观望"

- [ ] **Step 4: Run tests — expect PASS**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/test_flows/test_hitl_gate.py -v --tb=short
```

- [ ] **Step 5: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```
git add src/csqaq/main.py src/csqaq/api/cli.py tests/test_flows/test_hitl_gate.py
git commit -m "feat: add HITL high-risk confirmation gate in CLI"
```

---

### Task 15: E2E tests update

**Files:**
- Modify: `tests/test_e2e.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update conftest.py**

Add `IndexKlineBar` import and mock to `mock_market_api` fixture.

- [ ] **Step 2: Update E2E tests for new output format**

Update existing E2E tests to expect `summary` + `action_detail` instead of `recommendation`. Add new E2E test for parallel item flow.

- [ ] **Step 3: Run full test suite**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```
git add tests/test_e2e.py tests/conftest.py
git commit -m "test: update E2E tests for Phase 3 output format"
```

---

### Task 16: Docs + cleanup

**Files:**
- Modify: `docs/PROBLEMS.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: Update PROBLEMS.md**

Correct item 6: "存世量只有单品接口，无排行榜" → "已解决：排行榜 filter 支持 `存世量_存世量_升序/降序`"

- [ ] **Step 2: Update TODO.md**

Mark Phase 3 items as complete. Add Phase 4 items if applicable.

- [ ] **Step 3: Run full test suite one final time**

```
C:/Users/henry/.conda/envs/CSQAQ/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```
git add docs/PROBLEMS.md docs/TODO.md
git commit -m "docs: update PROBLEMS and TODO for Phase 3 completion"
```
