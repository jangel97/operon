from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml
from rich.console import Console

from operon.agent.loop import AgentLoop
from operon.agent.redact import Redactor
from operon.agent.secrets import resolve_env_vars
from operon.agent.spec import AgentDefinition, AgentSpec
from operon.agent.trace import ExecutionTrace
from operon.decision import create_provider
from operon.policy.engine import PolicyEngine
from operon.tools import create_tool, _discover_tools, _tools
from operon.tools.base import ToolRegistry
from operon.tools.collections import resolve_collection


class AgentRunner:
    def __init__(
        self,
        console: Console | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        self.console = console or Console()
        self.on_event = on_event

    def run(self, spec_path: str, inputs: dict | None = None, dry_run: bool = False) -> ExecutionTrace:
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"Agent spec not found: {spec_path}")

        raw = yaml.safe_load(resolve_env_vars(path.read_text()))
        definition = AgentDefinition(**raw)
        spec = definition.spec

        self.console.print(f"[bold]Agent:[/] {definition.metadata.name} ({definition.metadata.version})")
        self.console.print(f"[bold]Reasoner:[/] {spec.decision.provider}/{spec.decision.model}")
        if spec.decision.router:
            r = spec.decision.router
            self.console.print(
                f"[bold]Router:[/] {r.provider or spec.decision.provider}/{r.model}"
            )
        if spec.decision.extractor:
            ext = spec.decision.extractor
            self.console.print(
                f"[bold]Extractor:[/] {ext.provider or spec.decision.provider}/{ext.model}"
            )

        resolved_inputs = self._resolve_inputs(spec, inputs)

        redactor = Redactor()
        for name, input_spec in spec.inputs.items():
            if input_spec.no_log and name in resolved_inputs:
                redactor.add_secret(str(resolved_inputs[name]))
        for tool_spec in spec.actions.tools:
            if tool_spec.config:
                for value in tool_spec.config.values():
                    redactor.add_secret(str(value))

        if resolved_inputs:
            self.console.print(f"[bold]Inputs:[/] {redactor.redact(resolved_inputs)}")

        decision_engine = self._build_decision_engine(spec)

        tool_registry = self._build_tool_registry(spec)
        policy_engine = PolicyEngine(spec.policy, tool_registry)

        goal = spec.goal
        for key, value in resolved_inputs.items():
            goal = goal.replace(f"{{{{{key}}}}}", str(value))

        loop = AgentLoop(
            goal=goal,
            decision_engine=decision_engine,
            tool_registry=tool_registry,
            policy_engine=policy_engine,
            agent_name=definition.metadata.name,
            dry_run=dry_run,
            console=self.console,
            on_event=self.on_event,
            redactor=redactor,
        )

        return loop.run()

    def _resolve_inputs(self, spec: AgentSpec, inputs: dict | None) -> dict:
        resolved = {}
        for name, input_spec in spec.inputs.items():
            if inputs and name in inputs:
                resolved[name] = inputs[name]
            elif input_spec.default is not None:
                resolved[name] = input_spec.default
            else:
                raise ValueError(f"Missing required input: {name}")
        return resolved

    def _build_decision_engine(self, spec: AgentSpec):
        provider_kwargs: dict = {"model": spec.decision.model}
        if spec.decision.base_url:
            provider_kwargs["base_url"] = spec.decision.base_url
        if spec.decision.temperature is not None:
            provider_kwargs["temperature"] = spec.decision.temperature
        engine = create_provider(spec.decision.provider, **provider_kwargs)

        if spec.decision.router:
            r = spec.decision.router
            r_provider = r.provider or spec.decision.provider
            r_kwargs: dict = {"model": r.model}
            r_base_url = r.base_url or spec.decision.base_url
            if r_base_url:
                r_kwargs["base_url"] = r_base_url
            if r.temperature is not None:
                r_kwargs["temperature"] = r.temperature
            engine.set_router(create_provider(r_provider, **r_kwargs))

        if spec.decision.extractor:
            ext = spec.decision.extractor
            ext_provider = ext.provider or spec.decision.provider
            ext_kwargs: dict = {"model": ext.model}
            ext_base_url = ext.base_url or spec.decision.base_url
            if ext_base_url:
                ext_kwargs["base_url"] = ext_base_url
            if ext.temperature is not None:
                ext_kwargs["temperature"] = ext.temperature
            engine.set_extractor(create_provider(ext_provider, **ext_kwargs))

        return engine

    def _build_tool_registry(self, spec: AgentSpec) -> ToolRegistry:
        registry = ToolRegistry()

        _discover_tools()
        known = set(_tools.keys())

        for coll_spec in spec.actions.collections:
            tool_types = resolve_collection(coll_spec.name, known_tools=known)
            for tool_type in tool_types:
                if not registry.has_tool(tool_type):
                    registry.register(create_tool(tool_type), approval=coll_spec.approval)

        for tool_spec in spec.actions.tools:
            if not registry.has_tool(tool_spec.type):
                registry.register(
                    create_tool(tool_spec.type),
                    approval=tool_spec.approval,
                    config=tool_spec.config or None,
                )
            elif tool_spec.approval is not None:
                for fqn in list(registry._action_meta):
                    if fqn.startswith(f"{tool_spec.type}:"):
                        registry.set_approval(fqn, tool_spec.approval)

        return registry
