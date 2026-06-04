from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from operon.modules.spec import ModuleRuntime, ModuleSpec, load_module_spec
from operon.tools.base import Tool

logger = logging.getLogger(__name__)

DEFAULT_MODULES_PATH = Path("/usr/lib/operon/modules")
MODULES_PATH_ENV = "OPERON_MODULES_PATH"
MAX_OUTPUT_CHARS = 8000
EXECUTE_TIMEOUT = 30


def get_modules_dir() -> Path:
    return Path(os.environ.get(MODULES_PATH_ENV, str(DEFAULT_MODULES_PATH)))


def discover_modules(
    modules_dir: Path | None = None,
) -> dict[str, tuple[ModuleSpec, Path]]:
    if modules_dir is None:
        modules_dir = get_modules_dir()
    if not modules_dir.is_dir():
        return {}
    specs: dict[str, tuple[ModuleSpec, Path]] = {}
    for child in sorted(modules_dir.iterdir()):
        manifest = child / "tool.yaml"
        if child.is_dir() and manifest.is_file():
            try:
                spec = load_module_spec(manifest)
                specs[spec.name] = (spec, child)
            except Exception:
                logger.warning("Failed to load module from %s", child, exc_info=True)
    return specs


class PythonModuleAdapter(Tool):
    def __init__(self, spec: ModuleSpec, module_dir: Path) -> None:
        self._spec = spec
        self._module_dir = module_dir
        self._mod: ModuleType | None = None

    def _load_module(self) -> ModuleType:
        if self._mod is not None:
            return self._mod
        entrypoint = self._module_dir / self._spec.entrypoint
        mod_name = f"operon_module_{self._spec.name.replace('-', '_')}"
        loader_spec = importlib.util.spec_from_file_location(mod_name, entrypoint)
        if loader_spec is None or loader_spec.loader is None:
            raise ImportError(f"Cannot load module from {entrypoint}")
        mod = importlib.util.module_from_spec(loader_spec)
        sys.modules[mod_name] = mod
        loader_spec.loader.exec_module(mod)
        if not hasattr(mod, "execute"):
            raise AttributeError(
                f"Module {self._spec.name} entrypoint {self._spec.entrypoint} "
                f"does not define an execute() function"
            )
        self._mod = mod
        return mod

    @property
    def name(self) -> str:
        return self._spec.name

    def actions(self) -> list[dict]:
        return _actions_from_spec(self._spec)

    def execute(self, action: str, params: dict) -> str:
        if action not in {a.name for a in self._spec.actions}:
            return f"Unknown action: {action}"
        mod = self._load_module()
        return str(mod.execute(action, params))


class GolangModuleAdapter(Tool):
    def __init__(self, spec: ModuleSpec, module_dir: Path) -> None:
        self._spec = spec
        self._module_dir = module_dir

    @property
    def name(self) -> str:
        return self._spec.name

    def actions(self) -> list[dict]:
        return _actions_from_spec(self._spec)

    def execute(self, action: str, params: dict) -> str:
        if action not in {a.name for a in self._spec.actions}:
            return f"Unknown action: {action}"

        binary = self._module_dir / self._spec.entrypoint
        request = json.dumps({"action": action, "params": params})

        try:
            result = subprocess.run(
                [str(binary)],
                input=request,
                capture_output=True,
                text=True,
                timeout=EXECUTE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"Error: {action} timed out after {EXECUTE_TIMEOUT}s"
        except FileNotFoundError:
            return f"Error: binary not found: {binary}"

        if result.returncode != 0:
            return f"Error (exit {result.returncode}):\n{result.stderr.strip()}"

        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()

        if "error" in response:
            return f"Error: {response['error']}"

        output = str(response.get("result", ""))
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n\n...(truncated)"
        return output


def _actions_from_spec(spec: ModuleSpec) -> list[dict]:
    return [
        {
            "name": action.name,
            "type": action.type,
            "description": action.description,
            "params": {
                pname: pspec.type
                + (f" (default: {pspec.default})" if pspec.default is not None else "")
                for pname, pspec in action.params.items()
            },
        }
        for action in spec.actions
    ]


def create_module_tool(spec: ModuleSpec, module_dir: Path) -> Tool:
    if spec.runtime == ModuleRuntime.PYTHON:
        return PythonModuleAdapter(spec, module_dir)
    if spec.runtime == ModuleRuntime.GOLANG:
        return GolangModuleAdapter(spec, module_dir)
    raise ValueError(f"Unsupported module runtime: {spec.runtime}")
