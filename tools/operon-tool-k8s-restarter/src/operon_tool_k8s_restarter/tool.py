from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "rollout_restart": {
        "type": "write",
        "description": "Restart a deployment by triggering a rolling update",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
        },
        "command": ["rollout", "restart", "deployment", "{name}", "-n", "{namespace}"],
    },
}


class K8sRestarterTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-restarter"
