from __future__ import annotations

from abc import ABC, abstractmethod

from operon.agent.spec import ApprovalMode


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
        self._approval: dict[str, ApprovalMode | None] = {}
        self._config: dict[str, dict] = {}

    def register(
        self,
        tool: Tool,
        approval: ApprovalMode | None = None,
        config: dict | None = None,
    ) -> None:
        self._tools[tool.name] = tool
        if config:
            self._config[tool.name] = config
        for action in tool.actions():
            fqn = f"{tool.name}:{action['name']}"
            self._action_index[fqn] = (tool, action["name"])
            self._action_meta[fqn] = {**action, "name": fqn}
            self._approval[fqn] = approval

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_actions(self) -> list[dict]:
        return list(self._action_meta.values())

    def get_approval(self, action: str) -> ApprovalMode | None:
        return self._approval.get(action)

    def set_approval(self, action: str, approval: ApprovalMode | None) -> None:
        if action in self._approval:
            self._approval[action] = approval

    def get_action_meta(self, action: str) -> dict:
        return self._action_meta.get(action, {})

    def execute(self, action: str, params: dict) -> str:
        entry = self._action_index.get(action)
        if not entry:
            raise ValueError(f"Unknown action: '{action}'")
        tool, local_name = entry
        merged = {**self._config.get(tool.name, {}), **params}
        return tool.execute(local_name, merged)
