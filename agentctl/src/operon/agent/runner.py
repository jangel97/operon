from __future__ import annotations

from pathlib import Path

import yaml
from rich.console import Console

from operon.agent.loop import AgentLoop
from operon.agent.spec import AgentDefinition
from operon.decision import create_provider
from operon.policy.engine import PolicyEngine
from operon.tools import create_tool
from operon.tools.base import ToolRegistry

console = Console()


class AgentRunner:
    def run(self, spec_path: str, inputs: dict | None = None, dry_run: bool = False) -> list[dict]:
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"Agent spec not found: {spec_path}")

        raw = yaml.safe_load(path.read_text())
        definition = AgentDefinition(**raw)
        spec = definition.spec

        console.print(f"[bold]Agent:[/] {definition.metadata.name} ({definition.metadata.version})")
        console.print(f"[bold]Mode:[/] {spec.policy.mode}")
        console.print(f"[bold]Provider:[/] {spec.decision.provider}/{spec.decision.model}")

        resolved_inputs = self._resolve_inputs(spec, inputs)
        if resolved_inputs:
            console.print(f"[bold]Inputs:[/] {resolved_inputs}")

        provider_kwargs = {"model": spec.decision.model}
        if spec.decision.base_url:
            provider_kwargs["base_url"] = spec.decision.base_url
        decision_engine = create_provider(spec.decision.provider, **provider_kwargs)
        tool_registry = self._build_tool_registry(spec)
        policy_engine = PolicyEngine(spec.policy)

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
        )

        return loop.run()

    def _resolve_inputs(self, spec, inputs: dict | None) -> dict:
        resolved = {}
        for name, input_spec in spec.inputs.items():
            if inputs and name in inputs:
                resolved[name] = inputs[name]
            elif input_spec.default is not None:
                resolved[name] = input_spec.default
            else:
                raise ValueError(f"Missing required input: {name}")
        return resolved

    def _build_tool_registry(self, spec):
        registry = ToolRegistry()
        for tool_spec in spec.tools:
            registry.register(create_tool(tool_spec.type))
        return registry
