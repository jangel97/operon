from __future__ import annotations

import shutil
import subprocess

from operon.tools.base import Tool

MAX_OUTPUT_CHARS = 8000

OPERATIONS: dict[str, dict] = {
    # --- Read operations ---
    "list_issues": {
        "type": "read",
        "description": "List issues in a repository",
        "params": {
            "repo": {"type": "string", "required": True},
            "state": {"type": "string", "default": "open"},
            "limit": {"type": "integer", "default": "10"},
            "label": {"type": "string"},
        },
        "command": [
            "issue", "list",
            "--repo", "{repo}",
            "--state", "{state}",
            "--limit", "{limit}",
            "--json", "number,title,state,author,labels,createdAt",
        ],
    },
    "get_issue": {
        "type": "read",
        "description": "Get details of a specific issue including comments",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
        },
        "command": [
            "issue", "view", "{number}",
            "--repo", "{repo}",
            "--json", "number,title,state,body,author,labels,comments,createdAt",
        ],
    },
    "list_prs": {
        "type": "read",
        "description": "List pull requests in a repository",
        "params": {
            "repo": {"type": "string", "required": True},
            "state": {"type": "string", "default": "open"},
            "limit": {"type": "integer", "default": "10"},
        },
        "command": [
            "pr", "list",
            "--repo", "{repo}",
            "--state", "{state}",
            "--limit", "{limit}",
            "--json", "number,title,state,author,headRefName,createdAt",
        ],
    },
    "get_pr": {
        "type": "read",
        "description": "Get details of a specific pull request",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
        },
        "command": [
            "pr", "view", "{number}",
            "--repo", "{repo}",
            "--json", "number,title,state,body,author,headRefName,baseRefName,mergeable,reviews,createdAt",
        ],
    },
    "list_releases": {
        "type": "read",
        "description": "List releases in a repository",
        "params": {
            "repo": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": "5"},
        },
        "command": [
            "release", "list",
            "--repo", "{repo}",
            "--limit", "{limit}",
        ],
    },
    "list_workflow_runs": {
        "type": "read",
        "description": "List recent CI/CD workflow runs",
        "params": {
            "repo": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": "10"},
        },
        "command": [
            "run", "list",
            "--repo", "{repo}",
            "--limit", "{limit}",
            "--json", "databaseId,name,status,conclusion,headBranch,createdAt",
        ],
    },
    "get_workflow_run": {
        "type": "read",
        "description": "Get details of a specific workflow run",
        "params": {
            "repo": {"type": "string", "required": True},
            "run_id": {"type": "string", "required": True},
        },
        "command": [
            "run", "view", "{run_id}",
            "--repo", "{repo}",
        ],
    },
    # --- Write operations ---
    "create_issue": {
        "type": "write",
        "description": "Create a new issue in a repository",
        "params": {
            "repo": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "body": {"type": "string"},
            "label": {"type": "string"},
        },
        "command": [
            "issue", "create",
            "--repo", "{repo}",
            "--title", "{title}",
        ],
    },
    "close_issue": {
        "type": "write",
        "description": "Close an issue",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
        },
        "command": [
            "issue", "close", "{number}",
            "--repo", "{repo}",
        ],
    },
    "reopen_issue": {
        "type": "write",
        "description": "Reopen a closed issue",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
        },
        "command": [
            "issue", "reopen", "{number}",
            "--repo", "{repo}",
        ],
    },
    "comment_issue": {
        "type": "write",
        "description": "Add a comment to an issue or pull request",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
            "body": {"type": "string", "required": True},
        },
        "command": [
            "issue", "comment", "{number}",
            "--repo", "{repo}",
            "--body", "{body}",
        ],
    },
    "add_label": {
        "type": "write",
        "description": "Add a label to an issue or pull request",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
            "label": {"type": "string", "required": True},
        },
        "command": [
            "issue", "edit", "{number}",
            "--repo", "{repo}",
            "--add-label", "{label}",
        ],
    },
    "remove_label": {
        "type": "write",
        "description": "Remove a label from an issue or pull request",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
            "label": {"type": "string", "required": True},
        },
        "command": [
            "issue", "edit", "{number}",
            "--repo", "{repo}",
            "--remove-label", "{label}",
        ],
    },
    "close_pr": {
        "type": "write",
        "description": "Close a pull request without merging",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
        },
        "command": [
            "pr", "close", "{number}",
            "--repo", "{repo}",
        ],
    },
    "merge_pr": {
        "type": "write",
        "description": "Merge a pull request (method: merge, squash, or rebase)",
        "params": {
            "repo": {"type": "string", "required": True},
            "number": {"type": "integer", "required": True},
            "method": {"type": "string", "default": "merge"},
        },
        "command": [
            "pr", "merge", "{number}",
            "--repo", "{repo}",
        ],
    },
}

VALID_MERGE_METHODS = {"merge", "squash", "rebase"}


class GitHubTool(Tool):
    def __init__(self) -> None:
        self._ops = dict(OPERATIONS)

    @property
    def name(self) -> str:
        return "github"

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

        gh = shutil.which("gh")
        if not gh:
            return "Error: gh CLI not found in PATH (install: https://cli.github.com)"

        resolved = {}
        for k, schema in op["params"].items():
            value = params.get(k) or schema.get("default")
            if value is not None:
                resolved[k] = _coerce(value, schema)

        cmd_args = [arg.format(**resolved) for arg in op["command"]]

        if action == "create_issue":
            if params.get("body"):
                cmd_args.extend(["--body", str(params["body"])])
            if params.get("label"):
                cmd_args.extend(["--label", str(params["label"])])

        if action == "list_issues" and params.get("label"):
            cmd_args.extend(["--label", str(params["label"])])

        if action == "merge_pr":
            method = str(params.get("method", "merge")).lower()
            if method not in VALID_MERGE_METHODS:
                return f"Error: invalid merge method '{method}' (use: merge, squash, rebase)"
            cmd_args.append(f"--{method}")

        try:
            result = subprocess.run(
                [gh, *cmd_args],
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
            return "(success, no output)"

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
        try:
            return str(int(value))
        except (ValueError, TypeError):
            return str(schema.get("default", value))
    return str(value)
