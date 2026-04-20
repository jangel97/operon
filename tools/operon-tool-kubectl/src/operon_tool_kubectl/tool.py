from __future__ import annotations

import shutil
import subprocess

from operon.tools.base import Tool

MAX_OUTPUT_CHARS = 5000

OPERATIONS: dict[str, dict] = {
    # --- Read operations ---
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
    "get_events": {
        "type": "read",
        "description": "Get events in a namespace, sorted by time (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "events", "-n", "{namespace}", "--sort-by=.lastTimestamp", "-o", "json"],
    },
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
    "get_services": {
        "type": "read",
        "description": "List services in a namespace (returns JSON)",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["get", "services", "-n", "{namespace}", "-o", "json"],
    },
    "get_nodes": {
        "type": "read",
        "description": "List cluster nodes and their status (returns JSON)",
        "params": {},
        "command": ["get", "nodes", "-o", "json"],
    },
    "get_namespaces": {
        "type": "read",
        "description": "List all namespaces (returns JSON)",
        "params": {},
        "command": ["get", "namespaces", "-o", "json"],
    },
    "top_pods": {
        "type": "read",
        "description": "Show CPU/memory usage of pods",
        "params": {"namespace": {"type": "string", "default": "default"}},
        "command": ["top", "pods", "-n", "{namespace}"],
    },
    "top_nodes": {
        "type": "read",
        "description": "Show CPU/memory usage of nodes",
        "params": {},
        "command": ["top", "nodes"],
    },
    # --- Write operations (never exposed by default) ---
    "rollout_restart": {
        "type": "write",
        "description": "Restart a deployment by triggering a rolling update",
        "params": {
            "name": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "default"},
        },
        "command": ["rollout", "restart", "deployment", "{name}", "-n", "{namespace}"],
    },
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


class KubectlTool(Tool):
    def __init__(self) -> None:
        self._ops = dict(OPERATIONS)

    @property
    def name(self) -> str:
        return "kubectl"

    def actions(self) -> list[dict]:
        return [
            {
                "name": op_name,
                "type": op["type"],
                "description": op["description"],
                "params": {
                    k: v["type"] + (f" (default: {v['default']})" if "default" in v else "")
                    for k, v in op["params"].items()
                },
            }
            for op_name, op in self._ops.items()
        ]

    def execute(self, action: str, params: dict) -> str:
        op = self._ops.get(action)
        if not op:
            return f"Unknown operation: {action}"

        error = self._validate_params(op, params)
        if error:
            return error

        kubectl = shutil.which("kubectl")
        if not kubectl:
            return "Error: kubectl not found in PATH"

        resolved = {}
        for k, schema in op["params"].items():
            value = params.get(k) or schema.get("default")
            if value is not None:
                resolved[k] = _coerce(value, schema)

        cmd_args = [arg.format(**resolved) for arg in op["command"]]

        if action == "get_logs" and params.get("container"):
            cmd_args.extend(["-c", str(params["container"])])

        try:
            result = subprocess.run(
                [kubectl, *cmd_args],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return f"Error: {action} timed out after 30s"

        if result.returncode != 0:
            stderr = result.stderr.strip()
            return f"Error (exit {result.returncode}):\n{stderr}"

        output = result.stdout.strip()
        if not output:
            return "(no output)"

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n\n...(truncated)"

        return output

    def _validate_params(self, op: dict, params: dict) -> str | None:
        for param_name, schema in op["params"].items():
            if schema.get("required") and not params.get(param_name):
                return f"Error: missing required parameter '{param_name}'"
        return None


def _coerce(value: object, schema: dict) -> str:
    if schema["type"] == "integer":
        return str(int(value))
    return str(value)
