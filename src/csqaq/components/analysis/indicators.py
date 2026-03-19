import statistics
from typing import NamedTuple


class MACDResult(NamedTuple):
    macd_line: float
    signal_line: float
    histogram: float


class BollingerResult(NamedTuple):
    upper: float
    middle: float
    lower: float


class TechnicalIndicators:
    """Pure numerical computations for technical analysis.

    Agents don't do math — this module does.
    """

    @staticmethod
    def moving_average(prices: list[float], window: int) -> list[float | None]:
        """Simple Moving Average. Returns None for positions with insufficient data."""
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < window - 1:
                result.append(None)
            else:
                window_slice = prices[i - window + 1 : i + 1]
                result.append(sum(window_slice) / window)
        return result

    @staticmethod
    def exponential_moving_average(
        prices: list[float], window: int, smoothing: int = 2
    ) -> list[float | None]:
        """Exponential Moving Average. Returns None for positions with insufficient data.

        First EMA value is the SMA of the first `window` prices.
        Subsequent values use: EMA = price * multiplier + prev_EMA * (1 - multiplier)
        where multiplier = smoothing / (window + 1).
        """
        result: list[float | None] = [None] * len(prices)
        if len(prices) < window:
            return result
        multiplier = smoothing / (window + 1)
        first_sma = sum(prices[:window]) / window
        result[window - 1] = first_sma
        for i in range(window, len(prices)):
            result[i] = prices[i] * multiplier + result[i - 1] * (1 - multiplier)
        return result

    @staticmethod
    def volatility(prices: list[float], window: int) -> float:
        """Standard deviation of price changes over the window.

        Returns 0.0 if fewer than 2 data points in window.
        """
        if len(prices) < 2:
            return 0.0
        recent = prices[-window:] if len(prices) >= window else prices
        if len(recent) < 2:
            return 0.0
        return statistics.stdev(recent)

    @staticmethod
    def price_momentum(prices: list[float], period: int) -> float:
        """Price change over a period: current - price_N_periods_ago."""
        if len(prices) <= period:
            return prices[-1] - prices[0] if len(prices) >= 2 else 0.0
        return prices[-1] - prices[-1 - period]

    @staticmethod
    def platform_spread(price_a: float, price_b: float) -> float:
        """Percentage spread between two platform prices.

        Returns (a - b) / b * 100. Positive means A is more expensive.
        """
        if price_b == 0:
            return 0.0
        return (price_a - price_b) / price_b * 100

    @staticmethod
    def volume_trend(volumes: list[int], window: int) -> str:
        """Classify recent volume trend as 'increasing', 'decreasing', or 'stable'.

        Compares average of last `window` volumes to the `window` before that.
        Uses a 10% threshold for classification.
        """
        if len(volumes) < window * 2:
            return "stable"
        recent = volumes[-window:]
        previous = volumes[-window * 2 : -window]
        if not previous:
            return "stable"
        avg_recent = sum(recent) / len(recent)
        avg_previous = sum(previous) / len(previous)
        if avg_previous == 0:
            return "stable"
        change_pct = (avg_recent - avg_previous) / avg_previous * 100
        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        return "stable"

    @staticmethod
    def rsi(prices: list[float], period: int = 14) -> float:
        """Relative Strength Index using Wilder's method.

        Returns 50.0 (neutral) if insufficient data (fewer than period+1 prices).
        """
        if len(prices) < period + 1:
            return 50.0
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0.0 for c in changes]
        losses = [-c if c < 0 else 0.0 for c in changes]
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1 + rs)

    @staticmethod
    def macd(
        prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> MACDResult:
        """MACD indicator using EMA internally.

        Returns MACDResult(0, 0, 0) if insufficient data.
        """
        if len(prices) < slow:
            return MACDResult(0.0, 0.0, 0.0)
        fast_ema = TechnicalIndicators.exponential_moving_average(prices, fast)
        slow_ema = TechnicalIndicators.exponential_moving_average(prices, slow)
        macd_values: list[float] = []
        for f, s in zip(fast_ema, slow_ema):
            if f is not None and s is not None:
                macd_values.append(f - s)
        if len(macd_values) < signal:
            return MACDResult(0.0, 0.0, 0.0)
        signal_ema = TechnicalIndicators.exponential_moving_average(macd_values, signal)
        last_macd = macd_values[-1]
        last_signal = signal_ema[-1]
        if last_signal is None:
            return MACDResult(0.0, 0.0, 0.0)
        histogram = last_macd - last_signal
        return MACDResult(last_macd, last_signal, histogram)

    @staticmethod
    def bollinger_bands(
        prices: list[float], window: int = 20, num_std: int = 2
    ) -> BollingerResult:
        """Bollinger Bands: middle = SMA, upper/lower = middle ± num_std * stdev.

        Returns BollingerResult(0, 0, 0) if insufficient data.
        """
        if len(prices) < window:
            return BollingerResult(0.0, 0.0, 0.0)
        window_slice = prices[-window:]
        middle = sum(window_slice) / window
        std = statistics.pstdev(window_slice)
        upper = middle + num_std * std
        lower = middle - num_std * std
        return BollingerResult(upper, middle, lower)
