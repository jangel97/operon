# Product Vision — MVP

> **Status:** Design document. Describes the target product built on top of the agentctl engine.

## The Two Layers

Operon has two layers. The engine exists today. The product is what we're building next.

```
┌─────────────────────────────────────────────────────────┐
│  Product (Control Plane)                                │
│  Teams, workflows, webhooks, notifications, dashboard   │
│  State, orchestration, multi-tenancy                    │
└────────────────────────┬────────────────────────────────┘
                         │ orchestrates
┌────────────────────────▼────────────────────────────────┐
│  Engine (agentctl)                                      │
│  Declarative specs, decision loop, policy, tools        │
│  Stateless, single-agent, CLI / API                     │
└─────────────────────────────────────────────────────────┘
```

agentctl is the kernel — it runs one agent, enforces policy, produces a trace, and exits. It knows nothing about users, teams, or persistence. The Control Plane is the product layer that adds everything an organization needs to run agents in production.

## Core Concepts

### Organizations and Teams

Agents belong to teams. Teams belong to organizations. Access control determines who can create, run, approve, and audit agents.

```
Organization (Acme Corp)
├── Team: SRE
│   ├── Agent: k8s-incident-response
│   ├── Agent: node-health-monitor
│   └── Members: alice, bob (can run + approve)
├── Team: Platform
│   ├── Agent: deploy-canary
│   ├── Agent: cost-optimizer
│   └── Members: carol (admin), dave (can run)
└── Team: Security
    ├── Agent: vulnerability-scan
    └── Members: eve (admin)
```

### Workflows

A workflow chains multiple agents. Each step is a full agent run — the workflow orchestrates the sequence, not the agents themselves. Agents stay simple and single-purpose.

```yaml
apiVersion: workflows/v1
kind: Workflow

metadata:
  name: incident-response
  team: sre

steps:
  - name: investigate
    agent: k8s-incident-response
    inputs:
      namespace: "{{trigger.namespace}}"

  - name: notify
    agent: slack-notifier
    inputs:
      channel: "#incidents"
      message: "{{steps.investigate.summary}}"
    when: "{{steps.investigate.status == 'completed'}}"

  - name: recover
    agent: k8s-restarter
    inputs:
      namespace: "{{trigger.namespace}}"
      target: "{{steps.investigate.outputs.unhealthy_pod}}"
    when: "{{steps.investigate.outputs.severity == 'critical'}}"
    requires_approval: true
```

Key properties:

- **Declarative.** The workflow spec describes the sequence — no imperative code.
- **Steps are agent runs.** Each step produces a trace, has a status, and can pass outputs to the next step.
- **Conditional.** Steps can depend on previous results (`when`).
- **Approval gates.** Individual steps can require human approval, independent of the agent's own policy.

### Webhooks

External events trigger agent runs or workflows. The Control Plane receives the webhook, matches it to a registered trigger, and starts the run.

```yaml
triggers:
  - name: github-push
    type: webhook
    source: github
    event: push
    filter:
      branch: main
    runs:
      workflow: deploy-canary
      inputs:
        repo: "{{event.repository.full_name}}"
        sha: "{{event.after}}"

  - name: pagerduty-alert
    type: webhook
    source: pagerduty
    event: incident.triggered
    runs:
      agent: k8s-incident-response
      inputs:
        namespace: "{{event.service.name}}"
        severity: "{{event.urgency}}"

  - name: scheduled
    type: cron
    schedule: "0 6 * * 1-5"
    runs:
      agent: cost-optimizer
      inputs:
        account: production
```

### Notifications

Agents can request human attention without blocking the loop. Unlike `approval_required` (which halts execution), notifications are async — the agent continues or pauses and the human responds when ready.

Use cases:

| Scenario | Behavior |
|----------|----------|
| Agent found something interesting | Notify + continue |
| Agent wants to do something risky | Notify + wait for response |
| Agent finished a workflow step | Notify the team |
| Agent hit an error it can't recover from | Notify + stop |

Notification channels are configured per team — Slack, email, webhook, dashboard. The agent spec declares **when** to notify, the team config declares **where**.

```yaml
notifications:
  - on: step_completed
    channel: slack
    target: "#sre-agents"

  - on: approval_needed
    channel: slack
    target: "#sre-approvals"
    mention: "@oncall"

  - on: error
    channel: pagerduty
    severity: warning
```

## Dashboard

The product needs a UI. Minimum viable dashboard:

- **Runs** — live and historical. Status, trace, duration, who triggered it.
- **Workflows** — step-by-step progress, which step is running, where it's waiting for approval.
- **Agents** — registered agents, which team owns them, last run status.
- **Audit log** — every action, every decision, every policy check. Searchable.

The dashboard reads from the same event stream that `agentctl -o ndjson` produces — the engine already emits structured events, the dashboard just renders them.

