# Differentiation

## Core thesis

Operon automates judgment. Workflow tools automate procedures.

## Workflow tools (n8n, Zapier, Step Functions)

The operator designs **how** — every branch, every transformation, every condition. Execution follows a predefined DAG. Same input produces the same path every time.

Works well for: moving data between systems, reacting to events with known responses, ETL pipelines, notifications.

Breaks down when: the path isn't known upfront, the situation requires observation before deciding what to do next, or the problem space has too many branches to pre-draw.

## Operon

The operator designs **what and within what bounds** — the goal, the tools, the approval gates. The agent observes, reasons, and acts. Different situations produce different paths toward the same goal.

Works well for: incident response, triage, investigation, remediation, any task where a human would need to look at the situation before deciding what to do.

Breaks down when: the task is a known procedure with no judgment required. An agent is overhead when a simple flow would do.

## The deterministic layer

Workflow tools don't need a policy engine because the human already scripted every step. In Operon, the model proposes freely but the spec constrains what's reachable:

- **Tool list = permission boundary.** If a tool isn't in the spec, the agent can't use it.
- **Per-tool approval.** The operator decides which tools need human confirmation, not the model.
- **Max actions, denied patterns.** Hard limits enforced before execution.

The model proposes, the spec constrains, the engine enforces. Adaptability of an agent with blast radius control of a workflow.

## Where it gets blurry

The control plane (teams, schedules, webhooks, UI) will look similar to workflow platforms at the surface. The differentiation is the unit of work:

- Workflow platforms orchestrate **steps**.
- Operon orchestrates **agents**.

The control plane should schedule, trigger, and monitor agents — not chain static steps into DAGs. If a task doesn't need judgment, it doesn't need an agent.

## Positioning

| | Workflow tools | Operon |
|---|---|---|
| Unit of work | Step (deterministic) | Agent (adaptive) |
| Operator defines | The procedure | The goal + boundaries |
| Execution path | Fixed DAG | Emergent from observations |
| Handles unknowns | Fails or needs a new branch | Adapts |
| Control model | Flow design | Spec: tools, approval, constraints |
| Best for | Known procedures | Tasks requiring judgment |
