from __future__ import annotations

import os
import time

import requests

from operon.tools.base import Tool

POLL_INTERVAL = 3
POLL_TIMEOUT = 300


class CouncilTool(Tool):
    def __init__(self) -> None:
        self._base_url = os.environ.get("OPERON_SERVE_URL", "http://localhost:8080")

    @property
    def name(self) -> str:
        return "council"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "ask_panelist",
                "type": "read",
                "description": "Run a panelist agent with a question and return their response",
                "params": {
                    "spec": "string (required) — path to panelist agent YAML",
                    "question": "string (required) — the question to discuss",
                },
            },
            {
                "name": "list_runs",
                "type": "read",
                "description": "List all agent runs on the server",
                "params": {},
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        if action == "ask_panelist":
            return self._ask_panelist(params)
        if action == "list_runs":
            return self._list_runs()
        raise ValueError(f"Unknown action: {action}")

    def _ask_panelist(self, params: dict) -> str:
        spec = params.get("spec", "")
        question = params.get("question", "")
        if not spec:
            return "ERROR: 'spec' parameter is required"
        if not question:
            return "ERROR: 'question' parameter is required"

        resp = requests.post(
            f"{self._base_url}/api/v1/runs",
            json={"spec": spec, "inputs": {"question": question}},
            timeout=10,
        )
        if resp.status_code != 202:
            return f"ERROR: server returned {resp.status_code}: {resp.text}"

        run_id = resp.json()["run_id"]

        deadline = time.monotonic() + POLL_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
            detail = requests.get(
                f"{self._base_url}/api/v1/runs/{run_id}", timeout=10
            ).json()
            status = detail.get("status", "")
            if status not in ("pending", "running"):
                break

        if status in ("pending", "running"):
            return f"TIMEOUT: panelist run {run_id} did not finish within {POLL_TIMEOUT}s"

        trace = detail.get("trace") or {}
        events = trace.get("events") or []
        for event in reversed(events):
            if event.get("type") == "DONE":
                return event.get("summary", "(no summary)")
            if event.get("type") == "RESULT":
                return event.get("result", "(no result)")

        return f"Panelist run {run_id} finished with status '{status}' but produced no summary"

    def _list_runs(self) -> str:
        resp = requests.get(f"{self._base_url}/api/v1/runs", timeout=10)
        runs = resp.json()
        if not runs:
            return "No runs found."
        lines = []
        for r in runs:
            lines.append(f"- {r['run_id']}: {r.get('agent_name', '?')} [{r['status']}]")
        return "\n".join(lines)
