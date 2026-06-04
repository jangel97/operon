from __future__ import annotations

import json
import subprocess as sp
from unittest.mock import MagicMock, patch

import pytest

from operon.modules.loader import (
    GolangModuleAdapter,
    PythonModuleAdapter,
    create_module_tool,
    discover_modules,
)
from operon.modules.spec import ModuleRuntime, ModuleSpec
from operon.tools.base import ToolRegistry


def _make_spec(
    name: str = "test-tool",
    runtime: str = "python",
    entrypoint: str = "main.py",
    actions: list | None = None,
) -> ModuleSpec:
    if actions is None:
        actions = [{"name": "do_it", "type": "read", "description": "Does it"}]
    return ModuleSpec.model_validate({
        "name": name,
        "runtime": runtime,
        "entrypoint": entrypoint,
        "actions": actions,
    })


class TestDiscoverModules:
    def test_empty_dir(self, tmp_path):
        result = discover_modules(tmp_path)
        assert result == {}

    def test_nonexistent_dir(self, tmp_path):
        result = discover_modules(tmp_path / "missing")
        assert result == {}

    def test_discovers_module(self, tmp_path):
        mod_dir = tmp_path / "my-tool"
        mod_dir.mkdir()
        (mod_dir / "tool.yaml").write_text(
            "name: my-tool\n"
            "runtime: python\n"
            "entrypoint: main.py\n"
            "actions:\n"
            "  - name: act\n"
            "    type: read\n"
            "    description: does stuff\n"
        )
        (mod_dir / "main.py").write_text("def execute(action, params): return 'ok'")
        result = discover_modules(tmp_path)
        assert "my-tool" in result
        spec, path = result["my-tool"]
        assert spec.name == "my-tool"
        assert path == mod_dir

    def test_skips_dir_without_manifest(self, tmp_path):
        (tmp_path / "no-manifest").mkdir()
        result = discover_modules(tmp_path)
        assert result == {}

    def test_skips_invalid_manifest(self, tmp_path):
        mod_dir = tmp_path / "bad"
        mod_dir.mkdir()
        (mod_dir / "tool.yaml").write_text("not: valid: [tool spec")
        result = discover_modules(tmp_path)
        assert result == {}

    def test_multiple_modules(self, tmp_path):
        for name in ["tool-a", "tool-b"]:
            d = tmp_path / name
            d.mkdir()
            (d / "tool.yaml").write_text(
                f"name: {name}\nruntime: python\nentrypoint: main.py\n"
                f"actions:\n  - name: act\n    type: read\n    description: x\n"
            )
        result = discover_modules(tmp_path)
        assert "tool-a" in result
        assert "tool-b" in result


class TestPythonModuleAdapter:
    def test_name(self):
        spec = _make_spec(name="my-tool")
        adapter = PythonModuleAdapter(spec, module_dir=MagicMock())
        assert adapter.name == "my-tool"

    def test_actions_format(self):
        spec = _make_spec(actions=[
            {
                "name": "get_stuff",
                "type": "read",
                "description": "Gets stuff",
                "params": {"ns": {"type": "string", "default": "default"}},
            },
        ])
        adapter = PythonModuleAdapter(spec, module_dir=MagicMock())
        actions = adapter.actions()
        assert len(actions) == 1
        assert actions[0]["name"] == "get_stuff"
        assert actions[0]["type"] == "read"
        assert "default" in actions[0]["params"]["ns"]

    def test_execute_calls_module(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "def execute(action, params):\n"
            "    return f'ran {action}'\n"
        )
        spec = _make_spec()
        adapter = PythonModuleAdapter(spec, module_dir=tmp_path)
        result = adapter.execute("do_it", {})
        assert result == "ran do_it"

    def test_execute_passes_params(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "def execute(action, params):\n"
            "    return params.get('name', 'none')\n"
        )
        spec = _make_spec()
        adapter = PythonModuleAdapter(spec, module_dir=tmp_path)
        result = adapter.execute("do_it", {"name": "world"})
        assert result == "world"

    def test_execute_unknown_action(self, tmp_path):
        (tmp_path / "main.py").write_text("def execute(a, p): return 'ok'")
        spec = _make_spec()
        adapter = PythonModuleAdapter(spec, module_dir=tmp_path)
        result = adapter.execute("nonexistent", {})
        assert "Unknown action" in result

    def test_missing_execute_function(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        spec = _make_spec()
        adapter = PythonModuleAdapter(spec, module_dir=tmp_path)
        with pytest.raises(AttributeError, match="execute"):
            adapter.execute("do_it", {})

    def test_registry_integration(self, tmp_path):
        (tmp_path / "main.py").write_text("def execute(a, p): return 'ok'")
        spec = _make_spec(name="my-mod")
        adapter = PythonModuleAdapter(spec, module_dir=tmp_path)
        registry = ToolRegistry()
        registry.register(adapter)
        actions = registry.get_actions()
        names = [a["name"] for a in actions]
        assert "my-mod:do_it" in names
        result = registry.execute("my-mod:do_it", {})
        assert result == "ok"


class TestGolangModuleAdapter:
    def test_name(self):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=MagicMock())
        assert adapter.name == "go-tool"

    def test_execute_sends_json(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)

        with patch("operon.modules.loader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"result": "pods listed"}',
                stderr="",
            )
            result = adapter.execute("do_it", {"ns": "kube-system"})
            assert result == "pods listed"
            call_kwargs = mock_run.call_args
            stdin_data = json.loads(call_kwargs.kwargs.get("input", call_kwargs[1].get("input", "")))
            assert stdin_data["action"] == "do_it"
            assert stdin_data["params"]["ns"] == "kube-system"

    def test_execute_error_response(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)

        with patch("operon.modules.loader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"error": "namespace not found"}',
                stderr="",
            )
            result = adapter.execute("do_it", {})
            assert "namespace not found" in result

    def test_execute_nonzero_exit(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)

        with patch("operon.modules.loader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="segfault",
            )
            result = adapter.execute("do_it", {})
            assert "Error" in result
            assert "segfault" in result

    def test_execute_timeout(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)

        with patch("operon.modules.loader.subprocess.run", side_effect=sp.TimeoutExpired("cmd", 30)):
            result = adapter.execute("do_it", {})
            assert "timed out" in result

    def test_execute_unknown_action(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)
        result = adapter.execute("nonexistent", {})
        assert "Unknown action" in result

    def test_execute_binary_not_found(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./nonexistent")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)
        result = adapter.execute("do_it", {})
        assert "not found" in result

    def test_non_json_stdout_fallback(self, tmp_path):
        spec = _make_spec(name="go-tool", runtime="golang", entrypoint="./main")
        adapter = GolangModuleAdapter(spec, module_dir=tmp_path)

        with patch("operon.modules.loader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="plain text output", stderr="",
            )
            result = adapter.execute("do_it", {})
            assert result == "plain text output"


class TestCreateModuleTool:
    def test_python_adapter(self, tmp_path):
        spec = _make_spec(runtime="python")
        tool = create_module_tool(spec, tmp_path)
        assert isinstance(tool, PythonModuleAdapter)

    def test_golang_adapter(self, tmp_path):
        spec = _make_spec(runtime="golang", entrypoint="./main")
        tool = create_module_tool(spec, tmp_path)
        assert isinstance(tool, GolangModuleAdapter)
