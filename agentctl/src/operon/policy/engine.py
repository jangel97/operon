from __future__ import annotations

import re
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
        self._denied_re = [
            re.compile(p) for p in self.policy.constraints.denied_patterns
        ]

    def check(
        self,
        action: str,
        params: dict | None = None,
        action_meta: dict | None = None,
    ) -> PolicyResult:
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

        action_type = (action_meta or {}).get("type", "read")

        if self.policy.mode == "read_only" and action_type == "write":
            return PolicyResult(
                allowed=False,
                reason=f"Action '{action}' is a write operation (policy mode: read_only)",
            )

        if params and self._denied_re:
            command = params.get("command", "")
            for pattern in self._denied_re:
                if pattern.search(command):
                    return PolicyResult(
                        allowed=False,
                        reason=f"Command matches denied pattern: {pattern.pattern}",
                    )

        requires_approval = self.policy.mode == "approval_required"
        if not requires_approval and action_type == "write" and self.policy.mode != "autonomous":
            requires_approval = True

        return PolicyResult(allowed=True, requires_approval=requires_approval)

    def record_action(self) -> None:
        self.action_count += 1
