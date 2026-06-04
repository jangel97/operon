# Tool Design Guide

## Principles

1. **One concern per tool.** A tool that reads pods and deletes pods is two tools.
2. **Name reveals intent.** `k8s-pod-reader`, not `k8s`. `github-pr-merger`, not `github`.
3. **Blast radius is obvious.** An operator should know what a tool can do before reading a single line of code.
4. **Install = opt-in.** The operator controls what an agent can do by choosing which tools to install. No write tool installed = no writes possible.

## Tools vs Collections

### Tool

The smallest unit of capability. A tool does one thing and its blast radius is obvious from the name.

```
operon-tool-k8s-pod-reader         # get_pods, describe_pod
operon-tool-k8s-log-reader         # get_logs (tail, container, since)
operon-tool-k8s-event-reader       # get_events
operon-tool-k8s-deployment-reader  # get_deployments, describe_deployment
operon-tool-k8s-scaler             # scale_deployment (write)
operon-tool-k8s-restarter          # rollout_restart (write)
```

A tool has:
- A unique name (used for action namespacing: `k8s-pod-reader:get_pods`)
- A small set of related actions (typically 1-5)
- All actions at the same trust level (all read, or all write to the same resource)
- Its own credentials (tools own their auth, not agents)

### Collection

A curated bundle of tools for a use case. Collections are a convenience — they don't change the security model. Each tool inside keeps its own name, actions, and blast radius.

```
operon-collection-k8s-readonly
├── operon-tool-k8s-pod-reader
├── operon-tool-k8s-deployment-reader
├── operon-tool-k8s-service-reader
├── operon-tool-k8s-event-reader
├── operon-tool-k8s-log-reader
├── operon-tool-k8s-node-reader
└── operon-tool-k8s-namespace-reader

operon-collection-k8s-sre
├── operon-collection-k8s-readonly    # all readers
├── operon-tool-k8s-restarter         # rollout_restart
└── operon-tool-k8s-pod-deleter       # delete_pod (recreated by controller)

operon-collection-github-readonly
├── operon-tool-github-issue-reader
├── operon-tool-github-pr-reader
├── operon-tool-github-release-reader
└── operon-tool-github-ci-reader

operon-collection-github-triage
├── operon-collection-github-readonly
├── operon-tool-github-labeler        # add/remove labels
└── operon-tool-github-commenter      # comment on issues/PRs
```

A collection is just a pip package whose only dependency is other tools (or collections). No code — just a `pyproject.toml` with dependencies.

```toml
# operon-collection-k8s-readonly/pyproject.toml
[project]
name = "operon-collection-k8s-readonly"
version = "0.1.0"
dependencies = [
    "operon-tool-k8s-pod-reader>=0.1.0",
    "operon-tool-k8s-deployment-reader>=0.1.0",
    "operon-tool-k8s-service-reader>=0.1.0",
    "operon-tool-k8s-event-reader>=0.1.0",
    "operon-tool-k8s-log-reader>=0.1.0",
    "operon-tool-k8s-node-reader>=0.1.0",
    "operon-tool-k8s-namespace-reader>=0.1.0",
]
```

Install a collection, get all its tools:

```bash
pip install operon-collection-k8s-readonly    # 7 read-only tools
pip install operon-collection-k8s-sre         # readers + restarter + pod-deleter
```

## Granularity Guidelines

Split along two axes: **resource** and **operation type**.

| Axis | Boundary | Example |
|------|----------|---------|
| Resource | Each resource type gets its own tool | pods, deployments, services, nodes |
| Operation | Read and write are always separate tools | `pod-reader` vs `pod-deleter` |

### When to split further

