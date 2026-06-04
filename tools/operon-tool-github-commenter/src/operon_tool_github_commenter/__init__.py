from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubCommenterTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-commenter"
