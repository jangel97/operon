from __future__ import annotations

import pytest

from operon.agent.spec import ApprovalMode, ConstraintsSpec, PolicySpec
from operon.policy.engine import PolicyEngine, PolicyResult
from operon.tools.base import Tool, ToolRegistry


class FakeTool(Tool):
    @property
    def name(self) -> str:
        return "kubectl"

    def actions(self) -> list[dict]:
        return [
            {"name": "get_pods", "type": "read", "description": "List pods", "params": {}},
            {"name": "delete_pod", "type": "write", "description": "Delete pod", "params": {}},
        ]

    def execute(self, action: str, params: dict) -> str:
        return f"executed {action}"


def make_engine(
    max_actions: int = 10,
    denied_patterns: list[str] | None = None,
    approval: ApprovalMode | None = None,
) -> PolicyEngine:
    registry = ToolRegistry()
    registry.register(FakeTool(), approval=approval)
    return PolicyEngine(
        PolicySpec(
            constraints=ConstraintsSpec(
                max_actions=max_actions,
                denied_patterns=denied_patterns or [],
            ),
        ),
        tool_registry=registry,
    )


# --- Per-action approval ---


class TestDefaultApproval:
    def test_read_action_no_approval_by_default(self):
        engine = make_engine()
        result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert result.allowed is True
        assert result.requires_approval is False

    def test_write_action_requires_approval_by_default(self):
        engine = make_engine()
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is True

    def test_unknown_type_defaults_to_read(self):
        engine = make_engine()
        result = engine.check("kubectl:get_pods", action_meta={})
        assert result.allowed is True
        assert result.requires_approval is False


class TestExplicitApproval:
    def test_approval_required_forces_approval_on_read(self):
        engine = make_engine(approval=ApprovalMode.REQUIRED)
        result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert result.allowed is True
        assert result.requires_approval is True

    def test_approval_none_skips_approval_on_write(self):
        engine = make_engine(approval=ApprovalMode.NONE)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is False

    def test_approval_required_on_write(self):
        engine = make_engine(approval=ApprovalMode.REQUIRED)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is True


class TestPerActionOverride:
    def test_override_approval_for_specific_action(self):
        registry = ToolRegistry()
        registry.register(FakeTool())
        registry.set_approval("kubectl:delete_pod", ApprovalMode.NONE)
        engine = PolicyEngine(PolicySpec(), tool_registry=registry)

        read_result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert read_result.requires_approval is False

        write_result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert write_result.requires_approval is False


# --- Max actions ---


class TestMaxActions:
    def test_under_limit_allowed(self):
        engine = make_engine(max_actions=3)
        result = engine.check("kubectl:get_pods")
        assert result.allowed is True

    def test_at_limit_denied(self):
        engine = make_engine(max_actions=2)
        engine.record_action()
        engine.record_action()
        result = engine.check("kubectl:get_pods")
        assert result.allowed is False
        assert "Max actions limit" in result.reason

    def test_record_action_increments_count(self):
        engine = make_engine(max_actions=5)
        assert engine.action_count == 0
        engine.record_action()
        engine.record_action()
        assert engine.action_count == 2

    def test_max_actions_one(self):
        engine = make_engine(max_actions=1)
        result = engine.check("kubectl:get_pods")
        assert result.allowed is True
        engine.record_action()
        result = engine.check("kubectl:get_pods")
        assert result.allowed is False


# --- Denied patterns ---


class TestDeniedPatterns:
    def test_matching_pattern_denied(self):
        engine = make_engine(denied_patterns=[r"--force"])
        result = engine.check(
            "kubectl:delete_pod",
            params={"command": "delete pod foo --force"},
            action_meta={"type": "write"},
        )
        assert result.allowed is False
        assert "denied pattern" in result.reason

    def test_non_matching_pattern_allowed(self):
        engine = make_engine(denied_patterns=[r"--force"])
        result = engine.check(
            "kubectl:get_pods",
            params={"command": "get pods -n default"},
        )
        assert result.allowed is True

    def test_multiple_patterns(self):
        engine = make_engine(denied_patterns=[r"--force", r"rm\s+-rf"])
        result = engine.check(
            "kubectl:delete_pod",
            params={"command": "exec pod -- rm -rf /"},
        )
        assert result.allowed is False

    def test_no_params_skips_check(self):
        engine = make_engine(denied_patterns=[r"--force"])
        result = engine.check("kubectl:get_pods")
        assert result.allowed is True


# --- Check order ---


class TestCheckOrder:
    def test_max_actions_checked_first(self):
        engine = make_engine(max_actions=0, denied_patterns=[r"--force"])
        result = engine.check(
            "kubectl:get_pods",
            params={"command": "--force"},
        )
        assert result.allowed is False
        assert "Max actions" in result.reason
