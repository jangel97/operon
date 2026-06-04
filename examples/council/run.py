#!/usr/bin/env python3
"""Council of the Wise — multi-model debate via agentctl serve."""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"

OLLAMA_BASE_URL = "http://192.168.1.139:11434/v1"

PANELISTS = {
    "panelist-1": "qwen3:14b",
    "panelist-2": "granite3.3:8b",
    "panelist-3": "gemma2:9b",
}

MODERATOR_MODEL = "qwen3:14b"


def check_models() -> None:
    ollama_api = OLLAMA_BASE_URL.replace("/v1", "")
    try:
        resp = requests.get(f"{ollama_api}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Cannot reach Ollama at {ollama_api}: {e}")
        sys.exit(1)

    available = {m["name"] for m in resp.json().get("models", [])}
    required = {MODERATOR_MODEL} | set(PANELISTS.values())
    missing = required - available

    if missing:
        print(f"ERROR: Models not found on Ollama: {', '.join(sorted(missing))}")
        print(f"Pull them with: {' && '.join(f'ollama pull {m}' for m in sorted(missing))}")
        sys.exit(1)


def render_specs(tmpdir: str, max_turns: int) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), keep_trailing_newline=True)

    panelist_tpl = env.get_template("panelist.yaml.j2")
    moderator_tpl = env.get_template("moderator.yaml.j2")

    panelists = []
    for name, model in PANELISTS.items():
        rendered = panelist_tpl.render(
            name=name,
            model=model,
            ollama_base_url=OLLAMA_BASE_URL,
        )
        path = os.path.join(tmpdir, f"{name}.yaml")
        with open(path, "w") as f:
            f.write(rendered)
        panelists.append({"name": name, "model": model, "spec_path": path})

    moderator_path = os.path.join(tmpdir, "moderator.yaml")
    rendered = moderator_tpl.render(
        panelists=panelists,
        max_turns=max_turns,
        max_actions=len(PANELISTS) * max_turns + 5,
        moderator_model=MODERATOR_MODEL,
        ollama_base_url=OLLAMA_BASE_URL,
    )
    with open(moderator_path, "w") as f:
        f.write(rendered)

    return moderator_path


def main():
    parser = argparse.ArgumentParser(description="Council of the Wise")
    parser.add_argument("question", nargs="?", default="What came first, the egg or the chicken?")
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    check_models()

    with tempfile.TemporaryDirectory(prefix="council-") as tmpdir:
        moderator_path = render_specs(tmpdir, args.max_turns)

        print("=== Council of the Wise ===")
        print(f"Question: {args.question}")
        print(f"Panelists: {', '.join(f'{n} ({m})' for n, m in PANELISTS.items())}")
        print(f"Moderator: {MODERATOR_MODEL}")
        print(f"Max turns: {args.max_turns}")
        print()

        print("Starting API server...")
        serve = subprocess.Popen(
            ["agentctl", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def cleanup(*_):
            serve.terminate()
            serve.wait()

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        serve_url = os.environ.get("OPERON_SERVE_URL", "http://localhost:8080")
        for _ in range(30):
            time.sleep(0.5)
            try:
                if requests.get(f"{serve_url}/healthz", timeout=2).ok:
                    break
            except requests.RequestException:
                pass
        else:
            print("ERROR: API server did not start")
            cleanup()
            sys.exit(1)

        try:
            cmd = ["agentctl", "run", moderator_path, "--set", f"question={args.question}"]
            if args.dry_run:
                cmd.append("--dry-run")
            subprocess.run(cmd)
        finally:
            cleanup()


if __name__ == "__main__":
    main()
