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

# Run with custom inputs
agentctl run agent.yaml -i namespace=production

# Dry run — simulate without executing actions
agentctl run agent.yaml --dry-run

# Validate a spec without running
agentctl validate agent.yaml

# Show version
agentctl version
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

  # LLM configuration
  decision:
    type: llm
    provider: ollama              # ollama or openai
    model: qwen3:14b
    base_url: http://host:11434/v1  # optional, for remote Ollama

  # Runtime inputs (can be overridden with -i flag)
  inputs:
    namespace:
      type: string
      default: default

  # Tools the agent can use
  tools:
    - name: kubernetes
      type: k8s

  # Policy — what the agent is allowed to do
  policy:
    mode: approval_required       # approval_required | autonomous | read_only

    allowed_actions:              # whitelist of permitted actions
      - list_pods
      - restart_pod

    constraints:
      max_actions: 5              # hard limit on total actions per run
```

### Spec Reference

| Field | Description |
|-------|-------------|
| `spec.goal` | Natural language description of what the agent should accomplish |
| `spec.decision.provider` | LLM provider: `openai` or `ollama` |
| `spec.decision.model` | Model name (e.g., `gpt-4o-mini`, `qwen3:14b`) |
| `spec.decision.base_url` | Optional base URL for the LLM API |
| `spec.inputs` | Key-value inputs with types and optional defaults |
| `spec.tools` | List of tool types the agent can use |
| `spec.policy.mode` | `approval_required` (human approves each action), `autonomous` (no approval), `read_only` (future) |
| `spec.policy.allowed_actions` | Whitelist of actions the agent may execute |
| `spec.policy.constraints.max_actions` | Maximum number of actions per run |

## LLM Providers

### Ollama (local/remote)

No API key needed. Requires Ollama running with a model pulled.

```yaml
decision:
  type: llm
  provider: ollama
  model: qwen3:14b
  base_url: http://192.168.1.137:11434/v1   # remote
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

## Decision Schema

The LLM returns structured decisions:

```json
{
  "done": false,
  "action": "restart_pod",
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
 1  DECISION       2026-04-20T20:06:09.569    list_pods — identify failing pods (confidence: 1.0)
 2  POLICY_CHECK   2026-04-20T20:06:09.569    ALLOWED (approval required)
 3  APPROVAL       2026-04-20T20:06:21.661    approved
 4  ACTION         2026-04-20T20:06:21.662    list_pods({'namespace': 'default'})
 5  RESULT         2026-04-20T20:06:21.664    Pods in namespace 'default': ...
 ...
```

Event types: `DECISION`, `POLICY_CHECK`, `APPROVAL`, `ACTION`, `RESULT`, `ERROR`, `DONE`

## Policy Modes

| Mode | Behavior |
|------|----------|
| `approval_required` | Every action requires human approval (y/n prompt) |
| `autonomous` | Actions execute without approval |
| `read_only` | Planned — only allow read operations |

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

Tools are **separate pip packages** — agentctl ships with no tools bundled. It discovers installed tools automatically via Python entry points.

```
operon/
├── agentctl/                        # runtime (no tools)
└── tools/
    └── operon-tool-k8s/             # separate package
```

### Installing a tool

```bash
pip install operon-tool-k8s
# or from source:
pip install -e tools/operon-tool-k8s
```

Once installed, agentctl discovers it automatically — no configuration needed.

### Creating a new tool

1. Create a new package (e.g., `operon-tool-aws/`):

```
operon-tool-aws/
├── pyproject.toml
└── src/
    └── operon_tool_aws/
        ├── __init__.py
        └── tool.py
```

2. Implement the `Tool` interface in `tool.py`:

```python
from operon.tools.base import Tool

class AwsTool(Tool):
    @property
    def name(self) -> str:
        return "aws"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "list_instances",
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
from operon_tool_aws.tool import AwsTool
__all__ = ["AwsTool"]
```

4. Register via entry point in `pyproject.toml`:

```toml
[project]
name = "operon-tool-aws"
version = "0.1.0"
dependencies = ["operon>=0.1.0"]

[project.entry-points."operon.tools"]
aws = "operon_tool_aws:AwsTool"

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
  - name: aws
    type: aws
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
