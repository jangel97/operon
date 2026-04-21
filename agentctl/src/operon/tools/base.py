from __future__ import annotations

from abc import ABC, abstractmethod

from operon.agent.spec import PolicyMode


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def actions(self) -> list[dict]:
        """Return list of available actions with name, description, and params schema."""
        pass

    @abstractmethod
    def execute(self, action: str, params: dict) -> str:
        pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._action_index: dict[str, tuple[Tool, str]] = {}
        self._action_meta: dict[str, dict] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        for action in tool.actions():
            fqn = f"{tool.name}:{action['name']}"
            self._action_index[fqn] = (tool, action["name"])
            self._action_meta[fqn] = {**action, "name": fqn}

    def get_actions(
        self,
        allowed: list[str] | None = None,
        policy_mode: PolicyMode = PolicyMode.AUTONOMOUS,
    ) -> list[dict]:
        actions = list(self._action_meta.values())
        if allowed:
            actions = [a for a in actions if a["name"] in allowed]
        if policy_mode == PolicyMode.READ_ONLY:
            actions = [a for a in actions if a.get("type", "read") != "write"]
        return actions

    def get_action_meta(self, action: str) -> dict:
        return self._action_meta.get(action, {})

    def execute(self, action: str, params: dict) -> str:
        entry = self._action_index.get(action)
        if not entry:
            raise ValueError(f"Unknown action: '{action}'")
        tool, local_name = entry
        return tool.execute(local_name, params)
