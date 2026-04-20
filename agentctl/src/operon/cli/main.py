from __future__ import annotations

import json
import sys
from enum import IntEnum
from typing import Optional

import typer
from rich.console import Console

from operon import __version__

app = typer.Typer(
    name="agentctl",
    help="Operon Agent Runner — define goals, execute with control.",
    no_args_is_help=True,
)


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    AGENT_FAILURE = 2
    POLICY_DENIED = 3
    MAX_ITERATIONS = 4


_STATUS_EXIT_MAP = {
    "completed": ExitCode.SUCCESS,
    "failed": ExitCode.AGENT_FAILURE,
    "policy_denied": ExitCode.POLICY_DENIED,
    "max_iterations": ExitCode.MAX_ITERATIONS,
}


@app.command()
def run(
    spec: str = typer.Argument(..., help="Path to agent YAML spec"),
    set_var: Optional[list[str]] = typer.Option(
        None, "--set", "-e", help="Set input values as key=value (repeatable)",
    ),
    set_file: Optional[str] = typer.Option(
        None, "--set-file", help="Load input values from a YAML file",
    ),
    output: str = typer.Option(
        "rich", "--output", "-o", help="Output format: rich, json, or ndjson",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate the full loop without executing actions",
    ),
) -> None:
    """Run an agent from a YAML spec."""
    from pathlib import Path

    import yaml

    from operon.agent.runner import AgentRunner

    quiet = output in ("json", "ndjson")
    console = Console(quiet=quiet)

    on_event = None
    if output == "ndjson":
        on_event = _ndjson_emitter

    inputs: dict[str, str] = {}

    if set_file:
        file_path = Path(set_file)
        if not file_path.exists():
            _error(console, quiet, f"Set file not found: {set_file}")
            raise typer.Exit(ExitCode.ERROR)
        file_data = yaml.safe_load(file_path.read_text()) or {}
        if isinstance(file_data, dict):
            inputs.update({k: str(v) for k, v in file_data.items()})

    if set_var:
        for item in set_var:
            if "=" not in item:
                _error(console, quiet, f"Invalid format: {item} (expected key=value)")
                raise typer.Exit(ExitCode.ERROR)
            key, _, value = item.partition("=")
            inputs[key] = value

    try:
        runner = AgentRunner(console=console, on_event=on_event)
        trace = runner.run(spec, inputs if inputs else None, dry_run=dry_run)
    except Exception as e:
        _error(console, quiet, str(e))
        raise typer.Exit(ExitCode.ERROR)

    if output == "json":
        json.dump(trace.to_dict(), sys.stdout, indent=2)
        print()

    raise typer.Exit(_STATUS_EXIT_MAP.get(trace.status, ExitCode.ERROR))


@app.command()
def validate(
    spec: str = typer.Argument(..., help="Path to agent YAML spec"),
) -> None:
    """Validate an agent YAML spec without running it."""
    import yaml
    from pathlib import Path
    from operon.agent.spec import AgentDefinition

    console = Console()
    try:
        raw = yaml.safe_load(Path(spec).read_text())
        definition = AgentDefinition(**raw)
        console.print(f"[green]Valid:[/] {definition.metadata.name} ({definition.metadata.version})")
    except Exception as e:
        console.print(f"[bold red]Invalid spec:[/] {e}")
        raise typer.Exit(ExitCode.ERROR)


@app.command()
def version() -> None:
    """Show agentctl version."""
    Console().print(f"agentctl v{__version__}")


def _ndjson_emitter(event: dict) -> None:
    json.dump(event, sys.stdout, default=str)
    print(flush=True)


def _error(console: Console, quiet: bool, message: str) -> None:
    if quiet:
        json.dump({"error": message}, sys.stdout)
        print()
    else:
        console.print(f"[bold red]Error:[/] {message}")


if __name__ == "__main__":
    app()
