import os
import pytest
from csqaq.config import Settings


def test_settings_loads_defaults():
    """Settings should load with defaults when required fields are provided."""
    settings = Settings(
        csqaq_api_token="test-token",
        openai_api_key="test-key",
    )
    assert settings.csqaq_base_url == "https://api.csqaq.com/api/v1"
    assert settings.csqaq_rate_limit == 1.0
    assert settings.router_model == "gpt-4o-mini"
    assert settings.analyst_model == "gpt-4o"
    assert settings.advisor_model == "gpt-5"
    assert settings.database_url == "sqlite:///data/csqaq.db"
    assert settings.mode == "local"
    assert settings.api_cache_ttl == 60
    assert settings.daily_token_budget == 500_000
    assert settings.monthly_token_budget == 10_000_000


def test_settings_local_mode_requires_tokens():
    """In local mode, csqaq_api_token and openai_api_key are required."""
    settings = Settings(
        csqaq_api_token="tok",
        openai_api_key="key",
        mode="local",
    )
    assert settings.csqaq_api_token == "tok"
    assert settings.openai_api_key == "key"


def test_settings_server_mode_allows_empty_tokens(monkeypatch):
    """In server mode, tokens can be empty (users bind their own)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CSQAQ_API_TOKEN", raising=False)
    settings = Settings(
        mode="server",
        secret_key="test-secret",
    )
    assert settings.csqaq_api_token == ""
    assert settings.openai_api_key == ""
