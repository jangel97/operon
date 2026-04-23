from __future__ import annotations

import asyncio
import json
import threading

from fastapi import FastAPI, HTTPException
from rich.console import Console
from sse_starlette.sse import EventSourceResponse

from operon import __version__
from operon.agent.runner import AgentRunner
from operon.api.models import RunCreated, RunDetail, RunRequest, RunSummary
from operon.api.state import RunStore


def create_app() -> FastAPI:
    app = FastAPI(
        title="Operon Agent API",
        version=__version__,
        description="REST API for running Operon agents",
    )

    store = RunStore()

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "version": __version__}

    @app.post("/api/v1/runs", response_model=RunCreated, status_code=202)
    async def create_run(req: RunRequest):
        run_state = store.create(spec=req.spec, inputs=req.inputs, dry_run=req.dry_run)
        loop = asyncio.get_running_loop()

        def on_event(event: dict) -> None:
            event_type = event.get("type")
            if event_type == "START":
                run_state.status = "running"
                run_state.agent_name = event.get("agent")
                run_state.started_at = event.get("timestamp")
            elif event_type == "FINISH":
                run_state.status = event.get("status", "completed")
                run_state.finished_at = event.get("timestamp")
            store.push_event(run_state.run_id, event, loop)

        def run_agent() -> None:
            try:
                console = Console(quiet=True)
                runner = AgentRunner(console=console, on_event=on_event)
                trace = runner.run(
                    run_state.spec,
                    run_state.inputs if run_state.inputs else None,
                    dry_run=run_state.dry_run,
                )
                run_state.trace_dict = trace.to_dict()
                if run_state.status == "running":
                    run_state.status = trace.status
            except Exception as e:
                run_state.status = "failed"
                run_state.error = str(e)
                error_event = {"type": "ERROR", "error": str(e)}
                store.push_event(run_state.run_id, error_event, loop)
                finish_event = {"type": "FINISH", "status": "failed"}
                store.push_event(run_state.run_id, finish_event, loop)

        thread = threading.Thread(target=run_agent, daemon=True, name=f"run-{run_state.run_id}")
        thread.start()

        return RunCreated(run_id=run_state.run_id, status="pending")

    @app.get("/api/v1/runs", response_model=list[RunSummary])
    async def list_runs():
        return [
            RunSummary(
                run_id=r.run_id,
                spec=r.spec,
                status=r.status,
                agent_name=r.agent_name,
                started_at=r.started_at,
                finished_at=r.finished_at,
                event_count=len(r.events),
            )
            for r in store.list_all()
        ]

    @app.get("/api/v1/runs/{run_id}", response_model=RunDetail)
    async def get_run(run_id: str):
        run_state = store.get(run_id)
        if run_state is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return RunDetail(
            run_id=run_state.run_id,
            spec=run_state.spec,
            status=run_state.status,
            agent_name=run_state.agent_name,
            started_at=run_state.started_at,
            finished_at=run_state.finished_at,
            event_count=len(run_state.events),
            inputs=run_state.inputs,
            trace=run_state.trace_dict,
        )

    @app.get("/api/v1/runs/{run_id}/events")
    async def stream_events(run_id: str):
        run_state = store.get(run_id)
        if run_state is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        queue = store.subscribe(run_id)

        async def event_generator():
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    except asyncio.TimeoutError:
                        if run_state.status not in ("pending", "running"):
                            return
                        yield {"comment": "keep-alive"}
                        continue

                    yield {
                        "event": event.get("type", "message"),
                        "data": json.dumps(event, default=str),
                    }
                    if event.get("type") == "FINISH":
                        break
            finally:
                store.unsubscribe(run_id, queue)

        return EventSourceResponse(event_generator())

    return app
