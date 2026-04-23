from __future__ import annotations

import json

import pytest

from operon.agent.spec import DecisionSpec, ExtractorSpec
from operon.decision.base import LLMProvider, Decision, _EXTRACTOR_PROMPT


class _DummyProvider(LLMProvider):
    def __init__(self, response: str):
        self._response = response
        self.call_count = 0
        self.last_messages: list[dict] = []

    def _call_llm(self, messages: list[dict]) -> str:
        self.call_count += 1
        self.last_messages = messages
        return self._response


class TestExtractorSpec:
    def test_decision_spec_without_extractor(self):
        spec = DecisionSpec(type="llm")
        assert spec.extractor is None

    def test_decision_spec_with_extractor(self):
        spec = DecisionSpec(
            type="llm",
            provider="ollama",
            model="qwen3:14b",
            extractor=ExtractorSpec(model="qwen3:1.7b"),
        )
        assert spec.extractor is not None
        assert spec.extractor.model == "qwen3:1.7b"
        assert spec.extractor.provider is None
        assert spec.extractor.base_url is None

    def test_extractor_with_different_provider(self):
        spec = DecisionSpec(
            type="llm",
            provider="ollama",
            model="qwen3:14b",
            extractor=ExtractorSpec(model="gpt-4o-mini", provider="openai"),
        )
        assert spec.extractor.provider == "openai"

    def test_extractor_with_base_url(self):
        spec = DecisionSpec(
            type="llm",
            provider="ollama",
            model="qwen3:14b",
            base_url="http://host1:11434/v1",
            extractor=ExtractorSpec(model="small", base_url="http://host2:11434/v1"),
        )
        assert spec.extractor.base_url == "http://host2:11434/v1"

    def test_extractor_from_yaml_dict(self):
        raw = {
            "type": "llm",
            "provider": "ollama",
            "model": "qwen3:14b",
            "extractor": {"model": "llama3.1:8b"},
        }
        spec = DecisionSpec(**raw)
        assert spec.extractor.model == "llama3.1:8b"


class TestDecideWithoutExtractor:
    def test_direct_json_response(self):
        response = json.dumps({
            "done": False,
            "action": "kubectl:get_pods",
            "params": {"namespace": "default"},
            "reasoning": "check pods",
            "confidence": 0.9,
        })
        provider = _DummyProvider(response)
        decision = provider.decide("check pods", [], [])
        assert not decision.done
        assert decision.action.action == "kubectl:get_pods"
        assert provider._extractor is None

    def test_done_response(self):
        response = json.dumps({"done": True, "summary": "all good"})
        provider = _DummyProvider(response)
        decision = provider.decide("check pods", [], [])
        assert decision.done
        assert decision.summary == "all good"


class TestDecideWithExtractor:
    def test_extractor_processes_raw_output(self):
        main = _DummyProvider("I think we should list the pods to see what's happening")
        extractor = _DummyProvider(json.dumps({
            "done": False,
            "action": "kubectl:get_pods",
            "params": {"namespace": "default"},
            "reasoning": "check pod status",
            "confidence": 0.8,
        }))
        main.set_extractor(extractor)

        decision = main.decide("investigate pods", [], [])
        assert not decision.done
        assert decision.action.action == "kubectl:get_pods"
        assert main.call_count == 1
        assert extractor.call_count == 1

    def test_extractor_receives_main_output(self):
        raw_text = "Let me check the pods first to understand the situation"
        main = _DummyProvider(raw_text)
        extractor = _DummyProvider(json.dumps({
            "done": False,
            "action": "kubectl:get_pods",
            "params": {},
            "reasoning": "check pods",
            "confidence": 0.9,
        }))
        main.set_extractor(extractor)

        main.decide("investigate", [], [])

        assert len(extractor.last_messages) == 2
        assert extractor.last_messages[0]["role"] == "system"
        assert extractor.last_messages[1]["role"] == "user"
        assert extractor.last_messages[1]["content"] == raw_text

    def test_extractor_system_prompt(self):
        main = _DummyProvider("some text")
        extractor = _DummyProvider(json.dumps({"done": True, "summary": "done"}))
        main.set_extractor(extractor)

        main.decide("goal", [], [])

        system_msg = extractor.last_messages[0]["content"]
        assert "JSON extraction" in system_msg
        assert "action" in system_msg
        assert "done" in system_msg

    def test_extractor_done_response(self):
        main = _DummyProvider("We've completed the investigation, everything looks fine")
        extractor = _DummyProvider(json.dumps({
            "done": True,
            "summary": "Investigation complete, all pods healthy",
        }))
        main.set_extractor(extractor)

        decision = main.decide("check health", [], [])
        assert decision.done
        assert "healthy" in decision.summary

    def test_extractor_with_history(self):
        main = _DummyProvider("need more info")
        extractor = _DummyProvider(json.dumps({
            "done": False,
            "action": "kubectl:get_logs",
            "params": {"name": "pod-1"},
            "reasoning": "get logs",
            "confidence": 0.85,
        }))
        main.set_extractor(extractor)

        history = [{"action": "kubectl:get_pods", "params": {}, "result": "2 pods found"}]
        decision = main.decide("investigate", [], history)

        assert decision.action.action == "kubectl:get_logs"
        assert main.call_count == 1
        assert extractor.call_count == 1


class TestExtractorFallback:
    def test_extractor_messy_output_still_parsed(self):
        main = _DummyProvider("reasoning text")
        messy_json = 'Here is the JSON:\n```json\n{"done": false, "action": "k8s:list_pods", "params": {}, "reasoning": "check", "confidence": 0.7}\n```'
        extractor = _DummyProvider(messy_json)
        main.set_extractor(extractor)

        decision = main.decide("goal", [], [])
        assert decision.action.action == "k8s:list_pods"

    def test_extractor_garbage_falls_back_to_done(self):
        main = _DummyProvider("reasoning text")
        extractor = _DummyProvider("I cannot parse this properly")
        main.set_extractor(extractor)

        decision = main.decide("goal", [], [])
        assert decision.done


class TestSetExtractor:
    def test_set_extractor(self):
        main = _DummyProvider("test")
        extractor = _DummyProvider("test")
        assert main._extractor is None
        main.set_extractor(extractor)
        assert main._extractor is extractor

    def test_extractor_not_shared_between_instances(self):
        a = _DummyProvider("a")
        b = _DummyProvider("b")
        extractor = _DummyProvider("ext")
        a.set_extractor(extractor)
        assert a._extractor is extractor
        assert b._extractor is None
