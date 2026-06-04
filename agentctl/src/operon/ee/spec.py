from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ModuleDependency(BaseModel):
    path: str

    @model_validator(mode="before")
    @classmethod
    def parse_shorthand(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"path": data}
        return data


class EEDependencies(BaseModel):
    tools: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    python: list[str] = Field(default_factory=list)
    golang: list[str] = Field(default_factory=list)
    system: list[str] = Field(default_factory=list)
    modules: list[ModuleDependency] = Field(default_factory=list)


class EEBuildOptions(BaseModel):
    base_image: str = "python:3.12-slim"


class EEDefinition(BaseModel):
    version: int = 1
    build: EEBuildOptions = Field(default_factory=EEBuildOptions)
    dependencies: EEDependencies = Field(default_factory=EEDependencies)


def load_ee_definition(path: Path) -> EEDefinition:
    import yaml

    raw = yaml.safe_load(path.read_text())
    return EEDefinition.model_validate(raw)
