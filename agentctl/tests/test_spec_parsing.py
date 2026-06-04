from __future__ import annotations

import pytest

from operon.agent.spec import (
    ActionCollectionSpec,
    ActionToolSpec,
    ActionsSpec,
    AgentDefinition,
    ApprovalMode,
    DecisionSpec,
    ExtractorSpec,
    RouterSpec,
)


class TestActionToolSpec:
    def test_bare_string(self):
        spec = ActionToolSpec.model_validate("websearch")
        assert spec.type == "websearch"
        assert spec.approval is None

    def test_dict_with_approval_required(self):
        spec = ActionToolSpec.model_validate({"k8s-restarter": {"approval": "required"}})
        assert spec.type == "k8s-restarter"
        assert spec.approval == ApprovalMode.REQUIRED

    def test_dict_with_approval_none(self):
        spec = ActionToolSpec.model_validate({"k8s-scaler": {"approval": "none"}})
        assert spec.type == "k8s-scaler"
        assert spec.approval == ApprovalMode.NONE

    def test_dict_with_null_config(self):
        spec = ActionToolSpec.model_validate({"websearch": None})
        assert spec.type == "websearch"
        assert spec.approval is None

    def test_explicit_type_field(self):
        spec = ActionToolSpec.model_validate({"type": "websearch"})
        assert spec.type == "websearch"
        assert spec.approval is None

    def test_config_field(self):
        spec = ActionToolSpec.model_validate(
            {"telegram-sender": {"approval": "required", "config": {"bot_token": "abc", "chat_id": "123"}}}
        )
        assert spec.type == "telegram-sender"
        assert spec.approval == ApprovalMode.REQUIRED
        assert spec.config == {"bot_token": "abc", "chat_id": "123"}

    def test_config_defaults_to_empty(self):
        spec = ActionToolSpec.model_validate("websearch")
        assert spec.config == {}


class TestActionCollectionSpec:
    def test_bare_string(self):
        spec = ActionCollectionSpec.model_validate("k8s-readonly")
        assert spec.name == "k8s-readonly"
        assert spec.approval is None

    def test_dict_with_approval(self):
        spec = ActionCollectionSpec.model_validate({"k8s-sre": {"approval": "required"}})
        assert spec.name == "k8s-sre"
        assert spec.approval == ApprovalMode.REQUIRED

    def test_dict_with_null_config(self):
        spec = ActionCollectionSpec.model_validate({"k8s-readonly": None})
        assert spec.name == "k8s-readonly"
        assert spec.approval is None


class TestActionsSpec:
    def test_mixed_tools_and_collections(self):
        data = {
            "collections": ["k8s-readonly", {"k8s-sre": {"approval": "required"}}],
            "tools": ["websearch", {"k8s-restarter": {"approval": "required"}}],
        }
        spec = ActionsSpec.model_validate(data)
        assert len(spec.collections) == 2
        assert spec.collections[0].name == "k8s-readonly"
        assert spec.collections[1].approval == ApprovalMode.REQUIRED
        assert len(spec.tools) == 2
        assert spec.tools[0].type == "websearch"
        assert spec.tools[1].approval == ApprovalMode.REQUIRED

    def test_empty_actions(self):
        spec = ActionsSpec.model_validate({})
        assert spec.collections == []
        assert spec.tools == []

    def test_tools_only(self):
        spec = ActionsSpec.model_validate({"tools": ["websearch", "weather"]})
        assert len(spec.tools) == 2
        assert spec.collections == []


