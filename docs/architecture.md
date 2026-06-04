# Architecture

## Agent Loop

The core execution model. Every agent follows this loop until the goal is achieved or limits are reached.

```mermaid
flowchart TD
    START([Agent Start]) --> LOAD[Load YAML Spec]
    LOAD --> RESOLVE["Resolve Inputs\n${ENV_VAR} interpolation"]
    RESOLVE --> REGISTRY["Build Tool Registry\nDiscover plugins via entry points"]
    REGISTRY --> GOAL["Render Goal\nTemplate inputs into goal text"]
    GOAL --> DECIDE

    subgraph LOOP ["Agent Loop (max 20 iterations)"]
        DECIDE["LLM Decides\nPick action + params from\navailable actions menu"]
        DECIDE -->|done: true| DONE
        DECIDE -->|done: false| POLICY

        POLICY{"Policy Check"}
        POLICY -->|denied| DENIED["Record denial\nFeed back to LLM"]
        DENIED --> DECIDE
        POLICY -->|allowed + approval required| APPROVAL
        POLICY -->|allowed| EXECUTE

        APPROVAL{"Operator Approval"}
        APPROVAL -->|rejected| REJECTED["Record rejection\nFeed back to LLM"]
        REJECTED --> DECIDE
        APPROVAL -->|approved| EXECUTE

        EXECUTE["Execute Action\nTool builds & runs command"]
        EXECUTE --> RESULT["Record Result\nFeed back to LLM"]
        RESULT --> DECIDE
    end

    DONE([Goal Achieved]) --> TRACE
    TRACE["Output Trace\nRich table / JSON / NDJSON"]

    style POLICY fill:#f9f,stroke:#333
    style EXECUTE fill:#bbf,stroke:#333
    style DONE fill:#bfb,stroke:#333
    style DENIED fill:#fbb,stroke:#333
```

## Decision Engine — Three-Layer Architecture

The decision engine supports three optional layers, each configurable with its own model, provider, and temperature:

```mermaid
flowchart LR
    TOOLS["All Actions\n(from registry)"]
    ROUTER["Router\n(cheap/fast model)\nFilters relevant actions"]
    REASONER["Reasoner\n(main model)\nPicks action + params"]
    EXTRACTOR["Extractor\n(cheap/fast model)\nCleans JSON output"]
    DECISION["Decision\naction + params\nor done"]

    TOOLS --> ROUTER
    ROUTER -->|"filtered actions"| REASONER
    REASONER -->|"raw text"| EXTRACTOR
    EXTRACTOR --> DECISION

    style ROUTER fill:#ffe0b2,stroke:#333
    style REASONER fill:#bbdefb,stroke:#333
    style EXTRACTOR fill:#c8e6c9,stroke:#333
```

**Router** (optional): A fast model that receives the goal, action names/descriptions, and recent history. Returns a subset of relevant actions. Reduces noise for the reasoner when many tools are registered. Falls back to the full action list on failure.

**Reasoner** (required): The main model. Receives the goal, actions (filtered or full), and execution history. Decides what to do next.

**Extractor** (optional): A fast model that takes the reasoner's raw output and extracts clean JSON. Useful when the reasoner model doesn't reliably produce structured output.

Each layer can have its own `provider`, `model`, `base_url`, and `temperature`:

```yaml
decision:
  type: llm
  provider: ollama
  model: qwen3:14b
  base_url: http://192.168.1.139:11434/v1
  temperature: 0.7
  max_history: 5              # trim old history for small-context models

  router:
    model: qwen3:1.7b
    temperature: 0.3

  extractor:
    model: qwen3:1.7b
    temperature: 0.1
```

Router and extractor inherit `provider` and `base_url` from the top level if not specified. `max_history` limits how many past actions are sent to the LLM — only the most recent N entries are included. All layers are optional — the simplest config is just `provider` + `model`, which acts as the reasoner.

## Data Flow

How data moves through the system, and where redaction happens.

