# Operon

THIS IS A PILOT.

**Agentic Automation Platform** — define goals, not procedures.

Operon lets you define autonomous agents in YAML. You declare the goal and the tools — the agent figures out the steps. A deterministic policy layer enforces what the agent can and can't do before anything executes.

```yaml
apiVersion: agents/v1
kind: Agent
metadata:
  name: k8s-investigator
spec:
  goal: |
    Investigate the health of namespace "{{namespace}}".
    Check for unhealthy pods, get logs, and restart if needed.

  decision:
    type: llm
    provider: ollama
    model: qwen3:14b
    base_url: http://localhost:11434/v1

  inputs:
    namespace:
      type: string
      default: default

  actions:
    collections:
      - k8s-readonly
    tools:
      - k8s-restarter:
          approval: required

  policy:
    constraints:
      max_actions: 10
```

The agent reads pods, checks events, pulls logs — whatever the situation requires. It can restart, but only with human approval. No DAG to draw, no branches to predefine.

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-org/operon.git && cd operon
python3 -m venv .venv && source .venv/bin/activate
pip install -e agentctl/ -e tools/operon-tool-websearch/

# Run an agent
agentctl run agentctl/examples/agent-research.yaml \
  --set question="What is Operon?"
```

The research agent uses web search to find information, fetches relevant pages, and synthesizes a summary. No configuration beyond the YAML.

### More examples

```bash
# Weather via web search
agentctl run agentctl/examples/agent-websearch-weather.yaml \
  --set city="Barcelona, Spain"

# K8s investigation (requires kubectl configured + k8s tools installed)
pip install -e tools/operon-collection-k8s-readonly/
agentctl run agentctl/examples/agent-kubectl.yaml \
  --set namespace=production

# GitHub triage (requires gh CLI authenticated)
pip install -e tools/operon-tool-github/
agentctl run agentctl/examples/agent-github-triage.yaml \
  --set repo=myorg/myrepo

# Stream events as NDJSON
agentctl run agentctl/examples/agent-research.yaml -o ndjson \
  --set question="..."
```

## How It Works

```
┌──────────────┐
│  Agent YAML  │  goal + actions + policy
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│              Agent Loop                   │
│                                          │
│  LLM Decides ──▶ Policy Check ──▶ Execute │
│       ▲                              │    │
│       └──────── Observe Result ◀─────┘    │
│                                          │
│  LLM Decides ──▶ Done                    │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│    Trace     │  every step recorded
└──────────────┘
```

1. The LLM reads the goal and available actions, picks an action
2. The policy engine checks: is this action registered? Under max actions? Matches a denied pattern? Needs approval?
3. If allowed, the tool executes and the result goes back to the LLM
4. The LLM observes and decides the next step — or declares done
5. Every decision, policy check, and result is recorded in the trace

The model proposes. The deterministic layer enforces.

## Agent Spec

### Actions

The `actions` block declares what the agent can do. Two sub-keys: `collections` for curated bundles, `tools` for individual tools.

```yaml
actions:
  collections:
    - k8s-readonly                    # 7 read-only k8s tools
  tools:
    - k8s-restarter:
        approval: required            # human confirms each restart
    - websearch                       # no approval needed (read-only)
```

No `allowed_actions` whitelist. No global mode. The tool list IS the permission model.

### Per-tool approval

| Value | Behavior |
|-------|----------|
| `required` | Human confirms each action from this tool |
| `none` | Executes without confirmation |
| Omitted | Default: read tools → none, write tools → required |

### Policy

```yaml
policy:
  constraints:
    max_actions: 10                   # hard cap on actions per run
    denied_patterns:                  # regex patterns that block execution
      - "--force"
      - "rm\\s+-rf"
