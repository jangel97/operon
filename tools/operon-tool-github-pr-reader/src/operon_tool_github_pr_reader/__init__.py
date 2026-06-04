from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubPrReaderTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-pr-reader"
