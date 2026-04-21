# Operon Recipes (Planned)

Community-shared, reusable agent specs. Like Ansible Galaxy, but for autonomous agents.

> **Status:** This is a design document for a planned feature. The concepts below describe the target architecture — none of this is implemented yet.

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

## Policy as a Trust Boundary

This is what makes recipes safe to share. Unlike Ansible Galaxy where you run arbitrary Python, an Operon recipe's blast radius is visible in the YAML:

```yaml
policy:
  mode: autonomous
  allowed_actions:
    - kubectl:get_pods
    - kubectl:get_logs
    - kubectl:describe_pod
    - kubectl:rollout_restart    # write operation
  constraints:
    max_actions: 10
```

An operator can:

- **Inspect before running** — the spec declares every action the agent can take
- **Tighten the policy** — switch from `autonomous` to `approval_required` or `read_only`
- **Remove write actions** — delete `kubectl:rollout_restart` from `allowed_actions`
- **Add constraints** — lower `max_actions`, add `denied_patterns`

The recipe author defines the recommended policy. The operator has final say.

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
