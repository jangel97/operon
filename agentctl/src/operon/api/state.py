from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunState:
    run_id: str
    spec: str
    inputs: dict[str, str]
    dry_run: bool
    status: str = "pending"
    agent_name: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    trace_dict: dict[str, Any] | None = None
    error: str | None = None
    _subscribers: list[asyncio.Queue] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()

    def create(self, spec: str, inputs: dict[str, str], dry_run: bool) -> RunState:
        run_id = uuid.uuid4().hex[:12]
        state = RunState(run_id=run_id, spec=spec, inputs=inputs, dry_run=dry_run)
        with self._lock:
            self._runs[run_id] = state
        return state

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_all(self) -> list[RunState]:
        with self._lock:
            return list(self._runs.values())

    def push_event(self, run_id: str, event: dict, loop: asyncio.AbstractEventLoop) -> None:
        state = self.get(run_id)
        if state is None:
            return
        with state._lock:
            state.events.append(event)
            for queue in state._subscribers:
                loop.call_soon_threadsafe(queue.put_nowait, event)

    def subscribe(self, run_id: str) -> asyncio.Queue | None:
        state = self.get(run_id)
        if state is None:
            return None
        queue: asyncio.Queue = asyncio.Queue()
        with state._lock:
            state._subscribers.append(queue)
            for past in state.events:
                queue.put_nowait(past)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        state = self.get(run_id)
        if state is None:
            return
        with state._lock:
            try:
                state._subscribers.remove(queue)
            except ValueError:
                pass
