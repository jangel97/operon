# Product Milestones

## M0: Engine (done)

agentctl — the stateless kernel. Run one agent, enforce policy, produce a trace.

- [x] Declarative agent specs (YAML)
- [x] LLM decision loop (Ollama, OpenAI)
- [x] Policy engine (per-tool approval, max actions, denied patterns)
- [x] Tool plugin system (Python entry points)
- [x] Tool collections (curated bundles, dependency-only packages)
- [x] `actions.collections` + `actions.tools` spec format
- [x] Execution trace (Rich, JSON, NDJSON)
- [x] API server (`agentctl serve`)
- [x] Two-model architecture (extractor)
- [x] Secret interpolation + redaction
- [x] `agentctl install` command

## M1: Tool Ecosystem

Fine-grained, single-purpose tools. Language-agnostic exec protocol. Make it trivially easy to build and share tools.

- [x] Fine-grained k8s tools (pod-reader, log-reader, event-reader, deployment-reader, service-reader, node-reader, namespace-reader, restarter, scaler, pod-deleter)
- [x] k8s-readonly and k8s-sre collections
- [ ] Exec tool protocol (JSON over stdin/stdout — any language)
- [x] Split github tool → fine-grained tools (issue-reader, pr-reader, release-reader, ci-reader, issue-manager, labeler, commenter, pr-closer, pr-merger)
- [x] github-readonly and github-triage collections
- [ ] Tool author guide + template repo
- [ ] 3-5 additional tools (Prometheus, PagerDuty, Terraform, AWS, Postgres)

**Unlocks:** Broader adoption. Tools in any language. Not locked to Python.

## M2: Control Plane MVP

The product layer. Teams, webhooks, workflows, persistence. Open-source, Ansible/AWX model — agentctl is the CLI, Control Plane is the web UI.

- [ ] Single-tenant API server
- [ ] Teams as labels (basic access control)
- [ ] Run persistence (Postgres — runs, traces, workflow state)
- [ ] Webhook triggers (GitHub + generic)
- [ ] Sequential workflow engine (steps, conditionals, outputs between steps)
- [ ] Notifications (Slack + webhook)
- [ ] Dashboard (read-only web UI — runs, traces, workflow progress)

**Unlocks:** Teams running agents in production. Event-driven automation. Visibility.

## M3: Multi-Tenancy + Collaboration

Scale from one team to an organization.

- [ ] Organizations with multiple teams
- [ ] Role-based access control (admin, operator, viewer)
- [ ] Shared tool registry (org-scoped)
- [ ] Recipe marketplace (publish, discover, install)
- [ ] Audit log (searchable, exportable)
- [ ] Multi-tenant billing

**Unlocks:** Enterprise adoption. Self-service for teams within an org.

## M4: AutoRAG

Platform-managed knowledge. Agents get scoped context without operators managing RAG pipelines.

- [ ] AutoRAG infrastructure nodes (vector/index databases)
- [ ] Document ingestion (upload docs, runbooks, postmortems)
- [ ] Knowledge bases scoped to teams and agents
- [ ] Automatic context injection (engine queries index before each decision)
- [ ] Agent spec declares knowledge requirements, not retrieval mechanics

**Unlocks:** "Your agent automatically knows your runbooks." Knowledge-augmented agents without RAG expertise.

## M5: Inference Platform

Platform-managed model serving. Operators don't configure endpoints — the platform handles it.

- [ ] Model catalog + deployment (vLLM or best available runtime)
- [ ] Model lifecycle (pull, serve, health check, upgrade)
- [ ] Auto-scaling (scale to zero, burst replicas)
- [ ] GPU scheduling across teams (priority queues)
- [ ] Model routing (agent declares requirements, platform picks the instance)

**Unlocks:** Full stack — write the spec, the platform handles models, knowledge, tools, and orchestration.

## Sequencing

```
M0 ──▶ M1 ──▶ M2 ──▶ M3 ──▶ M4 ──▶ M5
engine  tools  control multi-  RAG   inference
(done)         plane   tenant
```

Each milestone validates demand for the next. Don't skip ahead. Inference (M5) is a commodity race — only build it when there's pull from M4 adopters who want a single platform. AutoRAG (M4) is the sharper differentiator.
