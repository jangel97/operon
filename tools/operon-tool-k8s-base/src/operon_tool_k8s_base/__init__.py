from __future__ import annotations

import shutil
import subprocess

from operon.tools.base import Tool

MAX_OUTPUT_CHARS = 5000


class KubectlBase(Tool):
    OPERATIONS: dict[str, dict] = {}

    def __init__(self) -> None:
        self._ops = dict(self.OPERATIONS)

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
