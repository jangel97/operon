from __future__ import annotations

import os
import re

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def resolve_env_vars(text: str) -> str:
    def _replace(match: re.Match) -> str:
        expr = match.group(1)
        if ":-" in expr:
            name, _, default = expr.partition(":-")
            return os.environ.get(name.strip(), default)
        value = os.environ.get(expr.strip())
        if value is None:
            raise ValueError(f"Environment variable not set: {expr.strip()}")
        return value

    return _ENV_PATTERN.sub(_replace, text)
