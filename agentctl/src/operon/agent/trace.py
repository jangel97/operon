from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table


class EventType(str, Enum):
    DECISION = "DECISION"
    POLICY_CHECK = "POLICY_CHECK"
    APPROVAL = "APPROVAL"
    ACTION = "ACTION"
    RESULT = "RESULT"
    ERROR = "ERROR"
    DONE = "DONE"


@dataclass
class TraceEvent:
    type: EventType
    timestamp: str
    data: dict[str, Any]

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class ExecutionTrace:
    agent_name: str
    started_at: str = ""
    finished_at: str = ""
    events: list[TraceEvent] = field(default_factory=list)
    status: str = "pending"

    def start(self) -> None:
        self.started_at = TraceEvent.now()
        self.status = "running"

    def finish(self, status: str = "completed") -> None:
        self.finished_at = TraceEvent.now()
        self.status = status

    def record(self, event_type: EventType, **data: Any) -> None:
        self.events.append(TraceEvent(
            type=event_type,
            timestamp=TraceEvent.now(),
            data=data,
        ))

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_events": len(self.events),
            "events": [
                {"type": e.type.value, "timestamp": e.timestamp, **e.data}
                for e in self.events
            ],
        }

    def print_summary(self, console: Console) -> None:
        table = Table(title="Execution Trace", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="bold", width=14)
        table.add_column("Timestamp", style="dim", width=28)
        table.add_column("Details")

        for i, event in enumerate(self.events, 1):
            style = _event_style(event.type)
            details = _format_details(event)
            table.add_row(str(i), f"[{style}]{event.type.value}[/]", event.timestamp, details)

        console.print()
        console.print(table)
        console.print(f"\n[bold]Status:[/] {self.status} | "
                      f"[bold]Events:[/] {len(self.events)} | "
                      f"[bold]Duration:[/] {self._duration()}")

    def _duration(self) -> str:
        if not self.started_at or not self.finished_at:
            return "n/a"
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.finished_at)
        delta = end - start
        return f"{delta.total_seconds():.1f}s"


def _event_style(event_type: EventType) -> str:
    return {
        EventType.DECISION: "yellow",
        EventType.POLICY_CHECK: "cyan",
        EventType.APPROVAL: "magenta",
        EventType.ACTION: "blue",
        EventType.RESULT: "green",
        EventType.ERROR: "red",
        EventType.DONE: "bold green",
    }.get(event_type, "white")


def _format_details(event: TraceEvent) -> str:
    d = event.data
    if event.type == EventType.DECISION:
        conf = f" (confidence: {d['confidence']})" if d.get("confidence") else ""
        return f"{d.get('action', 'done')} — {d.get('reasoning', '')}{conf}"
    if event.type == EventType.POLICY_CHECK:
        verdict = "ALLOWED" if d.get("allowed") else "DENIED"
        extra = f" (approval required)" if d.get("requires_approval") else ""
        reason = f" — {d['reason']}" if d.get("reason") else ""
        return f"{verdict}{extra}{reason}"
    if event.type == EventType.APPROVAL:
        return "approved" if d.get("approved") else "rejected"
    if event.type == EventType.ACTION:
        return f"{d.get('action', '?')}({d.get('params', {})})"
    if event.type == EventType.RESULT:
        text = str(d.get("result", ""))
        return text[:120] + "..." if len(text) > 120 else text
    if event.type == EventType.ERROR:
        return str(d.get("error", ""))
    if event.type == EventType.DONE:
        return str(d.get("summary", ""))
    return str(d)
