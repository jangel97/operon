from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, model_validator


class ApprovalMode(StrEnum):
    REQUIRED = "required"
    NONE = "none"


class RouterSpec(BaseModel):
    model: str
    provider: str | None = None
    base_url: str | None = None
    temperature: float | None = None


class ExtractorSpec(BaseModel):
    model: str
    provider: str | None = None
    base_url: str | None = None
    temperature: float | None = None


class DecisionSpec(BaseModel):
    type: str
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    temperature: float | None = None
    max_history: int | None = None
    router: RouterSpec | None = None
    extractor: ExtractorSpec | None = None


class InputSpec(BaseModel):
    type: str
    default: Any = None
    no_log: bool = False


class ActionToolSpec(BaseModel):
    type: str
    approval: ApprovalMode | None = None
    config: dict[str, Any] = {}

    @model_validator(mode="before")
    @classmethod
    def parse_shorthand(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"type": data}
        if isinstance(data, dict) and len(data) == 1:
            type_name, config = next(iter(data.items()))
            if type_name == "type":
                return data
            if config is None:
                return {"type": type_name}
            if isinstance(config, dict):
                return {"type": type_name, **config}
        return data


class ActionCollectionSpec(BaseModel):
    name: str
    approval: ApprovalMode | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_shorthand(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"name": data}
        if isinstance(data, dict) and len(data) == 1:
            coll_name, config = next(iter(data.items()))
            if coll_name == "name":
                return data
            if config is None:
                return {"name": coll_name}
            if isinstance(config, dict):
                return {"name": coll_name, **config}
        return data


class ActionsSpec(BaseModel):
    collections: list[ActionCollectionSpec] = []
    tools: list[ActionToolSpec] = []


class ConstraintsSpec(BaseModel):
    max_actions: int = 10
    denied_patterns: list[str] = []


class PolicySpec(BaseModel):
    constraints: ConstraintsSpec = ConstraintsSpec()


class AgentSpec(BaseModel):
    goal: str
    decision: DecisionSpec
    inputs: dict[str, InputSpec] = {}
    actions: ActionsSpec = ActionsSpec()
    policy: PolicySpec = PolicySpec()


class AgentMetadata(BaseModel):
    name: str
    version: str = "v1"


class AgentDefinition(BaseModel):
    apiVersion: str
    kind: str
    metadata: AgentMetadata
    spec: AgentSpec
