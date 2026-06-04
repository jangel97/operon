from __future__ import annotations

from operon_tool_github_base import GhBase

VALID_MERGE_METHODS = {"merge", "squash", "rebase"}


class GitHubPrMergerTool(GhBase):
    OPERATIONS = {
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

    @property
    def name(self) -> str:
        return "github-pr-merger"

    def execute(self, action: str, params: dict) -> str:
        if action == "merge_pr":
            method = str(params.get("method", "merge")).lower()
            if method not in VALID_MERGE_METHODS:
                return f"Error: invalid merge method '{method}' (use: merge, squash, rebase)"
        return super().execute(action, params)

    def _extra_args(self, action: str, params: dict) -> list[str]:
        if action == "merge_pr":
            method = str(params.get("method", "merge")).lower()
            return [f"--{method}"]
        return []
