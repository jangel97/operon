from __future__ import annotations

import pytest

from operon.decision.base import LLMProvider, _extract_json


class TestPlainJson:
    def test_clean_action(self):
        result = _extract_json('{"done": false, "action": "kubectl:get_pods", "params": {}}')
        assert result["action"] == "kubectl:get_pods"
        assert result["done"] is False

    def test_clean_done(self):
        result = _extract_json('{"done": true, "summary": "Task complete"}')
        assert result["done"] is True
        assert result["summary"] == "Task complete"

    def test_nested_params(self):
        text = '{"action": "kubectl:get_pods", "params": {"namespace": "prod"}, "confidence": 0.9}'
        result = _extract_json(text)
        assert result["params"]["namespace"] == "prod"


class TestCodeFences:
    def test_json_fence(self):
        text = 'Here is my decision:\n```json\n{"done": true, "summary": "done"}\n```'
        result = _extract_json(text)
        assert result["done"] is True

    def test_plain_fence(self):
        text = '```\n{"action": "websearch:web_search", "params": {"query": "test"}}\n```'
        result = _extract_json(text)
        assert result["action"] == "websearch:web_search"

    def test_fence_with_surrounding_text(self):
        text = 'I will search now.\n```json\n{"action": "websearch:web_search", "params": {}}\n```\nDone.'
        result = _extract_json(text)
        assert result["action"] == "websearch:web_search"


class TestJsonWithSurroundingText:
    def test_text_before_json(self):
        text = 'Let me think about this. {"done": true, "summary": "finished"}'
        result = _extract_json(text)
        assert result["done"] is True

    def test_text_after_json(self):
        text = '{"action": "kubectl:get_pods", "params": {}} I hope this works.'
        result = _extract_json(text)
        assert result["action"] == "kubectl:get_pods"

    def test_text_before_and_after(self):
        text = 'Okay here: {"done": true, "summary": "all good"} that is my answer.'
        result = _extract_json(text)
        assert result["done"] is True


class TestGarbageFallback:
    def test_plain_text_becomes_done_summary(self):
        result = _extract_json("I have completed the analysis and everything looks good.")
        assert result["done"] is True
        assert "completed the analysis" in result["summary"]

    def test_empty_string(self):
        result = _extract_json("")
        assert result["done"] is True

    def test_invalid_json(self):
        result = _extract_json("{not valid json at all")
        assert result["done"] is True


class TestMultipleJsonObjects:
    def test_picks_first_valid(self):
        text = 'bad {invalid and {"action": "kubectl:get_pods", "params": {}}'
        result = _extract_json(text)
        assert result["action"] == "kubectl:get_pods"


class TestEdgeCases:
    def test_unicode_content(self):
        text = '{"done": true, "summary": "Weather in Barcelona: 23\u00b0C sunny"}'
        result = _extract_json(text)
        assert "23" in result["summary"]

    def test_newlines_in_summary(self):
        text = '{"done": true, "summary": "line1\\nline2\\nline3"}'
        result = _extract_json(text)
        assert result["done"] is True

    def test_confidence_as_string(self):
        text = '{"action": "kubectl:get_pods", "params": {}, "confidence": "0.9"}'
        result = _extract_json(text)
        assert result["confidence"] == "0.9"


class TestParseResponse:
    class _DummyProvider(LLMProvider):
        def _call_llm(self, messages: list[dict]) -> str:
            return ""

    def test_missing_action_field_treated_as_done(self):
        provider = self._DummyProvider()
        decision = provider._parse_response('{"done": false, "reasoning": "hmm"}')
        assert decision.done is True

    def test_valid_action_parsed(self):
        provider = self._DummyProvider()
        decision = provider._parse_response('{"action": "kubectl:get_pods", "params": {}}')
        assert decision.action.action == "kubectl:get_pods"

    def test_done_true_parsed(self):
        provider = self._DummyProvider()
        decision = provider._parse_response('{"done": true, "summary": "all done"}')
        assert decision.done is True
        assert decision.summary == "all done"
