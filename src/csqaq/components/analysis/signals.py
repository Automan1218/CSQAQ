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
    """Detect MA golden/death cross. Returns None if insufficient data.

    Scans the most recent `long` periods for a crossover event to handle cases
    where the cross occurred a few bars ago but the signal is still current.
    Requires at least long+1 data points.
    """
    if len(prices) < long + 1:
        return None

    short_ma = TechnicalIndicators.moving_average(prices, short)
    long_ma = TechnicalIndicators.moving_average(prices, long)

    # Scan recent bars for the most recent crossover; report it if found
    # We look back at most `long` bars so we don't flag stale signals
    lookback = min(long, len(prices) - 1)
    start = len(prices) - lookback

    last_cross_direction: str | None = None
    for i in range(start, len(prices)):
        short_val = short_ma[i]
        long_val = long_ma[i]
        if short_val is None or long_val is None:
            continue
        if i == start:
            # No previous bar to compare against in this window
            continue
        prev_short = short_ma[i - 1]
        prev_long = long_ma[i - 1]
        if prev_short is None or prev_long is None:
            continue

        # Golden cross: short MA crosses above long MA
        if prev_short <= prev_long and short_val > long_val:
            last_cross_direction = "bullish"
        # Death cross: short MA crosses below long MA
        elif prev_short >= prev_long and short_val < long_val:
            last_cross_direction = "bearish"

    if last_cross_direction == "bullish":
        return Signal(
            name="ma_crossover",
            direction="bullish",
            strength=0.6,
            description="均线金叉：短期均线上穿长期均线，看涨信号",
        )

    if last_cross_direction == "bearish":
        return Signal(
            name="ma_crossover",
            direction="bearish",
            strength=0.6,
            description="均线死叉：短期均线下穿长期均线，看跌信号",
        )

    return None


def detect_rsi_extreme(prices: list[float], period: int = 14) -> Signal | None:
    """Detect RSI > 70 (overbought/bearish) or < 30 (oversold/bullish)."""
    if len(prices) < period + 1:
        return None

    rsi_value = TechnicalIndicators.rsi(prices, period)

    if rsi_value > 70:
        return Signal(
            name="rsi_extreme",
            direction="bearish",
            strength=0.7,
            description=f"RSI超买（{rsi_value:.1f} > 70）：价格可能回调，看跌信号",
        )

    if rsi_value < 30:
        return Signal(
            name="rsi_extreme",
            direction="bullish",
            strength=0.7,
            description=f"RSI超卖（{rsi_value:.1f} < 30）：价格可能反弹，看涨信号",
        )

    return None


def detect_macd_crossover(prices: list[float]) -> Signal | None:
    """Detect MACD line crossing signal line.

    Uses histogram sign to determine direction. Requires enough data for
    slow EMA (26) + signal EMA (9) = at least 35 data points for a
    meaningful crossover detection. Returns None if insufficient data.
    """
    # MACD needs at least slow(26) periods; returns (0,0,0) sentinel otherwise
    if len(prices) < 26:
        return None

    result = TechnicalIndicators.macd(prices)

    # macd() returns (0,0,0) when insufficient data
    if result.macd_line == 0.0 and result.signal_line == 0.0 and result.histogram == 0.0:
        return None

    if result.histogram > 0:
        return Signal(
            name="macd_crossover",
            direction="bullish",
            strength=0.7,
            description=f"MACD金叉：MACD线在信号线上方（柱状图={result.histogram:.4f}），看涨信号",
        )

    if result.histogram < 0:
        return Signal(
            name="macd_crossover",
            direction="bearish",
            strength=0.7,
            description=f"MACD死叉：MACD线在信号线下方（柱状图={result.histogram:.4f}），看跌信号",
        )

    return None


def detect_bollinger_breakout(prices: list[float]) -> Signal | None:
    """Detect price breaking above upper or below lower Bollinger band."""
    if len(prices) < 20:
        return None

    bands = TechnicalIndicators.bollinger_bands(prices)

    # bollinger_bands() returns (0,0,0) when insufficient data
    if bands.upper == 0.0 and bands.middle == 0.0 and bands.lower == 0.0:
        return None

    current_price = prices[-1]

    if current_price > bands.upper:
        return Signal(
            name="bollinger_breakout",
            direction="bearish",
            strength=0.8,
            description=(
                f"布林带上轨突破：当前价格({current_price:.2f}) > 上轨({bands.upper:.2f})，"
                "超买状态，看跌信号"
            ),
        )

    if current_price < bands.lower:
        return Signal(
            name="bollinger_breakout",
            direction="bullish",
            strength=0.8,
            description=(
                f"布林带下轨突破：当前价格({current_price:.2f}) < 下轨({bands.lower:.2f})，"
                "超卖状态，看涨信号"
            ),
        )

    return None


def detect_volume_price_divergence(prices: list[float], volumes: list[int]) -> Signal | None:
    """Detect divergence between price trend and volume trend.

    Price going up + volume going down = bearish (weak rally).
    Price going down + volume going up = bullish (accumulation).
    This has highest strength (0.9) due to T+7 market dynamics.
    """
    if len(prices) < 2 or len(volumes) < 2:
        return None

    # Use price_momentum to determine price direction
    period = min(len(prices) - 1, 5)
    price_change = TechnicalIndicators.price_momentum(prices, period)

    # Use volume_trend to determine volume direction
    # Need at least 2*window volumes for volume_trend; use window=len//2
    window = max(1, len(volumes) // 2)
    vol_trend = TechnicalIndicators.volume_trend(volumes, window)

    # Price up + volume down = weak rally (bearish)
    if price_change > 0 and vol_trend == "decreasing":
        return Signal(
            name="volume_price_divergence",
            direction="bearish",
            strength=0.9,
            description=(
                "量价背离（看跌）：价格上涨但成交量萎缩，涨势虚弱，"
                "T+7市场中建议谨慎追高"
            ),
        )

    # Price down + volume up = accumulation (bullish)
    if price_change < 0 and vol_trend == "increasing":
        return Signal(
            name="volume_price_divergence",
            direction="bullish",
            strength=0.9,
            description=(
                "量价背离（看涨）：价格下跌但成交量放大，主力吸筹迹象，"
                "T+7市场中可能存在买入机会"
            ),
        )

    return None
