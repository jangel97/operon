from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_logs": {
        "type": "read",
        "description": "Get logs from a pod (optionally a specific container)",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
            "container": {"type": "string"},
            "tail": {"type": "integer", "default": "100"},
        },
        "command": ["logs", "{name}", "-n", "{namespace}", "--tail={tail}"],
    },
}


class K8sLogReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-log-reader"
