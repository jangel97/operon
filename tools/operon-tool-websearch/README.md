# operon-tool-websearch

Web search and page fetching. Uses DuckDuckGo for search and HTTP for fetching with automatic HTML-to-text extraction.

## Install

```bash
pip install -e tools/operon-tool-websearch
```

No API keys required.

## Actions

| Action | Description | Params |
|--------|-------------|--------|
| `web_search` | Search the web via DuckDuckGo, returns titles, URLs, and snippets | `query` (required), `max_results` (1-10, default: 5) |
| `web_fetch` | Fetch a URL and return text content (HTML stripped) | `url` (required) |

`web_fetch` strips script, style, nav, header, and footer tags. Output is truncated at 4000 characters to protect the LLM context window.

## Example

```yaml
tools:
  - name: websearch
    type: websearch

policy:
  mode: autonomous
  allowed_actions:
    - websearch:web_search
    - websearch:web_fetch
```
