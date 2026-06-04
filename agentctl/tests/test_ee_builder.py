from __future__ import annotations

from unittest.mock import MagicMock, patch

from operon.ee.builder import generate_containerfile
from operon.ee.spec import EEDefinition


class TestMinimalContainerfile:
    def test_has_from(self):
        ee = EEDefinition()
        cf = generate_containerfile(ee)
        assert cf.startswith("FROM python:3.12-slim")

    def test_installs_agentctl(self):
        ee = EEDefinition()
        cf = generate_containerfile(ee)
        assert "pip install --no-cache-dir agentctl" in cf

    def test_has_entrypoint(self):
        ee = EEDefinition()
        cf = generate_containerfile(ee)
        assert 'ENTRYPOINT ["agentctl"]' in cf

    def test_no_apt_when_no_system(self):
        ee = EEDefinition()
        cf = generate_containerfile(ee)
        assert "apt-get" not in cf

    def test_no_go_stage_when_no_golang(self):
        ee = EEDefinition()
        cf = generate_containerfile(ee)
        assert "go-builder" not in cf


class TestSystemPackages:
    def test_apt_get_block(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"system": ["curl", "jq"]},
        })
        cf = generate_containerfile(ee)
        assert "apt-get update" in cf
        assert "curl" in cf
        assert "jq" in cf
        assert "rm -rf /var/lib/apt/lists/*" in cf


class TestToolPackages:
    def test_tools_prefixed(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"tools": ["k8s-pod-reader"]},
        })
        cf = generate_containerfile(ee)
        assert "operon-tool-k8s-pod-reader" in cf

    def test_collections_prefixed(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"collections": ["k8s-readonly"]},
        })
        cf = generate_containerfile(ee)
        assert "operon-collection-k8s-readonly" in cf

    def test_tools_and_collections_combined(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "tools": ["k8s-pod-reader"],
                "collections": ["github-triage"],
            },
        })
        cf = generate_containerfile(ee)
        assert "operon-tool-k8s-pod-reader" in cf
        assert "operon-collection-github-triage" in cf


class TestPythonDeps:
    def test_python_deps_quoted(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"python": ["requests>=2.31"]},
        })
        cf = generate_containerfile(ee)
        assert '"requests>=2.31"' in cf

    def test_no_python_block_when_empty(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"tools": ["k8s-pod-reader"]},
        })
        cf = generate_containerfile(ee)
        lines = cf.split("\n")
        pip_lines = [l for l in lines if "pip install" in l]
        assert not any('"' in l for l in pip_lines if "agentctl" not in l and "operon-" not in l)


class TestGolangDeps:
    def test_go_builder_stage(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "golang": ["github.com/someone/tool@latest"],
            },
        })
        cf = generate_containerfile(ee)
        assert "FROM golang:" in cf
        assert "AS go-builder" in cf

    def test_go_install_commands(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "golang": [
                    "github.com/org/tool-a@latest",
                    "github.com/org/tool-b@v1.0",
                ],
            },
        })
        cf = generate_containerfile(ee)
        assert "go install github.com/org/tool-a@latest" in cf
        assert "go install github.com/org/tool-b@v1.0" in cf

    def test_copy_go_binaries(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "golang": ["github.com/someone/tool@latest"],
            },
        })
        cf = generate_containerfile(ee)
        assert "COPY --from=go-builder /go/bin/ /usr/local/bin/" in cf

    def test_no_go_stage_without_golang(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"tools": ["k8s-pod-reader"]},
        })
        cf = generate_containerfile(ee)
        assert "go-builder" not in cf
        assert "golang:" not in cf


class TestCustomBaseImage:
    def test_custom_image_in_from(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "build": {"base_image": "registry.example.com/base:v1"},
        })
        cf = generate_containerfile(ee)
        assert "FROM registry.example.com/base:v1" in cf


class TestFullContainerfile:
    def test_section_order(self):
        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {
                "tools": ["k8s-pod-reader"],
                "collections": ["github-triage"],
                "python": ["requests>=2.31"],
                "golang": ["github.com/org/tool@latest"],
                "system": ["curl"],
            },
        })
        cf = generate_containerfile(ee)
        go_pos = cf.index("go-builder")
        apt_pos = cf.index("apt-get")
        copy_pos = cf.index("COPY --from=go-builder")
        agentctl_pos = cf.index("agentctl")
        operon_tool_pos = cf.index("operon-tool-")
        requests_pos = cf.index("requests")
        entrypoint_pos = cf.index("ENTRYPOINT")

        assert go_pos < apt_pos
        assert apt_pos < copy_pos
        assert copy_pos < agentctl_pos
        assert agentctl_pos < operon_tool_pos
        assert operon_tool_pos < requests_pos
        assert requests_pos < entrypoint_pos


class TestBuildImage:
    def test_invokes_runtime(self):
        from operon.ee.builder import build_image

        ee = EEDefinition()
        with patch("operon.ee.builder.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            code = build_image(ee, tag="test:latest", runtime="docker")
            assert code == 0
            args = mock_run.call_args[0][0]
            assert args[0] == "docker"
            assert "build" in args
            assert "-t" in args
            assert "test:latest" in args

    def test_podman_runtime(self):
        from operon.ee.builder import build_image

        ee = EEDefinition()
        with patch("operon.ee.builder.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            build_image(ee, tag="test:latest", runtime="podman")
            args = mock_run.call_args[0][0]
            assert args[0] == "podman"

    def test_returns_exit_code(self):
        from operon.ee.builder import build_image

        ee = EEDefinition()
        with patch("operon.ee.builder.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            code = build_image(ee, tag="test:latest")
            assert code == 1

    def test_writes_containerfile(self):
        from operon.ee.builder import build_image

        ee = EEDefinition.model_validate({
            "version": 1,
            "dependencies": {"tools": ["k8s-pod-reader"]},
        })
        written_content = {}

        def capture_run(cmd, **kwargs):
            from pathlib import Path
            cwd = kwargs.get("cwd", ".")
            cf = Path(cwd) / "Containerfile"
            if cf.exists():
                written_content["containerfile"] = cf.read_text()
            return MagicMock(returncode=0)

        with patch("operon.ee.builder.subprocess.run", side_effect=capture_run):
            build_image(ee, tag="test:latest")

        assert "operon-tool-k8s-pod-reader" in written_content["containerfile"]
