from csqaq.infrastructure.csqaq_client.rank_schemas import PageListItem, RankItem


class TestRankItem:
    def test_parse(self):
        data = {
            "id": 7310, "name": "AK-47 | 红线 (久经沙场)",
            "img": "https://example.com/ak.png",
            "exterior_localized_name": "久经沙场",
            "rarity_localized_name": "保密",
            "buff_sell_price": 85.5, "buff_sell_num": 1200,
            "buff_buy_price": 82.0, "buff_buy_num": 500,
            "steam_sell_price": 12.35, "steam_sell_num": 3000,
            "steam_buy_price": 11.0, "steam_buy_num": 800,
            "yyyp_sell_price": 83.0, "yyyp_sell_num": 600,
            "yyyp_buy_price": 80.0, "yyyp_buy_num": 200,
            "yyyp_lease_price": 0.5, "yyyp_long_lease_price": 0.3,
            "buff_price_chg": 1.25,
            "sell_price_1": 1.0, "sell_price_7": -2.0,
            "sell_price_15": 0, "sell_price_30": 3.0,
            "sell_price_90": 5.0, "sell_price_180": -1.0, "sell_price_365": 10.0,
            "sell_price_rate_1": 1.18, "sell_price_rate_7": -2.29,
            "sell_price_rate_15": 0, "sell_price_rate_30": 3.64,
            "sell_price_rate_90": 6.21, "sell_price_rate_180": -1.16,
            "sell_price_rate_365": 13.3,
            "created_at": "2026-03-18T14:20:19", "rank_num": 42,
        }
        item = RankItem.model_validate(data)
        assert item.id == 7310
        assert item.buff_sell_price == 85.5
        assert item.sell_price_rate_1 == 1.18

    def test_nullable_exterior(self):
        data = {
            "id": 100, "name": "印花 | test",
            "img": "", "exterior_localized_name": None,
            "rarity_localized_name": "高级",
            "buff_sell_price": 0.02, "buff_sell_num": 300,
            "buff_buy_price": 0.06, "buff_buy_num": 11,
            "steam_sell_price": 0.04, "steam_sell_num": 4000,
            "steam_buy_price": 0.03, "steam_buy_num": 400,
            "yyyp_sell_price": 0.02, "yyyp_sell_num": 500,
            "yyyp_buy_price": 0, "yyyp_buy_num": 0,
            "yyyp_lease_price": 0, "yyyp_long_lease_price": 0,
            "buff_price_chg": 0,
            "sell_price_1": 0, "sell_price_7": 0,
            "sell_price_15": 0, "sell_price_30": 0,
            "sell_price_90": 0, "sell_price_180": -0.01, "sell_price_365": -0.02,
            "sell_price_rate_1": 0, "sell_price_rate_7": 0,
            "sell_price_rate_15": 0, "sell_price_rate_30": 0,
            "sell_price_rate_90": 0, "sell_price_rate_180": -33.33,
            "sell_price_rate_365": -50,
            "created_at": "2026-03-18T14:20:19", "rank_num": 0,
        }
        item = RankItem.model_validate(data)
        assert item.exterior_localized_name is None


class TestPageListItem:
    def test_parse(self):
        data = {
            "id": 6798, "name": "蝴蝶刀 | 蓝钢 (崭新出厂)",
            "exterior_localized_name": "崭新出厂",
            "rarity_localized_name": "隐秘",
            "img": "https://example.com/knife.png",
            "yyyp_sell_price": 14300, "yyyp_sell_num": 16,
        }
        item = PageListItem.model_validate(data)
        assert item.id == 6798
        assert item.yyyp_sell_num == 16
