# Operon

**Agentic Automation Platform** — Define goals. Execute with control.

Operon is a platform for executing autonomous actions in production systems under strict policies, with full auditability.

## Project Structure

```
operon/
├── agentctl/              # Agent Runner — the core runtime
├── tools/                 # Tool plugins (each is a separate pip package)
│   └── operon-tool-k8s/   # Kubernetes tool (mock for MVP)
└── README.md
```

## Components

| Component | Description | Status |
|-----------|-------------|--------|
| [**agentctl**](agentctl/) | CLI runtime — loads agent specs, runs the decision loop, enforces policies | MVP |
| [**operon-tool-k8s**](tools/operon-tool-k8s/) | Kubernetes actions (list pods, restart pod) | MVP (mock) |
| **Control Plane** | Manages agents, coordinates execution, centralizes policies | Planned |

## Quick Start

```bash
# Install the runtime
cd agentctl
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Install a tool
pip install -e ../tools/operon-tool-k8s

# Run an agent
agentctl run examples/agent-ollama.yaml
```

## How it works

1. Define an agent in YAML (goal, tools, policy, LLM provider)
2. `agentctl run agent.yaml`
3. The loop runs: **decide → policy check → approve → execute → observe**
4. Every step is traced for auditability

## Tools are plugins

Tools are separate packages that agentctl discovers automatically via Python entry points. Anyone can create and publish their own:

```bash
pip install operon-tool-k8s     # Kubernetes
pip install operon-tool-aws     # AWS (future)
pip install operon-tool-github  # GitHub (future)
```

See [agentctl/README.md](agentctl/README.md) for full documentation on creating tools and providers.
