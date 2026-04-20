from __future__ import annotations

from dataclasses import dataclass

from operon.agent.spec import PolicySpec


@dataclass
class PolicyResult:
    allowed: bool
    requires_approval: bool = False
    reason: str = ""


class PolicyEngine:
    def __init__(self, policy: PolicySpec) -> None:
        self.policy = policy
        self.action_count = 0

    def check(self, action: str) -> PolicyResult:
        if self.action_count >= self.policy.constraints.max_actions:
            return PolicyResult(
                allowed=False,
                reason=f"Max actions limit reached ({self.policy.constraints.max_actions})",
            )

        if self.policy.allowed_actions and action not in self.policy.allowed_actions:
            return PolicyResult(
                allowed=False,
                reason=f"Action '{action}' is not in allowed_actions: {self.policy.allowed_actions}",
            )

        requires_approval = self.policy.mode == "approval_required"

        return PolicyResult(allowed=True, requires_approval=requires_approval)

    def record_action(self) -> None:
        self.action_count += 1
