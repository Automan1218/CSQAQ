from pydantic import BaseModel


class RankItem(BaseModel):
    """Rank list item from POST /api/v1/info/get_rank_list"""
    id: int
    name: str
    img: str
    exterior_localized_name: str | None
    rarity_localized_name: str
    buff_sell_price: float
    buff_sell_num: int
    buff_buy_price: float
    buff_buy_num: int
    steam_sell_price: float
    steam_sell_num: int
    steam_buy_price: float = 0
    steam_buy_num: int = 0
    yyyp_sell_price: float
    yyyp_sell_num: int
    yyyp_buy_price: float = 0
    yyyp_buy_num: int = 0
    yyyp_lease_price: float = 0
    yyyp_long_lease_price: float = 0
    sell_price_1: float = 0
    sell_price_7: float = 0
    sell_price_15: float = 0
    sell_price_30: float = 0
    sell_price_90: float = 0
    sell_price_180: float = 0
    sell_price_365: float = 0
    buff_price_chg: float = 0
    sell_price_rate_1: float = 0
    sell_price_rate_7: float = 0
    sell_price_rate_15: float = 0
    sell_price_rate_30: float = 0
    sell_price_rate_90: float = 0
    sell_price_rate_180: float = 0
    sell_price_rate_365: float = 0
    created_at: str = ""
    rank_num: int = 0


class PageListItem(BaseModel):
    """Page list item from POST /api/v1/info/get_page_list"""
    id: int
    name: str
    exterior_localized_name: str | None
    rarity_localized_name: str
    img: str
    yyyp_sell_price: float
    yyyp_sell_num: int
