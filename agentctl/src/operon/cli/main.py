from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from operon import __version__

app = typer.Typer(
    name="agentctl",
    help="Operon Agent Runner — define goals, execute with control.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    spec: str = typer.Argument(..., help="Path to agent YAML spec"),
    input: Optional[list[str]] = typer.Option(
        None, "--input", "-i", help="Input values as key=value"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate the full loop without executing actions"
    ),
) -> None:
    """Run an agent from a YAML spec."""
    from operon.agent.runner import AgentRunner

    inputs: dict[str, str] = {}
    if input:
        for item in input:
            if "=" not in item:
                console.print(f"[red]Invalid input format: {item} (expected key=value)[/]")
                raise typer.Exit(1)
            key, _, value = item.partition("=")
            inputs[key] = value

    try:
        runner = AgentRunner()
        runner.run(spec, inputs if inputs else None, dry_run=dry_run)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    spec: str = typer.Argument(..., help="Path to agent YAML spec"),
) -> None:
    """Validate an agent YAML spec without running it."""
    import yaml
    from pathlib import Path
    from operon.agent.spec import AgentDefinition

    try:
        raw = yaml.safe_load(Path(spec).read_text())
        definition = AgentDefinition(**raw)
        console.print(f"[green]Valid:[/] {definition.metadata.name} ({definition.metadata.version})")
    except Exception as e:
        console.print(f"[bold red]Invalid spec:[/] {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show agentctl version."""
    console.print(f"agentctl v{__version__}")


if __name__ == "__main__":
    app()
