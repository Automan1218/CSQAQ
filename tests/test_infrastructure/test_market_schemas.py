from csqaq.infrastructure.csqaq_client.market_schemas import (
    GreedyStatus, HomeData, OnlineNumber, RateData,
    SubData, SubIndexCount, SubIndexItem,
)


class TestSubIndexItem:
    def test_parse(self):
        data = {
            "id": 1, "name": "BUFF饰品指数", "name_key": "buff",
            "img": "https://example.com/img.png", "market_index": 1052.3,
            "chg_num": 2.5, "chg_rate": 0.24, "open": 1050.0,
            "close": 1052.3, "high": 1055.0, "low": 1048.0,
            "updated_at": "2026-03-18 12:00:00",
        }
        item = SubIndexItem.model_validate(data)
        assert item.market_index == 1052.3
        assert item.chg_rate == 0.24


class TestRateData:
    def test_parse(self):
        data = {
            "count_positive_1": 500, "count_negative_1": 300, "count_zero_1": 200,
            "count_positive_7": 450, "count_negative_7": 350, "count_zero_7": 200,
            "count_positive_15": 400, "count_negative_15": 400, "count_zero_15": 200,
            "count_positive_30": 420, "count_negative_30": 380, "count_zero_30": 200,
            "count_positive_90": 500, "count_negative_90": 300, "count_zero_90": 200,
            "count_positive_180": 480, "count_negative_180": 320, "count_zero_180": 200,
        }
        rate = RateData.model_validate(data)
        assert rate.count_positive_1 == 500
        assert rate.count_negative_30 == 380


class TestSubData:
    def test_parse(self):
        data = {
            "timestamp": [1710720000, 1710806400],
            "count": {
                "name": "BUFF饰品指数", "img": "", "now": 1052.3,
                "amplitude": 2.5, "rate": 0.24, "max_value": 1055,
                "min_value": 1048.0, "consecutive_days": 3,
            },
            "main_data": [[1052.3, 2.5, 0.24], [1050.0, -2.3, -0.22]],
            "hourly_list": [1050.0, 1051.0, 1052.3],
        }
        sub = SubData.model_validate(data)
        assert sub.count.now == 1052.3
        assert sub.count.consecutive_days == 3
        assert len(sub.main_data) == 2
