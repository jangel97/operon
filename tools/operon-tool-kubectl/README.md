# operon-tool-kubectl (deprecated)

> **Deprecated:** This monolithic tool has been replaced by granular k8s tools: `k8s-pod-reader`, `k8s-log-reader`, `k8s-event-reader`, `k8s-deployment-reader`, `k8s-service-reader`, `k8s-node-reader`, `k8s-namespace-reader`, `k8s-pod-deleter`, `k8s-scaler`, `k8s-restarter`. See `tools/docs/tool-design.md` for the design rationale.

Kubernetes operations via kubectl. Intent-based — the LLM picks operations, the tool builds and executes the actual commands.

## Install

```bash
pip install -e tools/operon-tool-kubectl
```

Requires `kubectl` in PATH and a configured kubeconfig.

## Actions

### Read operations

| Action | Description | Params |
|--------|-------------|--------|
| `get_pods` | List pods in a namespace (JSON) | `namespace` (default: `default`) |
| `describe_pod` | Detailed info about a pod | `name` (required), `namespace` |
| `get_logs` | Pod logs | `name` (required), `namespace`, `container`, `tail` (default: 100) |
| `get_events` | Namespace events sorted by time (JSON) | `namespace` |
| `get_deployments` | List deployments (JSON) | `namespace` |
| `describe_deployment` | Detailed deployment info | `name` (required), `namespace` |
| `get_services` | List services (JSON) | `namespace` |
| `get_nodes` | List cluster nodes (JSON) | — |
| `get_namespaces` | List all namespaces (JSON) | — |
| `top_pods` | CPU/memory usage of pods | `namespace` |
| `top_nodes` | CPU/memory usage of nodes | — |

### Write operations

Write operations are never exposed unless explicitly listed in `allowed_actions`.

| Action | Description | Params |
|--------|-------------|--------|
| `rollout_restart` | Restart a deployment (rolling update) | `name` (required), `namespace` |
| `scale_deployment` | Scale deployment replicas | `name` (required), `namespace`, `replicas` (required) |
| `delete_pod` | Delete a pod (recreated by controller) | `name` (required), `namespace` |

## Example

```yaml
tools:
  - name: kubectl
    type: kubectl

policy:
  mode: approval_required
  allowed_actions:
    - kubectl:get_pods
    - kubectl:describe_pod
    - kubectl:get_logs
```
