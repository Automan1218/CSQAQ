import pytest
from unittest.mock import patch
from csqaq.components.models.factory import ModelConfig, ModelFactory


def test_register_and_get_config():
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini", temperature=0.0)
    config = factory.get_config("router")
    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.0


def test_get_config_unknown_role_raises():
    factory = ModelFactory()
    with pytest.raises(KeyError, match="unknown_role"):
        factory.get_config("unknown_role")


def test_register_multiple_roles():
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini")
    factory.register("analyst", provider="openai", model="gpt-4o")
    factory.register("advisor", provider="openai", model="gpt-5")
    assert factory.get_config("router").model == "gpt-4o-mini"
    assert factory.get_config("analyst").model == "gpt-4o"
    assert factory.get_config("advisor").model == "gpt-5"


def test_create_model_returns_chat_model():
    """Verify create_model calls the right provider and returns a model."""
    factory = ModelFactory()
    factory.register("router", provider="openai", model="gpt-4o-mini", temperature=0.0)
    # Mock the actual OpenAI model creation to avoid needing API key
    with patch("csqaq.components.models.providers.ChatOpenAI") as mock_cls:
        mock_cls.return_value = "mock_model"
        model = factory.create("router")
        mock_cls.assert_called_once_with(model="gpt-4o-mini", temperature=0.0)
        assert model == "mock_model"