class TestFullSpecParsing:
    def test_new_format_parses(self):
        raw = {
            "apiVersion": "agents/v1",
            "kind": "Agent",
            "metadata": {"name": "test-agent", "version": "v1"},
            "spec": {
                "goal": "Test goal",
                "decision": {"type": "llm", "provider": "openai", "model": "gpt-4o-mini"},
                "actions": {
                    "collections": ["k8s-readonly"],
                    "tools": [
                        "websearch",
                        {"k8s-restarter": {"approval": "required"}},
                    ],
                },
                "policy": {
                    "constraints": {"max_actions": 15},
                },
            },
        }
        defn = AgentDefinition.model_validate(raw)
        assert defn.metadata.name == "test-agent"
        assert len(defn.spec.actions.collections) == 1
        assert len(defn.spec.actions.tools) == 2
        assert defn.spec.actions.tools[1].approval == ApprovalMode.REQUIRED
        assert defn.spec.policy.constraints.max_actions == 15

    def test_minimal_spec(self):
        raw = {
            "apiVersion": "agents/v1",
            "kind": "Agent",
            "metadata": {"name": "minimal"},
            "spec": {
                "goal": "Do something",
                "decision": {"type": "llm"},
                "actions": {
                    "tools": ["websearch"],
                },
            },
        }
        defn = AgentDefinition.model_validate(raw)
        assert len(defn.spec.actions.tools) == 1
        assert defn.spec.policy.constraints.max_actions == 10


class TestDecisionSpec:
    def test_temperature_default_none(self):
        spec = DecisionSpec(type="llm")
        assert spec.temperature is None

    def test_temperature_set(self):
        spec = DecisionSpec(type="llm", temperature=0.7)
        assert spec.temperature == 0.7

    def test_router_default_none(self):
        spec = DecisionSpec(type="llm")
        assert spec.router is None

    def test_router_spec(self):
        spec = DecisionSpec(
            type="llm",
            provider="ollama",
            model="qwen3:14b",
            router=RouterSpec(model="qwen3:1.7b"),
        )
        assert spec.router.model == "qwen3:1.7b"
        assert spec.router.provider is None
        assert spec.router.temperature is None

    def test_router_with_temperature(self):
        spec = DecisionSpec(
            type="llm",
            router=RouterSpec(model="small", temperature=0.3),
        )
        assert spec.router.temperature == 0.3

    def test_extractor_with_temperature(self):
        spec = DecisionSpec(
            type="llm",
            extractor=ExtractorSpec(model="small", temperature=0.1),
        )
        assert spec.extractor.temperature == 0.1

    def test_all_three_layers(self):
        spec = DecisionSpec(
            type="llm",
            provider="ollama",
            model="qwen3:14b",
            temperature=0.7,
            router=RouterSpec(model="qwen3:1.7b", temperature=0.3),
            extractor=ExtractorSpec(model="qwen3:1.7b", temperature=0.1),
        )
        assert spec.temperature == 0.7
        assert spec.router.model == "qwen3:1.7b"
        assert spec.router.temperature == 0.3
        assert spec.extractor.model == "qwen3:1.7b"
        assert spec.extractor.temperature == 0.1

    def test_from_yaml_dict(self):
        raw = {
            "type": "llm",
            "provider": "ollama",
            "model": "qwen3:14b",
            "temperature": 0.5,
            "router": {"model": "qwen3:1.7b", "temperature": 0.2},
            "extractor": {"model": "qwen3:1.7b"},
        }
        spec = DecisionSpec(**raw)
        assert spec.temperature == 0.5
        assert spec.router.model == "qwen3:1.7b"
        assert spec.router.temperature == 0.2
        assert spec.extractor.model == "qwen3:1.7b"
        assert spec.extractor.temperature is None

    def test_max_history_default_none(self):
        spec = DecisionSpec(type="llm")
        assert spec.max_history is None

    def test_max_history_set(self):
        spec = DecisionSpec(type="llm", max_history=5)
        assert spec.max_history == 5

    def test_max_history_from_yaml_dict(self):
        raw = {
            "type": "llm",
            "provider": "ollama",
            "model": "qwen3:14b",
            "max_history": 3,
        }
        spec = DecisionSpec(**raw)
        assert spec.max_history == 3
