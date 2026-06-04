from __future__ import annotations

import pytest

from operon.agent.spec import ApprovalMode
from operon.tools.base import Tool, ToolRegistry


class FakeTool(Tool):
    @property
    def name(self) -> str:
        return "kubectl"

    def actions(self) -> list[dict]:
        return [
            {"name": "get_pods", "type": "read", "description": "List pods", "params": {}},
            {"name": "get_logs", "type": "read", "description": "Get logs", "params": {}},
            {"name": "delete_pod", "type": "write", "description": "Delete pod", "params": {}},
        ]

    def execute(self, action: str, params: dict) -> str:
        return f"executed {action} with {params}"


class AnotherTool(Tool):
    @property
    def name(self) -> str:
        return "websearch"

    def actions(self) -> list[dict]:
        return [
            {"name": "web_search", "type": "read", "description": "Search", "params": {}},
            {"name": "web_fetch", "type": "read", "description": "Fetch", "params": {}},
        ]

    def execute(self, action: str, params: dict) -> str:
        return f"executed {action} with {params}"


def make_registry(*tools_with_approval: tuple[Tool, ApprovalMode | None] | Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for item in tools_with_approval:
        if isinstance(item, tuple):
            registry.register(item[0], approval=item[1])
        else:
            registry.register(item)
    return registry


# --- Namespacing ---


class TestNamespacing:
    def test_actions_are_namespaced(self):
        registry = make_registry(FakeTool())
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "kubectl:get_pods" in names
        assert "kubectl:delete_pod" in names
        assert "get_pods" not in names

    def test_multiple_tools_namespaced(self):
        registry = make_registry(FakeTool(), AnotherTool())
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "kubectl:get_pods" in names
        assert "websearch:web_search" in names

    def test_action_count(self):
        registry = make_registry(FakeTool(), AnotherTool())
        actions = registry.get_actions()
        assert len(actions) == 5


# --- Approval ---


class TestApproval:
    def test_default_approval_is_none(self):
        registry = make_registry(FakeTool())
        assert registry.get_approval("kubectl:get_pods") is None
        assert registry.get_approval("kubectl:delete_pod") is None

    def test_explicit_approval_stored(self):
        registry = make_registry((FakeTool(), ApprovalMode.REQUIRED))
        assert registry.get_approval("kubectl:get_pods") == ApprovalMode.REQUIRED
        assert registry.get_approval("kubectl:delete_pod") == ApprovalMode.REQUIRED

    def test_approval_none_stored(self):
        registry = make_registry((FakeTool(), ApprovalMode.NONE))
        assert registry.get_approval("kubectl:get_pods") == ApprovalMode.NONE

    def test_set_approval_overrides(self):
        registry = make_registry(FakeTool())
        registry.set_approval("kubectl:delete_pod", ApprovalMode.REQUIRED)
        assert registry.get_approval("kubectl:get_pods") is None
        assert registry.get_approval("kubectl:delete_pod") == ApprovalMode.REQUIRED

    def test_unknown_action_approval_returns_none(self):
        registry = make_registry(FakeTool())
        assert registry.get_approval("nonexistent:action") is None


# --- has_tool ---


class TestHasTool:
    def test_registered_tool(self):
        registry = make_registry(FakeTool())
        assert registry.has_tool("kubectl") is True

    def test_unregistered_tool(self):
        registry = make_registry(FakeTool())
        assert registry.has_tool("unknown") is False


# --- Action metadata ---


class TestActionMeta:
    def test_get_action_meta_returns_metadata(self):
        registry = make_registry(FakeTool())
        meta = registry.get_action_meta("kubectl:get_pods")
        assert meta["name"] == "kubectl:get_pods"
        assert meta["type"] == "read"
        assert meta["description"] == "List pods"

    def test_get_action_meta_unknown_returns_empty(self):
        registry = make_registry(FakeTool())
        meta = registry.get_action_meta("kubectl:nonexistent")
        assert meta == {}

    def test_meta_preserves_original_fields(self):
        registry = make_registry(FakeTool())
        meta = registry.get_action_meta("kubectl:delete_pod")
        assert meta["type"] == "write"


# --- Execution ---


class TestExecution:
    def test_execute_routes_to_correct_tool(self):
        registry = make_registry(FakeTool(), AnotherTool())
        result = registry.execute("kubectl:get_pods", {"namespace": "default"})
        assert "get_pods" in result
        assert "default" in result

    def test_execute_strips_namespace(self):
        registry = make_registry(FakeTool())
        result = registry.execute("kubectl:get_pods", {})
        assert result == "executed get_pods with {}"

    def test_execute_unknown_action_raises(self):
        registry = make_registry(FakeTool())
        with pytest.raises(ValueError, match="Unknown action"):
            registry.execute("kubectl:nonexistent", {})

    def test_execute_wrong_tool_prefix_raises(self):
        registry = make_registry(FakeTool())
        with pytest.raises(ValueError, match="Unknown action"):
            registry.execute("aws:list_instances", {})

    def test_execute_unnamespaced_raises(self):
        registry = make_registry(FakeTool())
        with pytest.raises(ValueError, match="Unknown action"):
            registry.execute("get_pods", {})


# --- Config ---


class TestConfig:
    def test_config_merged_into_params(self):
        registry = ToolRegistry()
        registry.register(FakeTool(), config={"token": "secret123"})
        result = registry.execute("kubectl:get_pods", {"namespace": "default"})
        assert "token" in result
        assert "secret123" in result
        assert "default" in result

    def test_params_override_config(self):
        registry = ToolRegistry()
        registry.register(FakeTool(), config={"namespace": "from-config"})
        result = registry.execute("kubectl:get_pods", {"namespace": "from-params"})
        assert "from-params" in result
        assert "from-config" not in result

    def test_no_config_passes_params_unchanged(self):
        registry = ToolRegistry()
        registry.register(FakeTool())
        result = registry.execute("kubectl:get_pods", {"namespace": "default"})
        assert result == "executed get_pods with {'namespace': 'default'}"

    def test_config_not_shared_between_tools(self):
        registry = ToolRegistry()
        registry.register(FakeTool(), config={"token": "secret"})
        registry.register(AnotherTool())
        result = registry.execute("websearch:web_search", {"query": "test"})
        assert "token" not in result
        assert "secret" not in result
