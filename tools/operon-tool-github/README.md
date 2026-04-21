# operon-tool-github

GitHub operations via the `gh` CLI. Intent-based — the LLM picks operations, the tool builds and executes the actual commands.

## Install

```bash
pip install -e tools/operon-tool-github
```

Requires `gh` CLI in PATH and authenticated (`gh auth login`).

## Actions

### Read operations

| Action | Description | Params |
|--------|-------------|--------|
| `list_issues` | List issues in a repository | `repo` (required), `state` (default: `open`), `limit` (default: 10), `label` |
| `get_issue` | Get issue details including comments | `repo` (required), `number` (required) |
| `list_prs` | List pull requests | `repo` (required), `state` (default: `open`), `limit` (default: 10) |
| `get_pr` | Get PR details including reviews | `repo` (required), `number` (required) |
| `list_releases` | List releases | `repo` (required), `limit` (default: 5) |
| `list_workflow_runs` | List recent CI/CD runs | `repo` (required), `limit` (default: 10) |
| `get_workflow_run` | Get details of a workflow run | `repo` (required), `run_id` (required) |

### Write operations

Write operations are never exposed unless explicitly listed in `allowed_actions`.

| Action | Description | Params |
|--------|-------------|--------|
| `create_issue` | Create a new issue | `repo` (required), `title` (required), `body`, `label` |
| `close_issue` | Close an issue | `repo` (required), `number` (required) |
| `reopen_issue` | Reopen a closed issue | `repo` (required), `number` (required) |
| `comment_issue` | Comment on an issue or PR | `repo` (required), `number` (required), `body` (required) |
| `add_label` | Add a label to an issue/PR | `repo` (required), `number` (required), `label` (required) |
| `remove_label` | Remove a label from an issue/PR | `repo` (required), `number` (required), `label` (required) |
| `close_pr` | Close a PR without merging | `repo` (required), `number` (required) |
| `merge_pr` | Merge a PR | `repo` (required), `number` (required), `method` (default: `merge` — also `squash`, `rebase`) |

## Example

```yaml
tools:
  - name: github
    type: github

policy:
  mode: approval_required
  allowed_actions:
    - github:list_issues
    - github:get_issue
    - github:add_label
    - github:comment_issue
```
