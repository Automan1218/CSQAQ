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