```

## Tools

Tools are pip packages discovered automatically via entry points. Each tool does one thing and its blast radius is obvious from the name.

```
operon-tool-k8s-pod-reader         # get_pods, describe_pod
operon-tool-k8s-log-reader         # get_logs
operon-tool-k8s-restarter          # rollout_restart (write)
operon-tool-k8s-scaler             # scale_deployment (write)
operon-tool-websearch              # web_search, web_fetch
operon-tool-github                 # issues, PRs, CI, releases
```

**Install = opt-in.** No write tool installed = no writes possible.

### Collections

A collection is a curated bundle of tools. Install one package, get all the tools for a use case.

```bash
# Install all k8s read-only tools (7 tools)
pip install operon-collection-k8s-readonly

# Install k8s SRE tools (readonly + restarter + pod-deleter)
pip install operon-collection-k8s-sre
```

Use collections in agent specs:

```yaml
actions:
  collections:
    - k8s-readonly
    - github-triage:
        approval: required
```

### Building a tool

A tool is a Python class with three methods:

```python
from operon.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my-tool"

    def actions(self) -> list[dict]:
        return [{"name": "do_thing", "type": "read", "description": "...", "params": {}}]

    def execute(self, action: str, params: dict) -> str:
        return "result"
```

Register it via entry points in `pyproject.toml`:

```toml
[project.entry-points."operon.tools"]
my-tool = "my_package:MyTool"
```

## LLM Providers

Operon works with any OpenAI-compatible API.

```yaml
# Ollama (local or remote)
decision:
  type: llm
  provider: ollama
  model: qwen3:14b
  base_url: http://localhost:11434/v1

# OpenAI
decision:
  type: llm
  provider: openai
  model: gpt-4o-mini
```

### Two-model architecture

Use a capable model for reasoning and a smaller one for extracting structured output:

```yaml
decision:
  type: llm
  provider: ollama
  model: qwen3:14b
  base_url: http://localhost:11434/v1
  extractor:
    model: qwen3:4b
```

## CLI Reference

```bash
agentctl run <spec.yaml>              # Run an agent
agentctl run <spec> --set key=value   # Run with inputs
agentctl run <spec> --dry-run         # Simulate without executing
agentctl run <spec> -o json           # Output trace as JSON
agentctl run <spec> -o ndjson         # Stream events as NDJSON
agentctl validate <spec.yaml>         # Validate a spec
agentctl install <name>               # Install a tool or collection
agentctl serve                        # Start the API server
agentctl version                      # Show version
```

## API Server

`agentctl serve` exposes a REST API for running agents programmatically.

```bash
agentctl serve --host 0.0.0.0 --port 8080
```

```bash
# Start a run
curl -X POST http://localhost:8080/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"spec": "agent.yaml", "inputs": {"namespace": "production"}}'

# Check status
curl http://localhost:8080/api/v1/runs/<run_id>

# Stream events
curl http://localhost:8080/api/v1/runs/<run_id>/events
```

## Testing

```bash
source .venv/bin/activate
pip install -e "agentctl/[dev]"
pytest agentctl/tests/ -v
```

## Project Structure

```
operon/
├── agentctl/                         # Core runtime (CLI + engine)
├── tools/
│   ├── operon-tool-k8s-pod-reader/   # Fine-grained tool packages
│   ├── operon-tool-k8s-log-reader/
│   ├── operon-tool-k8s-restarter/
│   ├── operon-tool-websearch/
│   ├── operon-tool-github/
│   ├── operon-collection-k8s-readonly/  # Tool collections
│   ├── operon-collection-k8s-sre/
│   └── docs/tool-design.md           # Tool design guide
├── examples/
│   └── council/                      # Multi-agent debate demo
└── docs/
    ├── architecture.md
    └── product/
```

## Documentation

| Document | Description |
|----------|-------------|
| [Tool Design Guide](tools/docs/tool-design.md) | Granularity, naming, collections, ecosystem map |
| [Architecture](docs/architecture.md) | Agent loop, data flow, plugin system, policy engine |
| [agentctl README](agentctl/README.md) | Full runtime documentation |

## License

Apache 2.0
