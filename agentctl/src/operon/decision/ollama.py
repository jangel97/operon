from __future__ import annotations

from openai import OpenAI

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434/v1", temperature: float | None = None):
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self.model = model
        self.temperature = temperature

    def _call_llm(self, messages: list[dict]) -> str:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
