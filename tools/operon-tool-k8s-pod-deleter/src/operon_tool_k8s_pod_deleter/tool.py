from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "delete_pod": {
        "type": "write",
        "description": "Delete a specific pod (it will be recreated by its controller)",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
        },
        "command": ["delete", "pod", "{name}", "-n", "{namespace}"],
    },
}


class K8sPodDeleterTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-pod-deleter"
