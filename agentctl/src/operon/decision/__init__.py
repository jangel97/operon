from __future__ import annotations

from operon.decision.base import LLMProvider

_providers: dict[str, type[LLMProvider]] = {}


def register_provider(name: str, cls: type[LLMProvider]) -> None:
    _providers[name] = cls


def create_provider(name: str, **kwargs) -> LLMProvider:
    if name not in _providers:
        available = ", ".join(_providers.keys()) or "none"
        raise ValueError(f"Unknown provider: '{name}'. Available: {available}")
    return _providers[name](**kwargs)


from operon.decision.ollama import OllamaProvider  # noqa: E402
from operon.decision.openai import OpenAIProvider  # noqa: E402

register_provider("openai", OpenAIProvider)
register_provider("ollama", OllamaProvider)
