from __future__ import annotations

import json
from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from operon.agent.redact import Redactor
from operon.agent.trace import EventType, ExecutionTrace
from operon.decision.base import LLMProvider
from operon.policy.engine import PolicyEngine
from operon.tools.base import ToolRegistry

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
        console: Console | None = None,
        on_event: Callable[[dict], None] | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        self.goal = goal
        self.decision_engine = decision_engine
        self.tool_registry = tool_registry
        self.policy_engine = policy_engine
        self.dry_run = dry_run
        self.console = console or Console()
        self.redactor = redactor or Redactor()
        self.history: list[dict] = []
        self.trace = ExecutionTrace(agent_name=agent_name, on_event=on_event, redactor=self.redactor)

    def run(self) -> ExecutionTrace:
        self.trace.start()

        if self.dry_run:
            self.console.print(Panel("[bold yellow]DRY RUN[/] — no actions will be executed", border_style="yellow"))

        self.console.print(Panel(self.goal, title="Goal", border_style="green"))

        available_actions = self.tool_registry.get_actions()

        for iteration in range(1, MAX_ITERATIONS + 1):
            self.console.print(f"\n[bold]--- Step {iteration} ---[/]")

            # 1. Decide
            self.console.print("[dim]Thinking...[/]")
            try:
                decision = self.decision_engine.decide(
                    self.goal, available_actions, self.history
                )
            except Exception as e:
                self.console.print(f"[bold red]Decision engine error:[/] {e}")
                self.trace.record(EventType.ERROR, error=str(e))
                self.trace.finish("failed")
                break

            if decision.done:
                self.console.print(
                    Panel(self.redactor.redact(decision.summary), title="Completed", border_style="green")
                )
                self.trace.record(EventType.DONE, summary=decision.summary)
                self.trace.finish("completed")
                break

            action = decision.action
            self.console.print(f"[bold yellow]Action:[/] {action.action}")
            self.console.print(f"[dim]Reasoning:[/] {self.redactor.redact(action.reasoning)}")
            self.console.print(f"[dim]Confidence:[/] {action.confidence}")
            if action.params:
                self.console.print(f"[dim]Params:[/] {json.dumps(self.redactor.redact(action.params))}")

            self.trace.record(
                EventType.DECISION,
                action=action.action,
                params=action.params,
                reasoning=action.reasoning,
                confidence=action.confidence,
            )

            # 2. Validate action exists
            action_meta = self.tool_registry.get_action_meta(action.action)
            if not action_meta:
                reason = f"Action '{action.action}' is not available"
                self.console.print(f"[bold red]Unknown action:[/] {reason}")
                self.trace.record(EventType.POLICY_CHECK, action=action.action, allowed=False, reason=reason)
                self.history.append({
                    "action": action.action,
                    "params": action.params,
                    "result": f"DENIED: {reason}",
                })
                continue

            # 3. Policy check
            policy_result = self.policy_engine.check(action.action, action.params, action_meta)

            self.trace.record(
                EventType.POLICY_CHECK,
                action=action.action,
                allowed=policy_result.allowed,
                requires_approval=policy_result.requires_approval,
                reason=policy_result.reason,
            )

            if not policy_result.allowed:
                self.console.print(f"[bold red]Policy DENIED:[/] {policy_result.reason}")
                self.history.append({
                    "action": action.action,
                    "params": action.params,
                    "result": f"DENIED by policy: {policy_result.reason}",
                })
                continue

            # 3. Approval
            if policy_result.requires_approval:
                if self.dry_run:
                    self.console.print("[bold magenta]Approval required[/] — [yellow]auto-skipped (dry run)[/]")
                    self.trace.record(EventType.APPROVAL, approved=False, dry_run=True)
                    self.history.append({
                        "action": action.action,
                        "params": action.params,
                        "result": "SKIPPED (dry run)",
                    })
                    continue
                else:
                    self.console.print("[bold magenta]Approval required.[/]")
                    approved = Confirm.ask("  Approve this action?")
                    self.trace.record(EventType.APPROVAL, approved=approved)
                    if not approved:
                        self.console.print("[yellow]Rejected by operator.[/]")
                        self.history.append({
                            "action": action.action,
                            "params": action.params,
                            "result": "REJECTED by operator",
                        })
                        continue

            # 4. Execute
            if self.dry_run:
                result = f"[DRY RUN] Would execute: {action.action}({json.dumps(action.params)})"
                self.console.print(f"[yellow]{result}[/]")
                self.trace.record(EventType.ACTION, action=action.action, params=action.params, dry_run=True)
                self.trace.record(EventType.RESULT, result=result)
            else:
                self.console.print("[blue]Executing...[/]")
                self.trace.record(EventType.ACTION, action=action.action, params=action.params)
                try:
                    result = self.tool_registry.execute(action.action, action.params)
                except Exception as e:
                    result = f"ERROR: {e}"
                    self.trace.record(EventType.ERROR, error=str(e))

                self.policy_engine.record_action()
                self.console.print(f"[green]Result:[/]\n{self.redactor.redact(result)}")
                self.trace.record(EventType.RESULT, result=result)

            self.history.append({
                "action": action.action,
                "params": action.params,
                "result": result,
            })
        else:
            self.console.print(
                f"[bold red]Max iterations ({MAX_ITERATIONS}) reached. Stopping.[/]"
            )
            self.trace.finish("max_iterations")

        self.trace.print_summary(self.console)
        return self.trace
