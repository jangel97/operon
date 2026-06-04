from __future__ import annotations

from operon_tool_k8s_base import KubectlBase

OPERATIONS: dict[str, dict] = {
    "scale_deployment": {
        "type": "write",
        "description": "Scale a deployment to a specific number of replicas",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
            "replicas": {"type": "integer", "required": True},
        },
        "command": ["scale", "deployment", "{name}", "-n", "{namespace}", "--replicas={replicas}"],
    },
}


class K8sScalerTool(KubectlBase):
    OPERATIONS = OPERATIONS

    @property
    def name(self) -> str:
        return "k8s-scaler"
