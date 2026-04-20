from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from operon.agent.trace import EventType, ExecutionTrace
from operon.decision.base import LLMProvider
from operon.policy.engine import PolicyEngine
from operon.tools.base import ToolRegistry

console = Console()

MAX_ITERATIONS = 20


class AgentLoop:
    def __init__(
        self,
        goal: str,
        decision_engine: LLMProvider,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
        agent_name: str = "unknown",
        dry_run: bool = False,
    ) -> None:
        self.goal = goal
        self.decision_engine = decision_engine
        self.tool_registry = tool_registry
        self.policy_engine = policy_engine
        self.dry_run = dry_run
        self.history: list[dict] = []
        self.trace = ExecutionTrace(agent_name=agent_name)

    def run(self) -> ExecutionTrace:
        self.trace.start()

        if self.dry_run:
            console.print(Panel("[bold yellow]DRY RUN[/] — no actions will be executed", border_style="yellow"))

        console.print(Panel(self.goal, title="Goal", border_style="green"))

        available_actions = self.tool_registry.get_actions()

        for iteration in range(1, MAX_ITERATIONS + 1):
            console.print(f"\n[bold]--- Step {iteration} ---[/]")

            # 1. Decide
            console.print("[dim]Thinking...[/]")
            try:
                decision = self.decision_engine.decide(
                    self.goal, available_actions, self.history
                )
            except Exception as e:
                console.print(f"[bold red]Decision engine error:[/] {e}")
                self.trace.record(EventType.ERROR, error=str(e))
                self.trace.finish("failed")
                break

            if decision.done:
                console.print(
                    Panel(decision.summary, title="Completed", border_style="green")
                )
                self.trace.record(EventType.DONE, summary=decision.summary)
                self.trace.finish("completed")
                break

            action = decision.action
            console.print(f"[bold yellow]Action:[/] {action.action}")
            console.print(f"[dim]Reasoning:[/] {action.reasoning}")
            console.print(f"[dim]Confidence:[/] {action.confidence}")
            if action.params:
                console.print(f"[dim]Params:[/] {json.dumps(action.params)}")

            self.trace.record(
                EventType.DECISION,
                action=action.action,
                params=action.params,
                reasoning=action.reasoning,
                confidence=action.confidence,
            )

            # 2. Policy check
            policy_result = self.policy_engine.check(action.action)

            self.trace.record(
                EventType.POLICY_CHECK,
                action=action.action,
                allowed=policy_result.allowed,
                requires_approval=policy_result.requires_approval,
                reason=policy_result.reason,
            )

            if not policy_result.allowed:
                console.print(f"[bold red]Policy DENIED:[/] {policy_result.reason}")
                self.history.append({
                    "action": action.action,
                    "params": action.params,
                    "result": f"DENIED by policy: {policy_result.reason}",
                })
                continue

            # 3. Approval
            if policy_result.requires_approval:
                if self.dry_run:
                    console.print("[bold magenta]Approval required[/] — [yellow]auto-skipped (dry run)[/]")
                    self.trace.record(EventType.APPROVAL, approved=False, dry_run=True)
                    self.history.append({
                        "action": action.action,
                        "params": action.params,
                        "result": "SKIPPED (dry run)",
                    })
                    continue
                else:
                    console.print("[bold magenta]Approval required.[/]")
                    approved = Confirm.ask("  Approve this action?")
                    self.trace.record(EventType.APPROVAL, approved=approved)
                    if not approved:
                        console.print("[yellow]Rejected by operator.[/]")
                        self.history.append({
                            "action": action.action,
                            "params": action.params,
                            "result": "REJECTED by operator",
                        })
                        continue

            # 4. Execute
            if self.dry_run:
                result = f"[DRY RUN] Would execute: {action.action}({json.dumps(action.params)})"
                console.print(f"[yellow]{result}[/]")
                self.trace.record(EventType.ACTION, action=action.action, params=action.params, dry_run=True)
                self.trace.record(EventType.RESULT, result=result)
            else:
                console.print("[blue]Executing...[/]")
                self.trace.record(EventType.ACTION, action=action.action, params=action.params)
                try:
                    result = self.tool_registry.execute(action.action, action.params)
                except Exception as e:
                    result = f"ERROR: {e}"
                    self.trace.record(EventType.ERROR, error=str(e))

                self.policy_engine.record_action()
                console.print(f"[green]Result:[/]\n{result}")
                self.trace.record(EventType.RESULT, result=result)

            self.history.append({
                "action": action.action,
                "params": action.params,
                "result": result,
            })
        else:
            console.print(
                f"[bold red]Max iterations ({MAX_ITERATIONS}) reached. Stopping.[/]"
            )
            self.trace.finish("max_iterations")

        self.trace.print_summary(console)
        return self.trace