## What the MVP Needs

The smallest product that delivers value:

| Component | Scope | Why |
|-----------|-------|-----|
| **Single-tenant API** | One org, teams as labels | Multi-tenancy can wait; teams as tags gives basic access control |
| **Webhook triggers** | GitHub + generic webhook | Enough to wire up CI/CD and alerting |
| **Workflow engine** | Sequential steps, conditional, outputs | No fan-out/fan-in yet — linear pipelines cover 80% of use cases |
| **Notifications** | Slack + webhook | Two channels covers most teams |
| **Run persistence** | Postgres | Store runs, traces, workflow state |
| **Dashboard** | Read-only web UI | Runs list, trace viewer, workflow progress |

### What can wait

- Multi-tenancy / billing
- Fan-out/fan-in workflows
- Agent marketplace
- Role-based access control (beyond team membership)
- Self-hosted tool registry

## Architecture (MVP)

```
┌──────────────┐     ┌──────────────────────────────────────┐
│  Webhook     │────▶│  Control Plane API                   │
│  (GitHub,    │     │                                      │
│   PagerDuty, │     │  ┌────────────┐  ┌───────────────┐  │
│   cron)      │     │  │ Trigger    │  │ Workflow      │  │
└──────────────┘     │  │ Router     │  │ Engine        │  │
                     │  └─────┬──────┘  └───────┬───────┘  │
┌──────────────┐     │        │                 │          │
│  Dashboard   │◀───▶│  ┌─────▼─────────────────▼───────┐  │
│  (Web UI)    │     │  │         Run Manager            │  │
└──────────────┘     │  │  Spawns agentctl, streams      │  │
                     │  │  events, persists traces        │  │
┌──────────────┐     │  └─────┬─────────────────────────┘  │
│  Slack /     │◀────│        │                            │
│  Notifications│    │  ┌─────▼──────┐  ┌──────────────┐  │
└──────────────┘     │  │ agentctl   │  │  Postgres     │  │
                     │  │ (engine)   │  │  (state)      │  │
                     │  └────────────┘  └──────────────┘  │
                     └──────────────────────────────────────┘
```

The Control Plane spawns agentctl processes, reads their NDJSON output, persists events to Postgres, and routes notifications. agentctl doesn't change — it stays stateless and unaware of the product layer.

## Long-Term Vision: Own the Full Stack

The MVP treats LLMs and knowledge as external dependencies — the operator points to an Ollama endpoint or an OpenAI key. Long-term, Operon manages the entire AI infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│  Product (Control Plane)                                    │
│  Teams, workflows, webhooks, notifications, dashboard       │
├─────────────────────────────────────────────────────────────┤
│  Engine (agentctl)                                          │
│  Declarative specs, decision loop, policy, tools            │
├──────────────────────────────┬──────────────────────────────┤
│  AutoRAG Nodes               │  Inference Nodes             │
│                              │                              │
│  Index databases per team    │  Model serving (vLLM, etc.)  │
│  Document ingestion          │  Model lifecycle management  │
│  Retrieval API               │  Auto-scaling                │
│  Knowledge scoped to agents  │  GPU scheduling              │
└──────────────────────────────┴──────────────────────────────┘
```

### AutoRAG Nodes

Infrastructure nodes that host vector/index databases. Agents get scoped knowledge without the operator managing RAG pipelines manually.

- **Document ingestion** — teams upload docs, runbooks, postmortems. The platform indexes them.
- **Scoped retrieval** — each agent (or team) has access to specific knowledge bases. An SRE incident agent sees runbooks; a security agent sees CVE databases.
- **Automatic context** — the engine queries the index before each decision, injecting relevant context into the LLM prompt. The agent spec declares what knowledge it needs, not how to retrieve it.

### Inference Nodes

Platform-managed model serving. Operators don't configure Ollama endpoints or manage GPU allocation — the platform handles it.

- **Model deployment** — deploy models from a catalog (vLLM, TGI, or whatever the best serving runtime is at the time). The platform manages the lifecycle: pull, serve, health check, upgrade.
- **Auto-scaling** — scale inference capacity based on agent demand. Idle models scale to zero. Burst traffic spins up replicas.
- **GPU scheduling** — allocate GPUs across teams. Priority queues for critical agents (incident response > cost optimization).
- **Model routing** — agent specs declare a model requirement (e.g., "reasoning-capable, 14B+ parameters"), the platform routes to the best available instance. No hardcoded endpoints in YAML.

### Why this matters

Today an operator needs to: set up an LLM endpoint, manage a RAG pipeline, configure tools, write the agent spec, and run it. Each layer is a different system with different expertise.

The long-term vision is that Operon is the single platform: write the agent spec, point it at your infrastructure, and the platform handles models, knowledge, tools, orchestration, and observability. The agent spec stays declarative — what changes is how much the platform manages for you.
