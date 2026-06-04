# agentctl

The Operon Agent Runner. A CLI runtime that loads declarative agent specs (YAML), runs an LLM-powered decision loop, enforces policies, and produces a full execution trace.

## What it does

```
agentctl run agent.yaml
```

1. Loads the agent spec (goal, tools, policy, LLM provider)
2. Runs the loop: **decide → policy check → approve → execute → observe**
3. Repeats until the goal is achieved or limits are reached
4. Outputs a full execution trace (every decision, check, and action)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Run an agent
agentctl run examples/agent-ollama.yaml

# Override inputs (like ansible -e)
agentctl run agent.yaml -e namespace=production
agentctl run agent.yaml --set city="Barcelona, Spain"

# Load inputs from a YAML file
agentctl run agent.yaml --set-file vars.yaml

# Both — file values are loaded first, CLI overrides take precedence
agentctl run agent.yaml --set-file defaults.yaml -e namespace=staging

# Dry run — simulate without executing actions
agentctl run agent.yaml --dry-run

# JSON output — machine-readable trace for automation
agentctl run agent.yaml -o json
agentctl run agent.yaml -o json | jq .status

# NDJSON streaming — real-time events for control planes
agentctl run agent.yaml -o ndjson
agentctl run agent.yaml -o ndjson | jq 'select(.type == "DECISION")'

# Validate a spec without running
agentctl validate agent.yaml

# Start the API server
agentctl serve --port 8080

# Show version
agentctl version
```

## Exit Codes

Meaningful exit codes for scripting and automation:

| Code | Status | Description |
|------|--------|-------------|
| `0` | `completed` | Agent achieved its goal |
| `1` | — | Generic error (bad spec, missing file, invalid inputs) |
| `2` | `failed` | Agent failure (LLM error, tool error, connection timeout) |
| `3` | `policy_denied` | Agent blocked by policy |
| `4` | `max_iterations` | Agent hit the iteration limit without completing |

```bash
agentctl run agent.yaml && echo "done" || echo "failed: $?"
```

## Agent Spec

Agents are defined in YAML. The spec declares **what** the agent should do and **what it's allowed to do**.

```yaml
apiVersion: agents/v1
kind: Agent

metadata:
  name: app-health-recovery
  version: v1

spec:
  # What the agent should accomplish
  goal: |
    Detect application failures and recover safely.

  # LLM configuration (supports ${ENV_VAR} interpolation)
  decision:
    type: llm
    provider: ollama              # ollama or openai
    model: qwen3:14b
    base_url: ${OLLAMA_URL}       # resolved from environment
    extractor:                    # optional: small model for reliable JSON extraction
      model: llama3.1:8b

  # Runtime inputs (override with --set/-e or --set-file)
  inputs:
    namespace:
      type: string
      default: default
    api_token:
      type: string
      no_log: true                # value redacted from all output
      default: ${API_TOKEN:-}

  # Tools the agent can use (tools define CAPABILITY)
  tools:
    - name: kubectl
      type: kubectl

  # Policy — what the agent is allowed to do (policy defines PERMISSIONS)
  policy:
    mode: approval_required       # approval_required | autonomous | read_only

    allowed_actions:              # whitelist of permitted actions (namespaced)
      - kubectl:get_pods
      - kubectl:describe_pod
      - kubectl:get_logs

    constraints:
      max_actions: 5              # hard limit on total actions per run
      denied_patterns: []         # regex patterns to block (defense in depth)
```

### Spec Reference

| Field | Description |
|-------|-------------|
| `spec.goal` | Natural language description of what the agent should accomplish |
| `spec.decision.provider` | LLM provider: `openai` or `ollama` |
| `spec.decision.model` | Model name (e.g., `gpt-4o-mini`, `qwen3:14b`) |
| `spec.decision.base_url` | Optional base URL for the LLM API |
| `spec.decision.extractor` | Optional extractor model for structured JSON extraction (see below) |
| `spec.inputs` | Key-value inputs with types, optional defaults, and `no_log` |
| `spec.inputs[].no_log` | When `true`, the input value is redacted from all output |
| `spec.tools` | List of tool types the agent can use (tools define capability) |
| `spec.policy.mode` | `approval_required` (human approves each action), `autonomous` (no approval), `read_only` (blocks write operations) |
| `spec.policy.allowed_actions` | Whitelist of namespaced actions the agent may execute (e.g., `kubectl:get_pods`) |
| `spec.policy.constraints.max_actions` | Maximum number of actions per run |
| `spec.policy.constraints.denied_patterns` | Regex patterns to block in command params |

## LLM Providers

### Ollama (local/remote)

No API key needed. Requires Ollama running with a model pulled.

```yaml
decision:
  type: llm
  provider: ollama
  model: qwen3:14b
  base_url: http://192.168.1.138:11434/v1   # remote
