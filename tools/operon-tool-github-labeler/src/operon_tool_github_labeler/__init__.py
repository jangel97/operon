from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubLabelerTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-labeler"
