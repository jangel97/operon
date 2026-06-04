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

## Plugin System

Tools are separate packages discovered automatically via Python entry points.

```mermaid
flowchart TD
    subgraph AGENTCTL ["agentctl (runtime)"]
        REGISTRY2["ToolRegistry"]
        EP["Entry Points Discovery\noperon.tools group"]
    end

    subgraph PLUGINS ["Tool Plugins (pip packages)"]
        K8S_READ["operon-tool-k8s-reader\nget pods, logs, events\nread only"]
        K8S_SCALE["operon-tool-k8s-scaler\nscale deployments\nwrite"]
        WEBSEARCH["operon-tool-websearch\nDuckDuckGo search\nHTTP fetch"]
        CUSTOM["operon-tool-???\nYour custom tool"]
    end

    EP --> K8S_READ
    EP --> K8S_SCALE
    EP --> WEBSEARCH
    EP --> CUSTOM
    K8S_READ --> REGISTRY2
    K8S_SCALE --> REGISTRY2
    WEBSEARCH --> REGISTRY2
    CUSTOM --> REGISTRY2

    style AGENTCTL fill:#e8f4fd,stroke:#333
    style PLUGINS fill:#f0f0f0,stroke:#333
```

## Credential Model

Tools consume their own credentials. The agent spec handles configuration (LLM endpoints, input defaults) — not tool authentication.

```mermaid
flowchart TD
    subgraph AGENT_SPEC ["Agent Spec (YAML)"]
        ENV_INTERP["${ENV_VAR} interpolation\nLLM base_url, input defaults"]
    end

    subgraph RUNTIME ["agentctl Runtime"]
        RUNNER["AgentRunner\nResolves ${ENV_VAR}\nBuilds tool registry"]
        LOOP["AgentLoop\nLLM decides what to do"]
        REDACTOR["Redactor\nno_log values → ***REDACTED***"]
    end

    subgraph TOOLS ["Tool Plugins (own their credentials)"]
        KUBECTL["kubectl tool\nReads kubeconfig"]
        GITHUB["github tool\nUses gh auth state"]
        CUSTOM["custom tool\nOwn auth mechanism"]
    end

    subgraph CREDS ["System Credentials (never touch the LLM)"]
        KUBECONFIG["~/.kube/config\nKUBECONFIG"]
        GH_AUTH["gh auth state\nGH_TOKEN"]
        CUSTOM_CRED["env vars / config files\ntoken files"]
    end

    ENV_INTERP --> RUNNER
    RUNNER --> LOOP
    LOOP -->|"action + params\n(no credentials)"| KUBECTL
    LOOP -->|"action + params"| GITHUB
    LOOP -->|"action + params"| CUSTOM
    LOOP --> REDACTOR

    KUBECONFIG -.->|"read at exec time"| KUBECTL
    GH_AUTH -.->|"read at exec time"| GITHUB
    CUSTOM_CRED -.->|"read at exec time"| CUSTOM

    style CREDS fill:#ffe0e0,stroke:#333
    style TOOLS fill:#e0f0ff,stroke:#333
    style AGENT_SPEC fill:#f0f0f0,stroke:#333
```

The LLM decides **what** to do (action + params). The tool decides **how** to authenticate. Credentials are resolved at execution time by the tool itself — the agent spec has no `credentials` field and no way to inject auth into a tool.

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
