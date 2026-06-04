from __future__ import annotations

import pytest

from operon.modules.spec import ModuleAction, ModuleActionParam, ModuleRuntime, ModuleSpec


class TestModuleSpec:
    def test_full_spec(self):
        spec = ModuleSpec.model_validate({
            "name": "k8s-pod-reader",
            "runtime": "python",
            "entrypoint": "main.py",
            "actions": [
                {
                    "name": "get_pods",
                    "type": "read",
                    "description": "List pods",
                    "params": {
                        "namespace": {"type": "string", "default": "default"},
                    },
                },
            ],
        })
        assert spec.name == "k8s-pod-reader"
        assert spec.runtime == ModuleRuntime.PYTHON
        assert spec.entrypoint == "main.py"
        assert len(spec.actions) == 1
        assert spec.actions[0].params["namespace"].default == "default"

    def test_golang_runtime(self):
        spec = ModuleSpec.model_validate({
            "name": "custom-tool",
            "runtime": "golang",
            "entrypoint": "./main",
            "actions": [{"name": "do_thing", "type": "write", "description": "Does a thing"}],
        })
        assert spec.runtime == ModuleRuntime.GOLANG

    def test_action_defaults(self):
        action = ModuleAction.model_validate({"name": "my_action"})
        assert action.type == "read"
        assert action.description == ""
        assert action.params == {}

    def test_param_defaults(self):
        param = ModuleActionParam.model_validate({"type": "string"})
        assert param.required is False
        assert param.default is None

    def test_param_required(self):
        param = ModuleActionParam.model_validate({"type": "string", "required": True})
        assert param.required is True

    def test_invalid_runtime(self):
        with pytest.raises(Exception):
            ModuleSpec.model_validate({
                "name": "bad",
                "runtime": "rust",
                "entrypoint": "main",
                "actions": [],
            })

    def test_multiple_actions(self):
        spec = ModuleSpec.model_validate({
            "name": "multi",
            "runtime": "python",
            "entrypoint": "main.py",
            "actions": [
                {"name": "action_a", "type": "read", "description": "A"},
                {"name": "action_b", "type": "write", "description": "B"},
            ],
        })
        assert len(spec.actions) == 2
        assert spec.actions[1].type == "write"


class TestLoadModuleSpec:
    def test_load_from_file(self, tmp_path):
        manifest = tmp_path / "tool.yaml"
        manifest.write_text(
            "name: test-tool\n"
            "runtime: python\n"
            "entrypoint: main.py\n"
            "actions:\n"
            "  - name: do_it\n"
            "    type: read\n"
            "    description: Does it\n"
        )
        from operon.modules.spec import load_module_spec

        spec = load_module_spec(manifest)
        assert spec.name == "test-tool"
        assert spec.runtime == ModuleRuntime.PYTHON

    def test_load_missing_file(self, tmp_path):
        from operon.modules.spec import load_module_spec

        with pytest.raises(FileNotFoundError):
            load_module_spec(tmp_path / "missing.yaml")
