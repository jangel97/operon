from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from operon_tool_github import GitHubTool


@pytest.fixture
def tool():
    return GitHubTool()


class TestGitHubToolBasics:
    def test_name(self, tool):
        assert tool.name == "github"

    def test_action_count(self, tool):
        assert len(tool.actions()) == 15

    def test_all_actions_have_required_fields(self, tool):
        for action in tool.actions():
            assert "name" in action
            assert "type" in action
            assert "description" in action
            assert "params" in action

    def test_read_write_split(self, tool):
        actions = tool.actions()
        read_actions = [a for a in actions if a["type"] == "read"]
        write_actions = [a for a in actions if a["type"] == "write"]
        assert len(read_actions) == 7
        assert len(write_actions) == 8

    def test_action_names(self, tool):
        names = [a["name"] for a in tool.actions()]
        assert "list_issues" in names
        assert "get_issue" in names
        assert "list_prs" in names
        assert "get_pr" in names
        assert "create_issue" in names
        assert "merge_pr" in names
        assert "add_label" in names


class TestGitHubToolValidation:
    def test_unknown_action(self, tool):
        result = tool.execute("nonexistent", {})
        assert "Unknown operation" in result

    def test_missing_required_param(self, tool):
        result = tool.execute("list_issues", {})
        assert "missing required parameter" in result
        assert "repo" in result

    def test_missing_required_number(self, tool):
        result = tool.execute("get_issue", {"repo": "owner/repo"})
        assert "missing required parameter" in result
        assert "number" in result

    def test_invalid_merge_method(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                result = tool.execute("merge_pr", {
                    "repo": "owner/repo",
                    "number": "1",
                    "method": "invalid",
                })
                assert "invalid merge method" in result
                mock_run.assert_not_called()


class TestGitHubToolExecution:
    def test_gh_not_found(self, tool):
        with patch("shutil.which", return_value=None):
            result = tool.execute("list_issues", {"repo": "owner/repo"})
            assert "gh CLI not found" in result

    def test_list_issues_builds_correct_command(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="[]", stderr=""
                )
                tool.execute("list_issues", {"repo": "owner/repo"})
                args = mock_run.call_args[0][0]
                assert args[0] == "/usr/bin/gh"
                assert "issue" in args
                assert "list" in args
                assert "--repo" in args
                assert "owner/repo" in args
                assert "--state" in args
                assert "open" in args

    def test_list_issues_with_label(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="[]", stderr=""
                )
                tool.execute("list_issues", {
                    "repo": "owner/repo",
                    "label": "bug",
                })
                args = mock_run.call_args[0][0]
                assert "--label" in args
                assert "bug" in args

    def test_create_issue_with_body_and_label(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="https://github.com/owner/repo/issues/1", stderr=""
                )
                tool.execute("create_issue", {
                    "repo": "owner/repo",
                    "title": "Bug found",
                    "body": "Description here",
                    "label": "bug",
                })
                args = mock_run.call_args[0][0]
                assert "--title" in args
                assert "Bug found" in args
                assert "--body" in args
                assert "Description here" in args
                assert "--label" in args
                assert "bug" in args

    def test_create_issue_without_optional_params(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="https://github.com/owner/repo/issues/1", stderr=""
                )
                tool.execute("create_issue", {
                    "repo": "owner/repo",
                    "title": "Bug found",
                })
                args = mock_run.call_args[0][0]
                assert "--title" in args
                assert "--body" not in args
                assert "--label" not in args

    def test_merge_pr_default_method(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="Merged", stderr=""
                )
                tool.execute("merge_pr", {
                    "repo": "owner/repo",
                    "number": "42",
                })
                args = mock_run.call_args[0][0]
                assert "--merge" in args

    def test_merge_pr_squash(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="Merged", stderr=""
                )
                tool.execute("merge_pr", {
                    "repo": "owner/repo",
                    "number": "42",
                    "method": "squash",
                })
                args = mock_run.call_args[0][0]
                assert "--squash" in args
                assert "--merge" not in args

    def test_error_output(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout="", stderr="Not Found"
                )
                result = tool.execute("get_issue", {
                    "repo": "owner/repo",
                    "number": "999",
                })
                assert "Error (exit 1)" in result
                assert "Not Found" in result

    def test_timeout_handling(self, tool):
        import subprocess
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 30)):
                result = tool.execute("list_issues", {"repo": "owner/repo"})
                assert "timed out" in result

    def test_empty_output(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="", stderr=""
                )
                result = tool.execute("close_issue", {
                    "repo": "owner/repo",
                    "number": "1",
                })
                assert result == "(success, no output)"

    def test_output_truncation(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="x" * 10000, stderr=""
                )
                result = tool.execute("list_issues", {"repo": "owner/repo"})
                assert len(result) < 10000
                assert "truncated" in result


class TestGitHubToolCoerce:
    def test_integer_coercion(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="[]", stderr=""
                )
                tool.execute("list_issues", {
                    "repo": "owner/repo",
                    "limit": "20",
                })
                args = mock_run.call_args[0][0]
                assert "20" in args

    def test_bad_integer_uses_default(self, tool):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="[]", stderr=""
                )
                tool.execute("list_issues", {
                    "repo": "owner/repo",
                    "limit": "not-a-number",
                })
                args = mock_run.call_args[0][0]
                assert "10" in args


class TestGitHubToolRegistry:
    def test_registers_in_tool_registry(self):
        from operon.tools.base import ToolRegistry

        registry = ToolRegistry()
        registry.register(GitHubTool())
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "github:list_issues" in names
        assert "github:create_issue" in names
        assert "github:merge_pr" in names

    def test_execute_routes_correctly(self):
        from operon.tools.base import ToolRegistry

        registry = ToolRegistry()
        registry.register(GitHubTool())

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="[]", stderr=""
                )
                result = registry.execute("github:list_issues", {"repo": "owner/repo"})
                assert result == "[]"
