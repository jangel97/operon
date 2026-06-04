from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubIssueReaderTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-issue-reader"

    def _extra_args(self, action: str, params: dict) -> list[str]:
        if action == "list_issues" and params.get("label"):
            return ["--label", str(params["label"])]
        return []
