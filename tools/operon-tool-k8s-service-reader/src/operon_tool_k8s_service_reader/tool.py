from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_services": {
        "type": "read",
        "description": "List services in a namespace (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "services", "-n", "{namespace}", "-o", "json"],
    },
}


class K8sServiceReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-service-reader"
