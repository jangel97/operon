from __future__ import annotations

from pathlib import Path


def execute(action: str, params: dict) -> str:
    if action != "write_file":
        return f"Unknown action: {action}"

    path = params.get("path")
    content = params.get("content")
    if not path or not content:
        return "Error: missing required parameters 'path' and 'content'"

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Written {len(content)} bytes to {path}"
