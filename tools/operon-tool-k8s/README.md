# operon-tool-k8s

Kubernetes tool for Operon. Provides pod management actions.

## Install

```bash
pip install -e .
```

## Actions

| Action | Description | Params |
|--------|-------------|--------|
| `list_pods` | List pods in a namespace with their status | `namespace` |
| `restart_pod` | Restart a pod by deleting it | `name`, `namespace` |

## Usage in agent spec

```yaml
tools:
  - name: kubernetes
    type: k8s
```

## Status

Currently uses mock data. Will be replaced with the `kubernetes` Python client for real cluster operations.
