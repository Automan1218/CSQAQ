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
