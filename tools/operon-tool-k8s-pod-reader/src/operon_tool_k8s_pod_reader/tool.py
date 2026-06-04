from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_pods": {
        "type": "read",
        "description": "List pods in a namespace (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "pods", "-n", "{namespace}", "-o", "json"],
    },
    "describe_pod": {
        "type": "read",
        "description": "Get detailed info about a specific pod",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
        },
        "command": ["describe", "pod", "{name}", "-n", "{namespace}"],
    },
    "top_pods": {
        "type": "read",
        "description": "Show CPU/memory usage of pods",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["top", "pods", "-n", "{namespace}"],
    },
}


class K8sPodReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-pod-reader"
