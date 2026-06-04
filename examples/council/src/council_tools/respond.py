from __future__ import annotations

from operon.tools.base import Tool


class RespondTool(Tool):
    @property
    def name(self) -> str:
        return "respond"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "respond",
                "type": "read",
                "description": "Deliver your response to the discussion",
                "params": {
                    "message": "string (required)",
                },
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        if action == "respond":
            return params.get("message", "")
        raise ValueError(f"Unknown action: {action}")
