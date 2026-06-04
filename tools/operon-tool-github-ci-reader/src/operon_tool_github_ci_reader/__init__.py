from __future__ import annotations

from operon_tool_github_base import GhBase


class GitHubCiReaderTool(GhBase):
    OPERATIONS = {
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
    }

    @property
    def name(self) -> str:
        return "github-ci-reader"
