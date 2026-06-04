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
    from operon.agent.secrets import resolve_env_vars
    from operon.agent.spec import AgentDefinition
    from operon.tools import _discover_tools, _tools

    console = Console()
    try:
        raw_text = Path(spec).read_text()
        resolved = resolve_env_vars(raw_text)
        raw = yaml.safe_load(resolved)
        definition = AgentDefinition(**raw)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/] File not found: {spec}")
        raise typer.Exit(ExitCode.ERROR)
    except Exception as e:
        console.print(f"[bold red]Invalid spec:[/] {e}")
        raise typer.Exit(ExitCode.ERROR)

    console.print(f"[green]Valid:[/] {definition.metadata.name} ({definition.metadata.version})")

    warnings: list[str] = []

    _discover_tools()
    for tool_spec in definition.spec.actions.tools:
        if tool_spec.type not in _tools:
            warnings.append(f"Tool type '{tool_spec.type}' is not installed")

    from operon.tools.collections import resolve_collection
    for coll_spec in definition.spec.actions.collections:
        try:
            tool_types = resolve_collection(coll_spec.name, known_tools=set(_tools.keys()))
            if not tool_types:
                warnings.append(f"Collection '{coll_spec.name}' resolved to zero tools")
        except ValueError as e:
            warnings.append(str(e))

    required_inputs = [
        name for name, inp in definition.spec.inputs.items()
        if inp.default is None
    ]
    if required_inputs:
        console.print(f"[dim]Required inputs:[/] {', '.join(required_inputs)}")

    if warnings:
        for w in warnings:
            console.print(f"[yellow]Warning:[/] {w}")
        raise typer.Exit(ExitCode.ERROR)

    console.print("[green]All checks passed.[/]")


@app.command()
def install(
    name: str = typer.Argument(..., help="Tool or collection name to install"),
) -> None:
    """Install a tool or collection."""
    import subprocess

    console = Console()

    collection_pkg = f"operon-collection-{name}"
    tool_pkg = f"operon-tool-{name}"

    for pkg in [collection_pkg, tool_pkg]:
        console.print(f"[dim]Trying: pip install {pkg}[/]")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(f"[green]Installed:[/] {pkg}")
            return

    console.print(f"[bold red]Error:[/] Could not find package for '{name}'")
    console.print(f"  Tried: {collection_pkg}, {tool_pkg}")
    raise typer.Exit(ExitCode.ERROR)


@app.command()
def build(
    file: str = typer.Option(
        "execution-environment.yml",
        "--file", "-f",
        help="Path to EE definition file",
    ),
    tag: str = typer.Option(
        "operon-ee:latest",
        "--tag", "-t",
        help="Image tag",
    ),
    runtime: str = typer.Option(
        "docker",
        "--runtime",
        help="Container runtime: docker or podman",
    ),
    generate_only: bool = typer.Option(
        False,
        "--generate-only",
        help="Print the Containerfile without building",
    ),
) -> None:
    """Build an Execution Environment container image."""
    from pathlib import Path

    from operon.ee.builder import build_image, generate_containerfile
    from operon.ee.spec import load_ee_definition

    console = Console()

    ee_path = Path(file)
    if not ee_path.exists():
        console.print(f"[bold red]Error:[/] EE definition not found: {file}")
        raise typer.Exit(ExitCode.ERROR)

    try:
        ee = load_ee_definition(ee_path)
    except Exception as e:
        console.print(f"[bold red]Invalid EE definition:[/] {e}")
        raise typer.Exit(ExitCode.ERROR)

    if runtime not in ("docker", "podman"):
        console.print(f"[bold red]Error:[/] Unsupported runtime: {runtime}")
        raise typer.Exit(ExitCode.ERROR)

    if generate_only:
        console.print(generate_containerfile(ee))
        return

    console.print(f"[bold]Building EE:[/] {tag}")
    console.print(f"[dim]Base image:[/] {ee.build.base_image}")
    console.print(f"[dim]Runtime:[/] {runtime}")

    tool_count = len(ee.dependencies.tools)
    coll_count = len(ee.dependencies.collections)
    go_count = len(ee.dependencies.golang)
    if tool_count or coll_count or go_count:
        console.print(
            f"[dim]Dependencies:[/] {tool_count} tools, {coll_count} collections, {go_count} go packages"
        )

    exit_code = build_image(ee, tag=tag, runtime=runtime)
    if exit_code != 0:
        console.print(f"[bold red]Build failed[/] (exit code {exit_code})")
        raise typer.Exit(ExitCode.ERROR)

    console.print(f"[green]Built:[/] {tag}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Bind address"),
    port: int = typer.Option(8080, "--port", "-p", help="Bind port"),
) -> None:
    """Start the agentctl API server."""
    try:
        import uvicorn
    except ImportError:
        Console().print(
            "[bold red]Error:[/] Server dependencies not installed.\n"
            'Install with: [bold]pip install "operon[serve]"[/]'
        )
        raise typer.Exit(ExitCode.ERROR)

    from operon.api.server import create_app as _create_app

    Console().print(f"[bold]Starting Operon API server[/] on {host}:{port}")
    uvicorn.run(_create_app(), host=host, port=port, log_level="info")


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