- The resource has different trust levels within read operations (e.g., `get_logs` might expose PII while `get_pods` doesn't)
- The write operation has significantly different blast radius (scaling vs deleting)

### When NOT to split

- Two actions on the same resource at the same trust level (e.g., `get_pods` and `describe_pod` are both read operations on pods — keep them together)

## Naming Convention

```
operon-tool-{domain}-{resource}-{operation}
operon-collection-{domain}-{use-case}
```

| Pattern | Examples |
|---------|----------|
| `{domain}` | `k8s`, `github`, `aws`, `postgres`, `prometheus` |
| `{resource}` | `pod`, `deployment`, `issue`, `pr`, `ec2` |
| `{operation}` | `reader`, `writer`, `scaler`, `restarter`, `merger`, `deleter` |
| `{use-case}` | `readonly`, `sre`, `triage`, `incident-response` |

Tools that naturally cover one concern don't need the full pattern:

```
operon-tool-websearch         # search + fetch is one concern
operon-tool-prometheus-reader # read metrics (one resource type)
```

## Ecosystem Map (Target)

### Kubernetes

| Tool | Actions | Type |
|------|---------|------|
| `k8s-pod-reader` | get_pods, describe_pod | read |
| `k8s-log-reader` | get_logs | read |
| `k8s-event-reader` | get_events | read |
| `k8s-deployment-reader` | get_deployments, describe_deployment | read |
| `k8s-service-reader` | get_services | read |
| `k8s-node-reader` | get_nodes, top_nodes | read |
| `k8s-namespace-reader` | get_namespaces | read |
| `k8s-pod-deleter` | delete_pod | write |
| `k8s-scaler` | scale_deployment | write |
| `k8s-restarter` | rollout_restart | write |

| Collection | Includes |
|------------|----------|
| `k8s-readonly` | all readers |
| `k8s-sre` | readonly + restarter + pod-deleter |
| `k8s-full` | everything |

### GitHub

| Tool | Actions | Type |
|------|---------|------|
| `github-issue-reader` | list_issues, get_issue | read |
| `github-pr-reader` | list_prs, get_pr | read |
| `github-release-reader` | list_releases | read |
| `github-ci-reader` | list_workflow_runs, get_workflow_run | read |
| `github-labeler` | add_label, remove_label | write |
| `github-commenter` | comment_issue | write |
| `github-issue-manager` | create_issue, close_issue, reopen_issue | write |
| `github-pr-closer` | close_pr | write |
| `github-pr-merger` | merge_pr | write |

| Collection | Includes |
|------------|----------|
| `github-readonly` | all readers |
| `github-triage` | readonly + labeler + commenter |
| `github-full` | everything |

### Other Domains (Future)

| Collection | Tools |
|------------|-------|
| `aws-ec2-readonly` | ec2-reader, sg-reader, vpc-reader |
| `prometheus-readonly` | metrics-reader, alerts-reader |
| `postgres-readonly` | query-reader, schema-reader, stats-reader |
| `postgres-dba` | readonly + vacuum, analyze, explain |
| `pagerduty-responder` | incident-reader, incident-acknowledger |

## Agent Spec Format

The agent spec uses `actions` to declare what the agent can do. Two sub-keys: `collections` for curated bundles, `tools` for individual tools.

### Basic example

```yaml
actions:
  collections:
    - k8s-readonly
  tools:
    - k8s-restarter:
        approval: required
    - websearch

policy:
  constraints:
    max_actions: 10
```

No `allowed_actions`. No global `mode`. The tool list IS the permission model. Approval is per-tool, right next to where the tool is listed.

### Per-tool approval

Each tool can declare its approval requirement:

```yaml
actions:
  collections:
    - k8s-readonly                       # readers, no approval needed
    - github-triage:
        approval: required               # approve comments and labels
  tools:
    - k8s-restarter:
        approval: required               # write tool, human confirms
    - k8s-scaler:
        approval: none                   # operator trusts auto-scaling
    - websearch                          # default: no approval (read tool)
```

| Value | Behavior |
|-------|----------|
| `required` | Human confirms each action from this tool |
| `none` | Executes without approval |
| Omitted | Tool's default (read tools → none, write tools → required) |

### Approval on collections

When a collection has `approval: required`, it applies to every tool in the collection:

```yaml
actions:
  collections:
    - k8s-sre:
        approval: required     # approval for ALL tools, including readers
```

### Minimal specs

Just tools:

```yaml
actions:
  tools:
    - websearch
    - k8s-pod-reader
```

Just collections:

```yaml
actions:
  collections:
    - k8s-sre
    - github-triage
```

### Full example — K8s incident response agent

```yaml
apiVersion: agents/v1
kind: Agent

metadata:
  name: k8s-incident-response
  version: v1

spec:
  goal: |
    Investigate the health of namespace "{{namespace}}".
    Check for unhealthy pods, get logs, and restart if needed.

  decision:
    provider: ollama
    model: qwen3:14b
    base_url: ${OLLAMA_URL}

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

Readable at a glance: the agent can read anything in the cluster, can restart things with approval, and is capped at 10 actions.
