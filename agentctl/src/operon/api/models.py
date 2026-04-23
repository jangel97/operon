from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    spec: str = Field(..., description="Path to agent YAML spec file")
    inputs: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = Field(default=False)


class RunCreated(BaseModel):
    run_id: str
    status: str


class RunSummary(BaseModel):
    run_id: str
    spec: str
    status: str
    agent_name: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    event_count: int = 0


class RunDetail(RunSummary):
    inputs: dict[str, str] = {}
    trace: dict[str, Any] | None = None