```

### OpenAI

Requires `OPENAI_API_KEY` environment variable.

```yaml
decision:
  type: llm
  provider: openai
  model: gpt-4o-mini
```

```bash
export OPENAI_API_KEY=sk-...
agentctl run agent.yaml
```

### Extractor (two-model architecture)

By default, the same model handles both reasoning and structured JSON output. Some models (especially reasoning-focused ones like DeepSeek-R1) produce better results when they can think freely without worrying about output format.

The `extractor` option adds a second, small model that converts the main model's raw output into structured JSON. The main model reasons freely, then the extractor reformats the response.

```yaml
decision:
  provider: ollama
  model: deepseek-r1:14b           # reasons freely
  base_url: http://192.168.1.138:11434/v1
  extractor:
    model: llama3.1:8b              # small, fast, reliable JSON output
```

The extractor inherits `provider` and `base_url` from the parent by default. Override them to use a different provider:

```yaml
decision:
  provider: ollama
  model: qwen3:14b
  base_url: http://192.168.1.138:11434/v1
  extractor:
    model: gpt-4o-mini
    provider: openai                # uses OpenAI for extraction
```

| Field | Description |
|-------|-------------|
| `extractor.model` | Model name for the extractor (required) |
| `extractor.provider` | Provider override (defaults to parent's provider) |
| `extractor.base_url` | Base URL override (defaults to parent's base_url) |

If `extractor` is omitted, the agent works exactly as before — the main model handles everything.

## Credentials

Credentials in Operon live at two levels. The agent spec never passes credentials to tools — each tool manages its own authentication independently.

### Tool credentials (authentication)

Tools consume their own credentials. The agent and the LLM never see them.

| Tool | Credential source | Setup |
|------|-------------------|-------|
| `kubectl` | kubeconfig (`~/.kube/config` or `KUBECONFIG`) | `kubectl` configured for target cluster |
| `github` | `gh` CLI auth state | `gh auth login` |
| `websearch` | None (public API) | — |

This is a security boundary: tool credentials are resolved at execution time by the tool itself, using standard system-level mechanisms (config files, environment variables, CLI auth state). The LLM decides **what** to do; the tool decides **how** to authenticate. The agent spec has no `credentials` field and no way to inject auth into a tool.

When creating a custom tool, handle authentication in your `execute()` method using whatever mechanism is appropriate (environment variables, config files, token files). The runtime will not pass credentials to you.

### Agent-level interpolation (configuration)

Agent specs support `${ENV_VAR}` interpolation in any string value. This is for agent configuration (LLM endpoints, input defaults) — not for tool authentication.

```yaml
decision:
  base_url: ${OLLAMA_URL}                    # required — fails if not set

inputs:
  db_password:
    type: string
    no_log: true                              # redacted from all output
    default: ${DB_PASSWORD:-}                 # optional — empty string if not set
```

| Syntax | Behavior |
|--------|----------|
| `${VAR}` | Resolves from environment. Fails if not set. |
| `${VAR:-default}` | Resolves from environment. Uses `default` if not set. |
| `${VAR:-}` | Resolves from environment. Empty string if not set. |

### no_log

Inputs marked with `no_log: true` have their values redacted from **all output** — console, JSON trace, NDJSON streaming, and Rich summary table. The LLM still sees the real value to reason with, but it never appears in any external output.

Redaction is **value-based**: if the secret value appears anywhere — in params, reasoning, results, or summaries — it gets replaced with `***REDACTED***`.

```bash
# The agent sees the real token, but output shows ***REDACTED***
export API_TOKEN=sk-secret-123
agentctl run agent.yaml -o json | grep REDACTED
```

### Validation

Use `agentctl validate` to check that all referenced environment variables are set:

```bash
agentctl validate agent.yaml
# Error: Environment variable not set: OLLAMA_URL
```

## Decision Schema

The LLM returns structured decisions:

```json
{
  "done": false,
  "action": "kubectl:restart_pod",
  "params": {"name": "pod-api-2", "namespace": "default"},
  "reasoning": "Pod is in CrashLoopBackOff with 5 restarts",
  "confidence": 0.95
}
```

| Field | Description |
|-------|-------------|
| `action` | Action name from the available tools |
| `params` | Parameters for the action |
| `reasoning` | Why the LLM chose this action |
| `confidence` | 0.0 (guessing) to 1.0 (certain) |

## Execution Trace

Every run produces a trace table showing what happened:

```
 #  Type           Timestamp                  Details
 1  DECISION       2026-04-20T20:06:09.569    kubectl:get_pods — identify failing pods (confidence: 1.0)
 2  POLICY_CHECK   2026-04-20T20:06:09.569    ALLOWED (approval required)
 3  APPROVAL       2026-04-20T20:06:21.661    approved
 4  ACTION         2026-04-20T20:06:21.662    kubectl:get_pods({'namespace': 'default'})
 5  RESULT         2026-04-20T20:06:21.664    Pods in namespace 'default': ...
 ...
