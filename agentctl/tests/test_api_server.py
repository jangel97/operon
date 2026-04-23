from __future__ import annotations

import time

import pytest

fastapi = pytest.importorskip("fastapi")
sse_starlette = pytest.importorskip("sse_starlette")

from fastapi.testclient import TestClient

from operon.api.server import create_app
from operon.api.state import RunStore


@pytest.fixture
def client():
    return TestClient(create_app())


class TestHealthz:
    def test_returns_ok(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "version" in resp.json()


class TestListRuns:
    def test_empty_list(self, client):
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetRun:
    def test_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent")
        assert resp.status_code == 404


class TestCreateRun:
    def test_returns_202(self, client):
        resp = client.post("/api/v1/runs", json={
            "spec": "/nonexistent/agent.yaml",
            "inputs": {},
        })
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["status"] == "pending"

    def test_invalid_spec_fails_gracefully(self, client):
        resp = client.post("/api/v1/runs", json={
            "spec": "/nonexistent/agent.yaml",
        })
        run_id = resp.json()["run_id"]
        time.sleep(0.5)
        detail = client.get(f"/api/v1/runs/{run_id}")
        assert detail.json()["status"] == "failed"

    def test_run_appears_in_list(self, client):
        client.post("/api/v1/runs", json={"spec": "/tmp/test.yaml"})
        time.sleep(0.1)
        resp = client.get("/api/v1/runs")
        assert len(resp.json()) == 1

    def test_run_detail_has_inputs(self, client):
        resp = client.post("/api/v1/runs", json={
            "spec": "/tmp/test.yaml",
            "inputs": {"key": "value"},
        })
        run_id = resp.json()["run_id"]
        time.sleep(0.1)
        detail = client.get(f"/api/v1/runs/{run_id}")
        assert detail.json()["inputs"] == {"key": "value"}


class TestStreamEvents:
    def test_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent/events")
        assert resp.status_code == 404

    def test_failed_run_streams_error_and_finish(self, client):
        resp = client.post("/api/v1/runs", json={
            "spec": "/nonexistent/agent.yaml",
        })
        run_id = resp.json()["run_id"]
        time.sleep(0.5)

        with client.stream("GET", f"/api/v1/runs/{run_id}/events") as stream:
            events = []
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    import json
                    events.append(json.loads(line[5:].strip()))
                    if events[-1].get("type") == "FINISH":
                        break

        types = [e["type"] for e in events]
        assert "ERROR" in types
        assert "FINISH" in types


class TestRunStore:
    def test_create_and_get(self):
        store = RunStore()
        run = store.create(spec="test.yaml", inputs={"k": "v"}, dry_run=False)
        assert store.get(run.run_id) is run
        assert run.status == "pending"

    def test_get_nonexistent(self):
        store = RunStore()
        assert store.get("nope") is None

    def test_list_all(self):
        store = RunStore()
        store.create(spec="a.yaml", inputs={}, dry_run=False)
        store.create(spec="b.yaml", inputs={}, dry_run=False)
        assert len(store.list_all()) == 2

    def test_unique_ids(self):
        store = RunStore()
        a = store.create(spec="a.yaml", inputs={}, dry_run=False)
        b = store.create(spec="b.yaml", inputs={}, dry_run=False)
        assert a.run_id != b.run_id
