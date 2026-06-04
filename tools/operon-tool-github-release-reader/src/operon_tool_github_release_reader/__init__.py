from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubReleaseReaderTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-release-reader"
