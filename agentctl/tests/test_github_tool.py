from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from operon.tools.base import ToolRegistry


# --- Test all fine-grained GitHub tools ---


class TestGitHubIssueReader:
    def test_name(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        assert GitHubIssueReaderTool().name == "github-issue-reader"

    def test_actions(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        actions = GitHubIssueReaderTool().actions()
        names = [a["name"] for a in actions]
        assert "list_issues" in names
        assert "get_issue" in names
        assert all(a["type"] == "read" for a in actions)

    def test_list_issues_command(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                tool.execute("list_issues", {"repo": "owner/repo"})
                args = mock_run.call_args[0][0]
                assert "issue" in args
                assert "list" in args
                assert "owner/repo" in args

    def test_list_issues_with_label(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                tool.execute("list_issues", {"repo": "owner/repo", "label": "bug"})
                args = mock_run.call_args[0][0]
                assert "--label" in args
                assert "bug" in args


class TestGitHubPrReader:
    def test_name(self):
        from operon_tool_github_pr_reader import GitHubPrReaderTool
        assert GitHubPrReaderTool().name == "github-pr-reader"

    def test_actions(self):
        from operon_tool_github_pr_reader import GitHubPrReaderTool
        actions = GitHubPrReaderTool().actions()
        names = [a["name"] for a in actions]
        assert "list_prs" in names
        assert "get_pr" in names


class TestGitHubReleaseReader:
    def test_name(self):
        from operon_tool_github_release_reader import GitHubReleaseReaderTool
        assert GitHubReleaseReaderTool().name == "github-release-reader"

    def test_actions(self):
        from operon_tool_github_release_reader import GitHubReleaseReaderTool
        actions = GitHubReleaseReaderTool().actions()
        assert len(actions) == 1
        assert actions[0]["name"] == "list_releases"


class TestGitHubCiReader:
    def test_name(self):
        from operon_tool_github_ci_reader import GitHubCiReaderTool
        assert GitHubCiReaderTool().name == "github-ci-reader"

    def test_actions(self):
        from operon_tool_github_ci_reader import GitHubCiReaderTool
        actions = GitHubCiReaderTool().actions()
        names = [a["name"] for a in actions]
        assert "list_workflow_runs" in names
        assert "get_workflow_run" in names


class TestGitHubIssueManager:
    def test_name(self):
        from operon_tool_github_issue_manager import GitHubIssueManagerTool
        assert GitHubIssueManagerTool().name == "github-issue-manager"

    def test_actions_are_write(self):
        from operon_tool_github_issue_manager import GitHubIssueManagerTool
        actions = GitHubIssueManagerTool().actions()
        assert all(a["type"] == "write" for a in actions)
        names = [a["name"] for a in actions]
        assert "create_issue" in names
        assert "close_issue" in names
        assert "reopen_issue" in names

    def test_create_issue_with_body_and_label(self):
        from operon_tool_github_issue_manager import GitHubIssueManagerTool
        tool = GitHubIssueManagerTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="created", stderr="")
                tool.execute("create_issue", {
                    "repo": "owner/repo",
                    "title": "Bug",
                    "body": "Description",
                    "label": "bug",
                })
                args = mock_run.call_args[0][0]
                assert "--body" in args
                assert "Description" in args
                assert "--label" in args
                assert "bug" in args

    def test_create_issue_without_optional_params(self):
        from operon_tool_github_issue_manager import GitHubIssueManagerTool
        tool = GitHubIssueManagerTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="created", stderr="")
                tool.execute("create_issue", {"repo": "owner/repo", "title": "Bug"})
                args = mock_run.call_args[0][0]
                assert "--body" not in args
                assert "--label" not in args


class TestGitHubLabeler:
    def test_name(self):
        from operon_tool_github_labeler import GitHubLabelerTool
        assert GitHubLabelerTool().name == "github-labeler"

    def test_actions(self):
        from operon_tool_github_labeler import GitHubLabelerTool
        actions = GitHubLabelerTool().actions()
        names = [a["name"] for a in actions]
        assert "add_label" in names
        assert "remove_label" in names


class TestGitHubCommenter:
    def test_name(self):
        from operon_tool_github_commenter import GitHubCommenterTool
        assert GitHubCommenterTool().name == "github-commenter"

    def test_actions(self):
        from operon_tool_github_commenter import GitHubCommenterTool
        actions = GitHubCommenterTool().actions()
        assert len(actions) == 1
        assert actions[0]["name"] == "comment_issue"


class TestGitHubPrCloser:
    def test_name(self):
        from operon_tool_github_pr_closer import GitHubPrCloserTool
        assert GitHubPrCloserTool().name == "github-pr-closer"


class TestGitHubPrMerger:
    def test_name(self):
        from operon_tool_github_pr_merger import GitHubPrMergerTool
        assert GitHubPrMergerTool().name == "github-pr-merger"

    def test_merge_default_method(self):
        from operon_tool_github_pr_merger import GitHubPrMergerTool
        tool = GitHubPrMergerTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="merged", stderr="")
                tool.execute("merge_pr", {"repo": "owner/repo", "number": "1"})
                args = mock_run.call_args[0][0]
                assert "--merge" in args

    def test_merge_squash(self):
        from operon_tool_github_pr_merger import GitHubPrMergerTool
        tool = GitHubPrMergerTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="merged", stderr="")
                tool.execute("merge_pr", {"repo": "owner/repo", "number": "1", "method": "squash"})
                args = mock_run.call_args[0][0]
                assert "--squash" in args

    def test_invalid_merge_method(self):
        from operon_tool_github_pr_merger import GitHubPrMergerTool
        tool = GitHubPrMergerTool()
        result = tool.execute("merge_pr", {"repo": "owner/repo", "number": "1", "method": "invalid"})
        assert "invalid merge method" in result


# --- Base behavior ---


class TestGhBase:
    def test_gh_not_found(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value=None):
            result = tool.execute("list_issues", {"repo": "owner/repo"})
            assert "gh CLI not found" in result

    def test_missing_required_param(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        result = tool.execute("list_issues", {})
        assert "missing required parameter" in result

    def test_unknown_action(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        result = tool.execute("nonexistent", {})
        assert "Unknown operation" in result

    def test_error_output(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
                result = tool.execute("list_issues", {"repo": "owner/repo"})
                assert "Error" in result
                assert "not found" in result

    def test_timeout_handling(self):
        import subprocess as sp
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", side_effect=sp.TimeoutExpired("gh", 30)):
                result = tool.execute("list_issues", {"repo": "owner/repo"})
                assert "timed out" in result

    def test_output_truncation(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        tool = GitHubIssueReaderTool()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="x" * 10000, stderr="")
                result = tool.execute("list_issues", {"repo": "owner/repo"})
                assert "truncated" in result
                assert len(result) < 10000


# --- Registry integration ---


class TestRegistryIntegration:
    def test_registers_in_tool_registry(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        registry = ToolRegistry()
        registry.register(GitHubIssueReaderTool())
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "github-issue-reader:list_issues" in names
        assert "github-issue-reader:get_issue" in names

    def test_multiple_tools_in_registry(self):
        from operon_tool_github_issue_reader import GitHubIssueReaderTool
        from operon_tool_github_pr_reader import GitHubPrReaderTool
        registry = ToolRegistry()
        registry.register(GitHubIssueReaderTool())
        registry.register(GitHubPrReaderTool())
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "github-issue-reader:list_issues" in names
        assert "github-pr-reader:list_prs" in names
