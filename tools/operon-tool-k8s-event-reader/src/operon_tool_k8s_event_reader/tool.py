from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_events": {
        "type": "read",
        "description": "Get events in a namespace, sorted by time (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "events", "-n", "{namespace}", "--sort-by=.lastTimestamp", "-o", "json"],
    },
}


class K8sEventReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-event-reader"
