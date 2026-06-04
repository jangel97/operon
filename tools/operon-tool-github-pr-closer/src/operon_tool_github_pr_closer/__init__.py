from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubPrCloserTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-pr-closer"
