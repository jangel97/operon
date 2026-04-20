from __future__ import annotations

from operon.tools.base import Tool


class MockKubernetesTool(Tool):
    @property
    def name(self) -> str:
        return "kubernetes"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "list_pods",
                "description": "List pods in a namespace with their status",
                "params": {"namespace": "string"},
            },
            {
                "name": "restart_pod",
                "description": "Restart a specific pod by deleting it (the controller recreates it)",
                "params": {"name": "string", "namespace": "string"},
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        if action == "list_pods":
            ns = params.get("namespace", "default")
            return (
                f"Pods in namespace '{ns}':\n"
                "  NAME              STATUS              RESTARTS\n"
                "  pod-api-1         Running              0\n"
                "  pod-api-2         CrashLoopBackOff     5\n"
                "  pod-worker-1      Running              0\n"
                "  pod-db-0          Running              0"
            )

        if action == "restart_pod":
            name = params.get("name", "unknown")
            ns = params.get("namespace", "default")
            return f"Pod '{name}' in namespace '{ns}' deleted. Controller is recreating it."

        return f"Unknown action: {action}"
