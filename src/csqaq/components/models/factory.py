from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel


@dataclass
class ModelConfig:
    provider: str
    model: str
    temperature: float = 0.7
    extra: dict[str, Any] = field(default_factory=dict)


class ModelFactory:
    """Registry + Factory for LLM models. Config-driven, no code changes needed to switch models."""

    def __init__(self):
        self._registry: dict[str, ModelConfig] = {}

    def register(self, role: str, provider: str, model: str, temperature: float = 0.7, **kwargs: Any) -> None:
        self._registry[role] = ModelConfig(
            provider=provider, model=model, temperature=temperature, extra=kwargs,
        )

    def get_config(self, role: str) -> ModelConfig:
        if role not in self._registry:
            raise KeyError(f"No model registered for role: {role}")
        return self._registry[role]

    def create(self, role: str) -> BaseChatModel:
        config = self.get_config(role)
        return _create_model(config)


def _create_model(config: ModelConfig) -> BaseChatModel:
    from .providers import create_openai_model

    creators = {
        "openai": create_openai_model,
    }
    creator = creators.get(config.provider)
    if creator is None:
        raise ValueError(f"Unknown provider: {config.provider}")
    return creator(config)
