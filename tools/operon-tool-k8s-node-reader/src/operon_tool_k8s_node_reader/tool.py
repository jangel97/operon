from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_nodes": {
        "type": "read",
        "description": "List cluster nodes and their status (returns JSON)",
        "params": {},
        "command": ["get", "nodes", "-o", "json"],
    },
    "top_nodes": {
        "type": "read",
        "description": "Show CPU/memory usage of nodes",
        "params": {},
        "command": ["top", "nodes"],
    },
}


class K8sNodeReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-node-reader"
