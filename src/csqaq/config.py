from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Runtime mode
    mode: Literal["local", "server"] = "local"

    # CSQAQ API
    csqaq_api_token: str = ""
    csqaq_base_url: str = "https://api.csqaq.com/api/v1"
    csqaq_rate_limit: float = 1.0

    # OpenAI
    openai_api_key: str = ""
    router_model: str = "gpt-4o-mini"
    analyst_model: str = "gpt-4o"
    advisor_model: str = "gpt-5"

    # Database
    database_url: str = "sqlite:///data/csqaq.db"

    # Cache
    redis_url: str | None = None
    api_cache_ttl: int = 60

    # Monitoring
    watchlist_poll_interval: int = 300
    market_poll_interval: int = 300
    scout_scan_interval: int = 1800
    alert_price_threshold_pct: float = 5.0

    # Memory
    max_history_messages: int = 20
    chromadb_path: str = "data/chroma"

    # Cost control
    daily_token_budget: int = 500_000
    monthly_token_budget: int = 10_000_000

    # Auth (server mode)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Notifications (server mode)
    notify_webhook_url: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
