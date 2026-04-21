from __future__ import annotations

import json

from operon.agent.redact import PLACEHOLDER, Redactor
from operon.agent.spec import AgentDefinition, InputSpec
from operon.agent.trace import EventType, ExecutionTrace


class TestInputSpecNoLog:
    def test_no_log_default_false(self):
        spec = InputSpec(type="string")
        assert spec.no_log is False

    def test_no_log_true(self):
        spec = InputSpec(type="string", no_log=True)
        assert spec.no_log is True

    def test_yaml_parsing_with_no_log(self):
        raw = {
            "apiVersion": "agents/v1",
            "kind": "Agent",
            "metadata": {"name": "test", "version": "v1"},
            "spec": {
                "goal": "test goal",
                "decision": {"type": "llm", "provider": "openai", "model": "gpt-4o-mini"},
                "inputs": {
                    "token": {"type": "string", "no_log": True},
                    "namespace": {"type": "string", "default": "default"},
                },
                "tools": [],
            },
        }
        definition = AgentDefinition(**raw)
        assert definition.spec.inputs["token"].no_log is True
        assert definition.spec.inputs["namespace"].no_log is False


class TestTraceRedaction:
    def _make_trace(self, secret: str) -> ExecutionTrace:
        redactor = Redactor()
        redactor.add_secret(secret)
        return ExecutionTrace(agent_name="test", redactor=redactor)

    def test_to_dict_redacts_params(self):
        trace = self._make_trace("supersecrettoken")
        trace.start()
        trace.record(
            EventType.ACTION,
            action="kubectl:get_pods",
            params={"token": "supersecrettoken"},
        )
        trace.finish("completed")

        output = trace.to_dict()
        serialized = json.dumps(output)
        assert "supersecrettoken" not in serialized
        assert PLACEHOLDER in serialized

    def test_to_dict_redacts_reasoning(self):
        trace = self._make_trace("my-password")
        trace.start()
        trace.record(
            EventType.DECISION,
            action="test:action",
            reasoning="Using my-password to connect",
            confidence=0.9,
        )
        trace.finish("completed")

        output = trace.to_dict()
        event = output["events"][0]
        assert "my-password" not in event["reasoning"]
        assert PLACEHOLDER in event["reasoning"]

    def test_to_dict_redacts_result(self):
        trace = self._make_trace("secret-api-key")
        trace.start()
        trace.record(
            EventType.RESULT,
            result="Response: auth=secret-api-key accepted",
        )
        trace.finish("completed")

        output = trace.to_dict()
        event = output["events"][0]
        assert "secret-api-key" not in event["result"]

    def test_to_dict_redacts_summary(self):
        trace = self._make_trace("leaked-token")
        trace.start()
        trace.record(EventType.DONE, summary="Done with leaked-token")
        trace.finish("completed")

        output = trace.to_dict()
        event = output["events"][0]
        assert "leaked-token" not in event["summary"]

    def test_ndjson_events_redacted(self):
        captured = []
        redactor = Redactor()
        redactor.add_secret("ndjson-secret")
        trace = ExecutionTrace(
            agent_name="test",
            on_event=captured.append,
            redactor=redactor,
        )
        trace.start()
        trace.record(
            EventType.ACTION,
            action="test:act",
            params={"key": "ndjson-secret"},
        )
        trace.finish("completed")

        for event in captured:
            assert "ndjson-secret" not in json.dumps(event)

    def test_no_redactor_passthrough(self):
        trace = ExecutionTrace(agent_name="test")
        trace.start()
        trace.record(EventType.RESULT, result="plain value")
        trace.finish("completed")

        output = trace.to_dict()
        assert output["events"][0]["result"] == "plain value"
