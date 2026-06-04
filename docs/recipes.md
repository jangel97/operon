# Operon Recipes (Planned)

Community-shared, reusable agent specs. Like Ansible Galaxy, but for autonomous agents.

> **Status:** This is a design document for a planned feature. The concepts below describe the target architecture — none of this is implemented yet.

## Philosophy

Operon is opinionated: the AI is not in charge — there is always an operator (the director) behind it. The operator selects the agent spec, configures the tools, sets the policy, and decides what the AI is allowed to do. The AI reasons and picks actions; the operator controls the environment it runs in.

Tools are the operator's responsibility, and Operon is opinionated about how they should be built: **each tool does one thing, and its blast radius is obvious from the name.** The operator controls what an agent can do by choosing which tools to install. If you don't install a write tool, the agent can't write — no policy misconfiguration possible.

The ecosystem of ready-made, fine-grained tools covers common cases: `k8s-reader` for cluster inspection, `github-reader` for issue triage, `websearch` for research. When the ecosystem doesn't cover a use case, operators build custom tools — the plugin system makes this straightforward. The agent spec never changes; the tool ecosystem around it grows.

## Concept

A recipe is a portable agent definition — goal, tools, policy, and inputs — that anyone can install and run. The YAML spec is the contract: you can read exactly what the agent does and what it's allowed to do before running it.

## Structure

A recipe is a directory with an agent spec and its dependencies:

```
operon-recipes/
├── k8s-incident-response/
│   ├── agent.yaml
│   ├── requirements.txt      # operon-tool-kubectl, operon-tool-pagerduty
│   └── README.md
├── security-audit/
│   ├── agent.yaml
│   ├── requirements.txt      # operon-tool-kubectl, operon-tool-trivy
│   └── README.md
├── cost-optimizer/
│   ├── agent.yaml
│   ├── requirements.txt      # operon-tool-aws
│   └── README.md
├── db-health-check/
│   ├── agent.yaml
│   ├── requirements.txt      # operon-tool-postgres
│   └── README.md
└── deploy-canary/
    ├── agent.yaml
    ├── requirements.txt      # operon-tool-kubectl, operon-tool-prometheus
    └── README.md
```

## Usage (Target)

```bash
# Install a recipe and its tool dependencies
operon install k8s-incident-response

# Run it
agentctl run k8s-incident-response -e namespace=production

# Edit the policy in the YAML before running (tighten permissions)
# Change mode from "autonomous" to "read_only" or "approval_required"
```

## Why Recipes are Portable

Agent specs are declarative — they describe **what** to do, not **how** to authenticate. Credentials live in the tool layer, not the spec.

```
┌─────────────────────────────────────────────────┐
│  Recipe (YAML)                                  │
│  ✓ goal, tools, policy, inputs                  │
│  ✗ no credentials, no endpoints, no config      │
│  → shareable, auditable, version-controlled      │
└────────────────────┬────────────────────────────┘
                     │ references
┌────────────────────▼────────────────────────────┐
│  Tool Plugins (installed separately)            │
│  kubectl → reads kubeconfig at exec time        │
│  github  → reads gh auth state at exec time     │
│  aws     → reads ~/.aws/credentials at exec time│
└─────────────────────────────────────────────────┘
```

The same recipe runs against any cluster, any GitHub org, any AWS account — the operator controls **where** by configuring the tools on their machine. The recipe author controls **what** the agent does and what it's allowed to do.

## Safety Model

Safety comes from two layers. The first is the most important.

### Layer 1: Tool selection (install = opt-in)

The operator controls blast radius by choosing which tools to install. Fine-grained tools make this intuitive:

```bash
# Read-only investigation — install only readers
pip install operon-tool-k8s-reader operon-tool-github-reader

# Incident response — add the restarter deliberately
pip install operon-tool-k8s-restarter
```

The recipe declares what tools it needs. The operator decides what to install. If a recipe asks for `k8s-scaler` and the operator doesn't install it, the agent simply can't scale — no YAML editing required.

### Layer 2: Per-tool approval + constraints

The agent spec controls approval per tool and sets hard limits:

```yaml
actions:
  collections:
    - k8s-readonly                       # readers, no approval
  tools:
    - k8s-restarter:
        approval: required               # human confirms restarts

policy:
  constraints:
    max_actions: 10
```

An operator can:

- **Inspect before running** — the spec lists every tool and collection
- **Set approval per tool** — write tools require approval, read tools don't
- **Add constraints** — lower `max_actions`, add `denied_patterns`
- **Remove tools** — delete a tool from the list to revoke that capability

The recipe author defines the recommended setup. The operator has final say.

## Recipe Categories

| Category | Examples |
|----------|----------|
| **Incident Response** | K8s pod recovery, service health check, log analysis |
| **Security** | Image vulnerability scan, RBAC audit, secret rotation |
| **Cost Optimization** | Idle resource cleanup, right-sizing recommendations |
| **Observability** | Alert triage, dashboard generation, SLO monitoring |
| **Deployment** | Canary rollout, blue-green switch, rollback automation |
| **Database** | Health check, backup verification, query analysis |
| **Research** | Web research, documentation lookup, competitive analysis |

## Recipe Spec Extensions

Beyond the standard agent spec, recipes can include:

```yaml
recipe:
  name: k8s-incident-response
  version: 1.0.0
  description: Detect and recover from Kubernetes pod failures
  author: operon-community
  tags: [kubernetes, incident-response, sre]
  
  dependencies:
    tools:
      - operon-tool-kubectl>=0.1.0
      - operon-tool-pagerduty>=0.1.0
    providers:
      - ollama    # works with local models
      - openai    # or cloud providers

  recommended_models:
    - qwen3:14b       # minimum for reliable reasoning
    - gpt-4o-mini     # good balance of cost and capability

  inputs:
    namespace:
      type: string
      description: Kubernetes namespace to monitor
    severity:
      type: string
      default: warning
      description: Minimum severity to act on
```

## Registry (Target)

A future `operon-registry` service (or a simple Git repository) where recipes are published, versioned, and discoverable:

```bash
# Search for recipes
operon search kubernetes

# Show recipe details
operon info k8s-incident-response

# Install a specific version
operon install k8s-incident-response@1.0.0

# List installed recipes
operon list
```

## Design Principles

1. **Readable** — Any operator can open the YAML and understand what the agent does
2. **Safe by default** — Write operations require explicit opt-in in the policy
3. **Overridable** — The operator always has final say over policy and inputs
4. **Portable** — Recipes work with any supported LLM provider
5. **Versioned** — Recipes and their tool dependencies are versioned independently
