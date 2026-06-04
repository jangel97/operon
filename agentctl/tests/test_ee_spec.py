from __future__ import annotations

import pytest

from operon.ee.spec import EEBuildOptions, EEDefinition, EEDependencies


class TestEEDefinition:
    def test_full_definition(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "build": {"base_image": "python:3.11-slim"},
            "dependencies": {
                "tools": ["k8s-pod-reader", "k8s-log-reader"],
                "collections": ["k8s-readonly"],
                "python": ["requests>=2.31"],
                "golang": ["github.com/someone/tool@latest"],
                "system": ["curl", "jq"],
            },
        })
        assert ee.version == 1
        assert ee.build.base_image == "python:3.11-slim"
        assert ee.dependencies.tools == ["k8s-pod-reader", "k8s-log-reader"]
        assert ee.dependencies.collections == ["k8s-readonly"]
        assert ee.dependencies.python == ["requests>=2.31"]
        assert ee.dependencies.golang == ["github.com/someone/tool@latest"]
        assert ee.dependencies.system == ["curl", "jq"]

    def test_minimal_definition(self):
        ee = EEDefinition.model_validate({"version": 1})
        assert ee.build.base_image == "python:3.12-slim"
        assert ee.dependencies.tools == []
        assert ee.dependencies.collections == []
        assert ee.dependencies.python == []
        assert ee.dependencies.golang == []
        assert ee.dependencies.system == []

    def test_defaults(self):
        ee = EEDefinition()
        assert ee.version == 1
        assert ee.build.base_image == "python:3.12-slim"

    def test_tools_only(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"tools": ["prometheus-reader"]},
        })
        assert ee.dependencies.tools == ["prometheus-reader"]
        assert ee.dependencies.collections == []

    def test_collections_only(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"collections": ["k8s-sre"]},
        })
        assert ee.dependencies.collections == ["k8s-sre"]
        assert ee.dependencies.tools == []

    def test_python_deps_preserved(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"python": ["requests>=2.31", "boto3~=1.28"]},
        })
        assert ee.dependencies.python == ["requests>=2.31", "boto3~=1.28"]

    def test_golang_deps(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "golang": [
                    "github.com/org/tool-a@latest",
                    "github.com/org/tool-b@v1.2.0",
                ],
            },
        })
        assert len(ee.dependencies.golang) == 2

    def test_custom_base_image(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "build": {"base_image": "registry.example.com/base:v1"},
        })
        assert ee.build.base_image == "registry.example.com/base:v1"


class TestLoadEEDefinition:
    def test_load_from_file(self, tmp_path):
        ee_file = tmp_path / "ee.yml"
        ee_file.write_text(
            "version: 1\n"
            "build:\n"
            "  base_image: python:3.12-slim\n"
            "dependencies:\n"
            "  tools:\n"
            "    - k8s-pod-reader\n"
        )
        from operon.ee.spec import load_ee_definition

        ee = load_ee_definition(ee_file)
        assert ee.dependencies.tools == ["k8s-pod-reader"]

    def test_load_missing_file(self, tmp_path):
        from operon.ee.spec import load_ee_definition

        with pytest.raises(FileNotFoundError):
            load_ee_definition(tmp_path / "missing.yml")
