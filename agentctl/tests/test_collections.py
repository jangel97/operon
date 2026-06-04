from __future__ import annotations

from unittest.mock import patch

import pytest

from operon.tools.collections import resolve_collection


def mock_requires(package_name: str):
    packages = {
        "operon-collection-k8s-readonly": [
            "operon-tool-k8s-pod-reader>=0.1.0",
            "operon-tool-k8s-log-reader>=0.1.0",
            "operon-tool-k8s-event-reader>=0.1.0",
        ],
        "operon-collection-k8s-sre": [
            "operon-collection-k8s-readonly>=0.1.0",
            "operon-tool-k8s-restarter>=0.1.0",
            "operon-tool-k8s-pod-deleter>=0.1.0",
        ],
        "operon-collection-empty": None,
        "operon-collection-with-base": [
            "operon-tool-k8s-pod-reader>=0.1.0",
            "operon-tool-k8s-base>=0.1.0",
        ],
    }
    from importlib.metadata import PackageNotFoundError
    if package_name not in packages:
        raise PackageNotFoundError(package_name)
    return packages[package_name]


class TestResolveCollection:
    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_simple_collection(self, _mock):
        tools = resolve_collection("k8s-readonly")
        assert "k8s-pod-reader" in tools
        assert "k8s-log-reader" in tools
        assert "k8s-event-reader" in tools
        assert len(tools) == 3

    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_nested_collection(self, _mock):
        tools = resolve_collection("k8s-sre")
        assert "k8s-pod-reader" in tools
        assert "k8s-log-reader" in tools
        assert "k8s-event-reader" in tools
        assert "k8s-restarter" in tools
        assert "k8s-pod-deleter" in tools
        assert len(tools) == 5

    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_collection_not_installed(self, _mock):
        with pytest.raises(ValueError, match="not installed"):
            resolve_collection("nonexistent")

    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_empty_collection(self, _mock):
        tools = resolve_collection("empty")
        assert tools == []

    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_filters_by_known_tools(self, _mock):
        known = {"k8s-pod-reader", "k8s-log-reader"}
        tools = resolve_collection("k8s-readonly", known_tools=known)
        assert "k8s-pod-reader" in tools
        assert "k8s-log-reader" in tools
        assert "k8s-event-reader" not in tools

    @patch("operon.tools.collections.requires", side_effect=mock_requires)
    def test_filters_non_tool_packages(self, _mock):
        known = {"k8s-pod-reader"}
        tools = resolve_collection("with-base", known_tools=known)
        assert tools == ["k8s-pod-reader"]
