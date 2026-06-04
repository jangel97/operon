from __future__ import annotations

import re
from dataclasses import dataclass

from operon.agent.spec import ApprovalMode, PolicySpec
from operon.tools.base import ToolRegistry


@dataclass
class PolicyResult:
    allowed: bool
    requires_approval: bool = False
    reason: str = ""


class PolicyEngine:
    def __init__(self, policy: PolicySpec, tool_registry: ToolRegistry) -> None:
        self.policy = policy
        self.tool_registry = tool_registry
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

        if params and self._denied_re:
            command = params.get("command", "")
            for pattern in self._denied_re:
                if pattern.search(command):
                    return PolicyResult(
                        allowed=False,
                        reason=f"Command matches denied pattern: {pattern.pattern}",
                    )

        action_type = (action_meta or {}).get("type", "read")
        explicit_approval = self.tool_registry.get_approval(action)

        if explicit_approval is not None:
            requires_approval = explicit_approval == ApprovalMode.REQUIRED
        else:
            requires_approval = action_type == "write"

        return PolicyResult(allowed=True, requires_approval=requires_approval)

    def record_action(self) -> None:
        self.action_count += 1
