from __future__ import annotations

from abc import ABC, abstractmethod


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
        self._action_index: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        for action in tool.actions():
            self._action_index[action["name"]] = tool

    def get_actions(self) -> list[dict]:
        all_actions: list[dict] = []
        for tool in self._tools.values():
            all_actions.extend(tool.actions())
        return all_actions

    def execute(self, action: str, params: dict) -> str:
        tool = self._action_index.get(action)
        if not tool:
            raise ValueError(f"Unknown action: '{action}'")
        return tool.execute(action, params)
