from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "get_deployments": {
        "type": "read",
        "description": "List deployments in a namespace (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "deployments", "-n", "{namespace}", "-o", "json"],
    },
    "describe_deployment": {
        "type": "read",
        "description": "Get detailed info about a specific deployment",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
        },
        "command": ["describe", "deployment", "{name}", "-n", "{namespace}"],
    },
}


class K8sDeploymentReaderTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-deployment-reader"