```mermaid
flowchart LR
    subgraph INPUT ["Input"]
        YAML["Agent YAML\n+ ${ENV_VAR}"]
        CLI["CLI flags\n--set / --set-file"]
    end

    subgraph CORE ["Core Runtime"]
        RUNNER["AgentRunner\nResolve inputs\nBuild registry"]
        LOOP["AgentLoop\nDecide → Check → Execute"]
        LLM["LLM Provider\nOllama / OpenAI"]
        TOOLS["Tool Registry\nNamespaced actions"]
        POLICY_E["Policy Engine\nMode / Allowed / Denied"]
    end

    subgraph OUTPUT ["Output (Redacted)"]
        CONSOLE["Console\nRich tables"]
        JSON_OUT["JSON\nFull trace"]
        NDJSON["NDJSON\nStreaming events"]
    end

    YAML --> RUNNER
    CLI --> RUNNER
    RUNNER --> LOOP
    LOOP <--> LLM
    LOOP <--> TOOLS
    LOOP <--> POLICY_E
    LOOP -->|"Redactor\n(no_log values)"| CONSOLE
    LOOP -->|"Redactor"| JSON_OUT
    LOOP -->|"Redactor"| NDJSON

    style OUTPUT fill:#ffe,stroke:#333
```

## Tool Design Philosophy

Operon is opinionated about tools: **each tool should do one thing, and its blast radius should be obvious from the name.**

The operator controls what an agent can do by choosing which tools to install — not by editing policy whitelists. If the operator doesn't install a write tool, the agent can't write. Policy exists as defense-in-depth, not as the primary control.

```
Good: fine-grained, obvious blast radius
├── operon-tool-k8s-reader        # pods, logs, events — can't break anything
├── operon-tool-k8s-scaler        # scale deployments — clearly a write tool
├── operon-tool-k8s-restarter     # rolling restarts only
├── operon-tool-github-reader     # issues, PRs, releases — read-only
├── operon-tool-github-triage     # add labels, comment — lightweight writes
└── operon-tool-github-merge      # merge PRs — powerful, opt-in

Bad: broad tools that hide dangerous operations
└── operon-tool-kubectl           # 14 operations, mix of read and write
```

### Why fine-grained?

1. **Install = opt-in.** The operator installs `k8s-reader` for an investigator agent. No risk of accidental writes — the tool simply can't do them.
2. **Auditable from the outside.** `pip list | grep operon-tool` shows exactly what an agent can do. No need to read YAML policy to understand the blast radius.
3. **Composable.** An incident response recipe depends on `k8s-reader` + `k8s-restarter`. A monitoring recipe depends on `k8s-reader` only. Each recipe declares the minimum tools it needs.
4. **Community-friendly.** Tool authors build small, focused packages. Reviewers can audit a 50-line tool, not a 500-line Swiss Army knife.

### Guidelines for tool authors

- **One concern per tool.** A tool that reads and writes is two tools.
- **Name reveals intent.** `k8s-reader`, not `k8s`. `github-merge`, not `github`.
- **Default to read-only.** Most tools should be read-only. Write tools are separate packages that operators install deliberately.
- **Minimal surface area.** Fewer actions = easier to audit, easier to trust.

## Tool System

Tools are discovered from two sources: **modules** (self-contained directories) and **entry points** (pip packages). Modules take precedence.

### Modules

A module is a directory with a `tool.yaml` manifest and code in Python or Go:

```
weather-reader/
├── tool.yaml       # name, runtime, actions, params
└── main.py         # execute(action, params) -> str
```

```yaml
# tool.yaml
name: weather-reader
runtime: python          # or golang
entrypoint: main.py      # or ./binary
actions:
  - name: get_weather
    type: read
    description: Get current weather for a city
    params:
      city: { type: string, required: true }
```

Modules are discovered from `OPERON_MODULES_PATH` (default: `/usr/lib/operon/modules/`). Python modules are loaded in-process; Go modules communicate via JSON over stdin/stdout.

### Per-Tool Config

Credentials and configuration can be injected into tools via the `config` field in the agent spec. Config values are merged into action params at execution time, so modules receive credentials as params rather than reading environment variables directly.

```yaml
actions:
  tools:
    - telegram-sender:
        approval: required
        config:
          bot_token: ${TELEGRAM_BOT_TOKEN}
          chat_id: ${TELEGRAM_CHAT_ID}
```

Config values are automatically added to the redactor so they don't leak in traces.

### Entry Points (fallback)

Tools can also be pip packages discovered via `operon.tools` entry points. This is the original mechanism, kept as a fallback for tools that need Python packaging.

