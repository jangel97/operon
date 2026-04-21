from __future__ import annotations

import pytest

from operon.agent.spec import ConstraintsSpec, PolicyMode, PolicySpec
from operon.policy.engine import PolicyEngine, PolicyResult


def make_engine(
    mode: PolicyMode = PolicyMode.AUTONOMOUS,
    allowed_actions: list[str] | None = None,
    max_actions: int = 10,
    denied_patterns: list[str] | None = None,
) -> PolicyEngine:
    return PolicyEngine(
        PolicySpec(
            mode=mode,
            allowed_actions=allowed_actions or [],
            constraints=ConstraintsSpec(
                max_actions=max_actions,
                denied_patterns=denied_patterns or [],
            ),
        )
    )


# --- Policy modes ---


class TestAutonomousMode:
    def test_read_action_allowed_without_approval(self):
        engine = make_engine(mode=PolicyMode.AUTONOMOUS)
        result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert result.allowed is True
        assert result.requires_approval is False

    def test_write_action_allowed_without_approval(self):
        engine = make_engine(mode=PolicyMode.AUTONOMOUS)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is False


class TestApprovalRequiredMode:
    def test_read_action_requires_approval(self):
        engine = make_engine(mode=PolicyMode.APPROVAL_REQUIRED)
        result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert result.allowed is True
        assert result.requires_approval is True

    def test_write_action_requires_approval(self):
        engine = make_engine(mode=PolicyMode.APPROVAL_REQUIRED)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is True


class TestReadOnlyMode:
    def test_read_action_allowed(self):
        engine = make_engine(mode=PolicyMode.READ_ONLY)
        result = engine.check("kubectl:get_pods", action_meta={"type": "read"})
        assert result.allowed is True
        assert result.requires_approval is False

    def test_write_action_blocked(self):
        engine = make_engine(mode=PolicyMode.READ_ONLY)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is False
        assert "write operation" in result.reason

    def test_unknown_type_defaults_to_read(self):
        engine = make_engine(mode=PolicyMode.READ_ONLY)
        result = engine.check("kubectl:get_pods", action_meta={})
        assert result.allowed is True


# --- Allowed actions ---


class TestAllowedActions:
    def test_action_in_whitelist_allowed(self):
        engine = make_engine(allowed_actions=["kubectl:get_pods", "kubectl:get_logs"])
        result = engine.check("kubectl:get_pods")
        assert result.allowed is True

    def test_action_not_in_whitelist_denied(self):
        engine = make_engine(allowed_actions=["kubectl:get_pods"])
        result = engine.check("kubectl:delete_pod")
        assert result.allowed is False
        assert "not in allowed_actions" in result.reason

    def test_empty_whitelist_allows_all(self):
        engine = make_engine(allowed_actions=[])
        result = engine.check("kubectl:anything")
        assert result.allowed is True

    def test_namespaced_format_required(self):
        engine = make_engine(allowed_actions=["kubectl:get_pods"])
        result = engine.check("get_pods")
        assert result.allowed is False


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
            "kubectl:exec",
            params={"command": "exec pod -- rm -rf /"},
        )
        assert result.allowed is False

    def test_regex_pattern(self):
        engine = make_engine(denied_patterns=[r"namespace\s*=\s*prod.*"])
        result = engine.check(
            "kubectl:get_pods",
            params={"command": "get pods namespace=production"},
        )
        assert result.allowed is False

    def test_no_params_skips_check(self):
        engine = make_engine(denied_patterns=[r"--force"])
        result = engine.check("kubectl:get_pods")
        assert result.allowed is True


# --- Write actions in non-autonomous modes ---


class TestWriteApprovalEscalation:
    def test_write_in_read_only_blocked(self):
        engine = make_engine(mode=PolicyMode.READ_ONLY)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is False

    def test_write_in_approval_required_needs_approval(self):
        engine = make_engine(mode=PolicyMode.APPROVAL_REQUIRED)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is True

    def test_write_in_autonomous_no_approval(self):
        engine = make_engine(mode=PolicyMode.AUTONOMOUS)
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is True
        assert result.requires_approval is False


# --- Check order of evaluation ---


class TestCheckOrder:
    def test_max_actions_checked_before_allowed_actions(self):
        engine = make_engine(
            allowed_actions=["kubectl:get_pods"],
            max_actions=0,
        )
        result = engine.check("kubectl:get_pods")
        assert result.allowed is False
        assert "Max actions" in result.reason

    def test_allowed_actions_checked_before_mode(self):
        engine = make_engine(
            mode=PolicyMode.READ_ONLY,
            allowed_actions=["kubectl:get_pods"],
        )
        result = engine.check("kubectl:delete_pod", action_meta={"type": "write"})
        assert result.allowed is False
        assert "not in allowed_actions" in result.reason
