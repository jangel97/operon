from __future__ import annotations

import re
from html.parser import HTMLParser

from ddgs import DDGS
from primp import Client

from operon.tools.base import Tool

MAX_FETCH_CHARS = 4000


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._skip = tag in ("script", "style", "nav", "header", "footer", "noscript")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "header", "footer", "noscript"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


class WebSearchTool(Tool):
    @property
    def name(self) -> str:
        return "websearch"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "web_search",
                "description": "Search the web and return top results with titles, URLs, and snippets",
                "params": {"query": "string", "max_results": "integer (1-10, default 5)"},
            },
            {
                "name": "web_fetch",
                "description": "Fetch a URL and return its text content (HTML tags stripped)",
                "params": {"url": "string"},
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        if action == "web_search":
            return self._search(params)
        if action == "web_fetch":
            return self._fetch(params)
        return f"Unknown action: {action}"

    def _search(self, params: dict) -> str:
        query = params.get("query", "")
        max_results = int(params.get("max_results", 5))
        max_results = max(1, min(max_results, 10))

        try:
            results = DDGS().text(query, max_results=max_results)
        except Exception as e:
            return f"Search failed: {e}"

        if not results:
            return f"No results found for: {query}"

        lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"  [{i}] {r['title']}")
            lines.append(f"      {r['href']}")
            lines.append(f"      {r['body']}")
            lines.append("")

        return "\n".join(lines)

    def _fetch(self, params: dict) -> str:
        url = params.get("url", "")
        if not url:
            return "Error: url parameter is required"

        try:
            client = Client(impersonate="chrome_131")
            resp = client.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return f"Fetch failed: {e}"

        parser = _TextExtractor()
        parser.feed(resp.text)
        text = parser.get_text()
        text = re.sub(r"\n{3,}", "\n\n", text)

        if len(text) > MAX_FETCH_CHARS:
            text = text[:MAX_FETCH_CHARS] + "\n\n[...truncated]"

        return f"Content from {url}:\n\n{text}"
