from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from .factory import ModelConfig


def create_openai_model(config: ModelConfig) -> ChatOpenAI:
    return ChatOpenAI(model=config.model, temperature=config.temperature, **config.extra)
