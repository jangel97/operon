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

## Plugin System

Tools are separate pip packages discovered automatically via Python entry points.

```mermaid
flowchart TD
    subgraph AGENTCTL ["agentctl (runtime)"]
        REGISTRY2["ToolRegistry"]
        EP["Entry Points Discovery\noperon.tools group"]
    end

    subgraph PLUGINS ["Tool Plugins (pip packages)"]
        KUBECTL["operon-tool-kubectl\n14 operations\nread/write tagged"]
        WEBSEARCH["operon-tool-websearch\nDuckDuckGo search\nHTTP fetch"]
        WEATHER["operon-tool-weather\nMock data\nFor testing"]
        CUSTOM["operon-tool-???\nYour custom tool"]
    end

    EP --> KUBECTL
    EP --> WEBSEARCH
    EP --> WEATHER
    EP --> CUSTOM
    KUBECTL --> REGISTRY2
    WEBSEARCH --> REGISTRY2
    WEATHER --> REGISTRY2
    CUSTOM --> REGISTRY2

    style AGENTCTL fill:#e8f4fd,stroke:#333
    style PLUGINS fill:#f0f0f0,stroke:#333
```

## Policy Enforcement

Tools define capability, policy defines permissions. Single source of truth.

```mermaid
flowchart TD
    TOOL_DEF["Tool defines operations\nget_pods (read)\ndelete_pod (write)\nscale_deployment (write)"]

    POLICY_DEF["Policy defines permissions\nallowed_actions:\n  - kubectl:get_pods\n  - kubectl:delete_pod"]

    TOOL_DEF --> FILTER["Filter: only allowed\nactions shown to LLM"]
    POLICY_DEF --> FILTER

    FILTER --> LLM_SEES["LLM sees:\n kubectl:get_pods\n kubectl:delete_pod"]

    LLM_SEES -->|picks| ACTION["kubectl:delete_pod"]

    ACTION --> MODE_CHECK{"Policy Mode?"}
    MODE_CHECK -->|read_only| BLOCK["Blocked\n(write operation)"]
    MODE_CHECK -->|approval_required| ASK["Ask operator"]
    MODE_CHECK -->|autonomous| RUN["Execute"]
    ASK -->|approved| RUN
    ASK -->|rejected| BLOCK

    style BLOCK fill:#fbb,stroke:#333
    style RUN fill:#bfb,stroke:#333
```
