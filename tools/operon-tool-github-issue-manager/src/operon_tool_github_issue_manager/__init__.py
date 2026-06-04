from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubIssueManagerTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-issue-manager"

    def _extra_args(self, action: str, params: dict) -> list[str]:
        if action == "create_issue":
            extra = []
            if params.get("body"):
                extra.extend(["--body", str(params["body"])])
            if params.get("label"):
                extra.extend(["--label", str(params["label"])])
            return extra
        return []
