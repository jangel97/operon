from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PolicyMode(StrEnum):
    AUTONOMOUS = "autonomous"
    APPROVAL_REQUIRED = "approval_required"
    READ_ONLY = "read_only"


class DecisionSpec(BaseModel):
    type: str
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str | None = None


class InputSpec(BaseModel):
    type: str
    default: Any = None


class ToolSpec(BaseModel):
    name: str
    type: str
    config: dict[str, Any] = {}


class TriggerSpec(BaseModel):
    type: str
    schedule: str | None = None


class ExecutionSpec(BaseModel):
    trigger: TriggerSpec | None = None


class ConstraintsSpec(BaseModel):
    max_actions: int = 10
    denied_patterns: list[str] = []


class PolicySpec(BaseModel):
    mode: PolicyMode = PolicyMode.APPROVAL_REQUIRED
    allowed_actions: list[str] = []
    constraints: ConstraintsSpec = ConstraintsSpec()


class AgentSpec(BaseModel):
    goal: str
    decision: DecisionSpec
    inputs: dict[str, InputSpec] = {}
    tools: list[ToolSpec] = []
    policy: PolicySpec = PolicySpec()
    execution: ExecutionSpec | None = None


class AgentMetadata(BaseModel):
    name: str
    version: str = "v1"


class AgentDefinition(BaseModel):
    apiVersion: str
    kind: str
    metadata: AgentMetadata
    spec: AgentSpec
