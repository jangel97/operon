from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_namespaces": {
        "type": "read",
        "description": "List all namespaces (returns JSON)",
        "params": {},
        "command": ["get", "namespaces", "-o", "json"],
    },
}


class K8sNamespaceReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-namespace-reader"