```

Event types: `DECISION`, `POLICY_CHECK`, `APPROVAL`, `ACTION`, `RESULT`, `ERROR`, `DONE`

### JSON output

Use `-o json` for a complete trace after the run finishes:

```bash
agentctl run agent.yaml -o json
```

```json
{
  "agent": "app-health-recovery",
  "status": "completed",
  "started_at": "2026-04-20T20:06:09.000+00:00",
  "finished_at": "2026-04-20T20:06:25.000+00:00",
  "duration": "16.0s",
  "total_events": 9,
  "events": [...]
}
```

### NDJSON streaming

Use `-o ndjson` for real-time event streaming (one JSON object per line). Events are emitted as they happen — ideal for control planes, dashboards, and log aggregation:

```bash
agentctl run agent.yaml -o ndjson
```

```
{"type": "START", "agent": "researcher", "timestamp": "2026-04-20T22:04:12.828+00:00"}
{"type": "DECISION", "timestamp": "...", "action": "websearch:web_search", "reasoning": "...", "confidence": 0.9}
{"type": "POLICY_CHECK", "timestamp": "...", "action": "websearch:web_search", "allowed": true}
{"type": "ACTION", "timestamp": "...", "action": "websearch:web_search", "params": {"query": "..."}}
{"type": "RESULT", "timestamp": "...", "result": "..."}
{"type": "DONE", "timestamp": "...", "summary": "..."}
{"type": "FINISH", "agent": "researcher", "status": "completed", "duration": "13.7s", "total_events": 9}
```

## API Server

`agentctl serve` starts a REST API server for triggering and monitoring agent runs over HTTP. This is the foundation for control planes, dashboards, and CI/CD integrations.

```bash
pip install "operon[serve]"
agentctl serve --port 8080
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check |
| `POST` | `/api/v1/runs` | Submit a new agent run (returns `run_id`) |
| `GET` | `/api/v1/runs` | List all runs |
| `GET` | `/api/v1/runs/{run_id}` | Get run status and full trace |
| `GET` | `/api/v1/runs/{run_id}/events` | SSE stream of real-time events |

### Example

```bash
# Submit a run
curl -X POST http://localhost:8080/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"spec": "examples/agent-github-triage.yaml", "inputs": {"repo": "myorg/myrepo"}}'
# {"run_id": "a1b2c3d4e5f6", "status": "pending"}

# Check status
curl http://localhost:8080/api/v1/runs/a1b2c3d4e5f6

# Stream events (Server-Sent Events)
curl http://localhost:8080/api/v1/runs/a1b2c3d4e5f6/events
```

Runs execute in background threads. The API returns `202 Accepted` immediately with a `run_id` for polling or SSE streaming. Use `autonomous` or `read_only` policy modes — `approval_required` is designed for interactive CLI use.

## Policy Modes

| Mode | Behavior |
|------|----------|
| `approval_required` | Every action requires human approval (y/n prompt) |
| `autonomous` | Actions execute without approval |
| `read_only` | Blocks write operations, allows read-only actions |

Tools tag their operations as `read` or `write`. The policy engine enforces this automatically — a `read_only` agent can never execute a write operation, regardless of what the LLM decides.

## Architecture

```
spec (YAML)
  → AgentRunner (loads spec, resolves inputs)
    → AgentLoop (the core loop)
      → LLMProvider (decides next action)
      → PolicyEngine (checks if action is allowed)
      → ToolRegistry (executes the action)
      → ExecutionTrace (records everything)
```

```
src/operon/
├── cli/main.py            # Typer CLI
├── agent/
│   ├── spec.py            # Pydantic models for YAML spec
│   ├── runner.py          # Wires everything together
│   ├── loop.py            # The core decide-check-execute loop
│   └── trace.py           # Execution trace and audit
├── decision/
│   ├── __init__.py        # Provider factory (register + create)
│   ├── base.py            # LLMProvider interface + shared logic
│   ├── openai.py          # OpenAI provider
│   └── ollama.py          # Ollama provider
├── tools/
│   ├── __init__.py        # Tool factory (auto-discovers plugins)
│   └── base.py            # Tool + ToolRegistry interfaces
├── policy/
│   └── engine.py          # Policy enforcement
└── utils/
    └── logging.py         # Rich console helpers
```

## Tools (Plugin System)

Tools are **separate packages** — agentctl ships with no tools bundled. It discovers installed tools automatically via Python entry points.

### Design principle: fine-grained tools

