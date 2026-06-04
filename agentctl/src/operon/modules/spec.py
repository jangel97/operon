from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModuleRuntime(StrEnum):
    PYTHON = "python"
    GOLANG = "golang"


class ModuleActionParam(BaseModel):
    type: str
    required: bool = False
    default: Any = None


class ModuleAction(BaseModel):
    name: str
    type: str = "read"
    description: str = ""
    params: dict[str, ModuleActionParam] = Field(default_factory=dict)


class ModuleSpec(BaseModel):
    name: str
    runtime: ModuleRuntime
    entrypoint: str
    actions: list[ModuleAction]


def load_module_spec(path: Path) -> ModuleSpec:
    import yaml

    raw = yaml.safe_load(path.read_text())
    return ModuleSpec.model_validate(raw)