```mermaid
flowchart TD
    subgraph DISCOVERY ["Tool Discovery (priority order)"]
        MODULES["1. Modules\nOPERON_MODULES_PATH\ntool.yaml + code"]
        EP["2. Entry Points\noperon.tools group\npip packages"]
    end

    subgraph REGISTRY ["ToolRegistry"]
        ACTIONS["Namespaced actions\ntool:action_name"]
        CONFIG["Per-tool config\nmerged into params"]
        APPROVAL["Per-tool approval\nrequired / none"]
    end

    MODULES --> REGISTRY
    EP --> REGISTRY

    style MODULES fill:#c8e6c9,stroke:#333
    style EP fill:#f0f0f0,stroke:#333
    style REGISTRY fill:#e8f4fd,stroke:#333
```

## Credential Model

Two credential patterns are supported:

**System credentials** — tools like kubectl and gh read their own auth from the environment (kubeconfig, `GH_TOKEN`). The agent spec doesn't know about these.

**Config injection** — for modules that need credentials (API tokens, chat IDs), the agent spec injects them via the `config` field. Values are resolved from `${ENV_VAR}` at load time, merged into action params at execution time, and automatically redacted from traces.

```mermaid
flowchart TD
    subgraph AGENT_SPEC ["Agent Spec (YAML)"]
        ENV_INTERP["${ENV_VAR} interpolation\nLLM endpoints, config values"]
    end

    subgraph RUNTIME ["agentctl Runtime"]
        RUNNER["AgentRunner\nResolves ${ENV_VAR}\nBuilds tool registry"]
        LOOP["AgentLoop\nLLM decides what to do"]
        REDACTOR["Redactor\nno_log + config values\n→ ***REDACTED***"]
    end

    subgraph TOOLS ["Tools"]
        MODULE["Module tool\nReceives creds via params\n(from config injection)"]
        PLUGIN["Plugin tool\nReads own auth\n(kubeconfig, gh, etc)"]
    end

    ENV_INTERP --> RUNNER
    RUNNER --> LOOP
    LOOP -->|"action + params\n(config merged in)"| MODULE
    LOOP -->|"action + params"| PLUGIN
    LOOP --> REDACTOR

    style TOOLS fill:#e0f0ff,stroke:#333
    style AGENT_SPEC fill:#f0f0f0,stroke:#333
```

The LLM decides **what** to do (action + params). It never sees credentials — config values are merged into params by the registry at execution time, after the LLM has made its decision.

## Safety Model

Safety comes from three layers: tool selection, per-tool approval, and constraints.

```mermaid
flowchart TD
    SPEC["Agent Spec\nactions:\n  collections: [k8s-readonly]\n  tools:\n    - k8s-restarter:\n        approval: required"]

    SPEC --> INSTALLED{"Tools\ninstalled?"}
    INSTALLED -->|not installed| CANT["Agent can't start\nMissing dependency"]
    INSTALLED -->|installed| REGISTRY["Build tool registry\nAll actions from listed\ntools + collections"]

    REGISTRY --> LLM["LLM picks action"]
    LLM --> APPROVAL{"Approval\nrequired?"}
    APPROVAL -->|"read tool\n(default: none)"| EXECUTE["Execute"]
    APPROVAL -->|"write tool\n(default: required)"| ASK["Ask operator"]
    APPROVAL -->|"explicit override"| CHECK_OVERRIDE{"approval\nsetting?"}
    CHECK_OVERRIDE -->|none| EXECUTE
    CHECK_OVERRIDE -->|required| ASK

    ASK -->|approved| EXECUTE
    ASK -->|rejected| DENIED["Denied\nFeed back to LLM"]

    EXECUTE --> CONSTRAINTS{"Constraints\ncheck"}
    CONSTRAINTS -->|"max_actions\nexceeded"| STOP["Stop agent"]
    CONSTRAINTS -->|ok| RESULT["Record result\nFeed back to LLM"]

    style CANT fill:#fbb,stroke:#333
    style DENIED fill:#fbb,stroke:#333
    style STOP fill:#fbb,stroke:#333
    style EXECUTE fill:#bfb,stroke:#333
```

**Layer 1: Tool selection.** The agent lists tools and collections in `actions`. If a tool isn't listed, the LLM never sees it. If it's not installed, the agent can't start.

**Layer 2: Per-tool approval.** Each tool can set `approval: required` or `approval: none`. Defaults: read tools → none, write tools → required. The approval decision lives next to the tool, not in a separate policy block.

**Layer 3: Constraints.** Hard limits — `max_actions` caps total actions per run, `denied_patterns` blocks specific patterns via regex. Defense-in-depth.
