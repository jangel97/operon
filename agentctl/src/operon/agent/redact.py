from __future__ import annotations

from typing import Any

PLACEHOLDER = "***REDACTED***"
MIN_SECRET_LEN = 4


class Redactor:
    def __init__(self) -> None:
        self._secrets: list[str] = []

    def add_secret(self, value: str) -> None:
        if value and len(value) >= MIN_SECRET_LEN and value not in self._secrets:
            self._secrets.append(value)

    def redact(self, data: Any) -> Any:
        if not self._secrets:
            return data
        if isinstance(data, str):
            result = data
            for secret in self._secrets:
                result = result.replace(secret, PLACEHOLDER)
            return result
        if isinstance(data, dict):
            return {k: self.redact(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.redact(item) for item in data]
        return data