Each tool should do one thing, and its blast radius should be obvious from the name. The operator controls what an agent can do by choosing which tools to install — not by editing policy whitelists.

```
operon/
├── agentctl/                          # runtime (no tools)
└── tools/
    ├── operon-tool-k8s-reader/        # pods, logs, events — read-only
    ├── operon-tool-k8s-scaler/        # scale deployments — write
    ├── operon-tool-k8s-restarter/     # rolling restarts — write
    ├── operon-tool-github-reader/     # issues, PRs, releases — read-only
    ├── operon-tool-github-triage/     # labels, comments — lightweight writes
    ├── operon-tool-websearch/         # web search + fetch
    └── operon-tool-weather/           # weather (mock)
```

**Install = opt-in.** If the operator installs `k8s-reader`, the agent can inspect clusters. If they also install `k8s-restarter`, the agent can do rolling restarts. No write tool installed = no writes possible.

### Installing a tool

```bash
pip install operon-tool-k8s-reader
```

Once installed, agentctl discovers it automatically — no configuration needed.

### Namespaced actions

Actions are namespaced as `tool:operation`. Tools define **capability** (what operations exist), policy defines **permissions** as defense-in-depth.

```yaml
tools:
  - name: k8s-reader
    type: k8s-reader

policy:
  allowed_actions:
    - k8s-reader:get_pods
    - k8s-reader:describe_pod
    - k8s-reader:get_logs
```

The LLM decides:
```json
{"action": "k8s-reader:get_pods", "params": {"namespace": "production"}}
```

The tool executes: `kubectl get pods -n production -o json`

### Creating a new tool

Before writing a tool, decide its scope. Follow these guidelines:

- **One concern per tool.** A tool that reads and writes is two tools.
- **Name reveals intent.** `aws-ec2-reader`, not `aws`. `postgres-backup`, not `postgres`.
- **Default to read-only.** Most tools should be read-only. Write tools are separate packages that operators install deliberately.
- **Minimal surface area.** Fewer actions = easier to audit, easier to trust.

1. Create a new package (e.g., `operon-tool-aws-ec2-reader/`):

```
operon-tool-aws-ec2-reader/
├── pyproject.toml
└── src/
    └── operon_tool_aws_ec2_reader/
        ├── __init__.py
        └── tool.py
```

2. Implement the `Tool` interface in `tool.py`:

```python
from operon.tools.base import Tool

class AwsEc2ReaderTool(Tool):
    @property
    def name(self) -> str:
        return "aws-ec2-reader"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "list_instances",
                "type": "read",
                "description": "List EC2 instances",
                "params": {"region": "string"},
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        if action == "list_instances":
            # call AWS API
            ...
```

3. Export it in `__init__.py`:

```python
from operon_tool_aws_ec2_reader.tool import AwsEc2ReaderTool
__all__ = ["AwsEc2ReaderTool"]
```

4. Register via entry point in `pyproject.toml`:

```toml
[project]
name = "operon-tool-aws-ec2-reader"
version = "0.1.0"
dependencies = ["operon>=0.1.0"]

[project.entry-points."operon.tools"]
aws-ec2-reader = "operon_tool_aws_ec2_reader:AwsEc2ReaderTool"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

5. Install and use:

```bash
pip install -e .
```

```yaml
tools:
  - name: aws-ec2-reader
    type: aws-ec2-reader
```

agentctl will discover it on next run. No changes to agentctl code needed.

## Adding a New LLM Provider

Providers are registered in `agentctl/src/operon/decision/__init__.py`.

1. Create `src/operon/decision/your_provider.py`:

```python
from .base import LLMProvider

class YourProvider(LLMProvider):
    def __init__(self, model: str = "default-model"):
        self.model = model
        # init your client

    def _call_llm(self, messages: list[dict]) -> str:
        # call your API, return raw response text
        ...
```

2. Register in `src/operon/decision/__init__.py`:

```python
from operon.decision.your_provider import YourProvider
register_provider("your_provider", YourProvider)
```

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

The test suite covers the safety-critical components with no external dependencies (no LLM calls, no network):

| Test file | What it covers |
|-----------|----------------|
| `test_policy_engine.py` | All three policy modes, allowed actions, max actions, denied patterns, write escalation, check evaluation order |
| `test_extract_json.py` | Clean JSON, code fences, surrounding text, garbage fallback, edge cases |
| `test_tool_registry.py` | Namespacing, allowed filtering, policy mode filtering, metadata, execution routing |
| `test_github_tool.py` | Action schema, validation, command building, error handling, coercion, registry integration |
| `test_extractor.py` | Two-model architecture: spec parsing, extractor wiring, prompt construction, fallback handling |
| `test_api_server.py` | API server: endpoints, run lifecycle, SSE streaming, in-memory state store |
