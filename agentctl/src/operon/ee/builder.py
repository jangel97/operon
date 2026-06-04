from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from operon.ee.spec import EEDefinition

_GO_BUILDER_IMAGE = "golang:1.23"
_MODULES_TARGET = "/usr/lib/operon/modules"


def generate_containerfile(ee: EEDefinition) -> str:
    lines: list[str] = []
    has_golang = bool(ee.dependencies.golang)

    if has_golang:
        lines.append(f"FROM {_GO_BUILDER_IMAGE} AS go-builder")
        for pkg in ee.dependencies.golang:
            lines.append(f"RUN go install {pkg}")
        lines.append("")

    lines.append(f"FROM {ee.build.base_image}")
    lines.append("")

    if ee.dependencies.system:
        parts = " \\\n    ".join(ee.dependencies.system)
        lines.append(
            "RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            f"    {parts} \\\n"
            "    && rm -rf /var/lib/apt/lists/*"
        )
        lines.append("")

    if has_golang:
        lines.append("COPY --from=go-builder /go/bin/ /usr/local/bin/")
        lines.append("")

    lines.append("RUN pip install --no-cache-dir agentctl")
    lines.append("")

    tool_pkgs = [f"operon-tool-{t}" for t in ee.dependencies.tools]
    coll_pkgs = [f"operon-collection-{c}" for c in ee.dependencies.collections]
    all_operon = tool_pkgs + coll_pkgs
    if all_operon:
        parts = " \\\n    ".join(all_operon)
        lines.append(f"RUN pip install --no-cache-dir \\\n    {parts}")
        lines.append("")

    if ee.dependencies.python:
        parts = " \\\n    ".join(f'"{p}"' for p in ee.dependencies.python)
        lines.append(f"RUN pip install --no-cache-dir \\\n    {parts}")
        lines.append("")

    if ee.dependencies.modules:
        lines.append(f"RUN mkdir -p {_MODULES_TARGET}")
        for mod in ee.dependencies.modules:
            dir_name = Path(mod.path).name
            lines.append(f"COPY modules/{dir_name} {_MODULES_TARGET}/{dir_name}")
        lines.append("")

    lines.append('ENTRYPOINT ["agentctl"]')
    lines.append("")

    return "\n".join(lines)


def build_image(
    ee: EEDefinition,
    tag: str,
    runtime: str = "docker",
    context_dir: Path | None = None,
) -> int:
    containerfile = generate_containerfile(ee)
    tmp = tempfile.mkdtemp(prefix="operon-ee-")
    try:
        cf_path = Path(tmp) / "Containerfile"
        cf_path.write_text(containerfile)

        if ee.dependencies.modules:
            modules_staging = Path(tmp) / "modules"
            modules_staging.mkdir()
            base = context_dir or Path.cwd()
            for mod in ee.dependencies.modules:
                src = (base / mod.path).resolve()
                if not src.is_dir():
                    raise FileNotFoundError(f"Module directory not found: {mod.path}")
                shutil.copytree(src, modules_staging / src.name)

        result = subprocess.run(
            [runtime, "build", "-t", tag, "-f", "Containerfile", "."],
            cwd=tmp,
        )
        return result.returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
