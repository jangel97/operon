from __future__ import annotations

import re

from importlib.metadata import PackageNotFoundError, requires

_VERSION_RE = re.compile(r"[><=!~]")


def _parse_dep_name(dep: str) -> str:
    dep = dep.split(";")[0].strip()
    m = _VERSION_RE.search(dep)
    if m:
        return dep[: m.start()].strip()
    return dep.split(" ")[0].strip()


def resolve_collection(
    collection_name: str,
    known_tools: set[str] | None = None,
) -> list[str]:
    package_name = f"operon-collection-{collection_name}"
    try:
        deps = requires(package_name)
    except PackageNotFoundError:
        raise ValueError(
            f"Collection '{collection_name}' is not installed. "
            f"Install with: agentctl install {collection_name}"
        )

    if deps is None:
        return []

    tool_types: list[str] = []
    for dep in deps:
        dep_name = _parse_dep_name(dep)

        if dep_name.startswith("operon-tool-"):
            tool_type = dep_name.removeprefix("operon-tool-")
            tool_types.append(tool_type)
        elif dep_name.startswith("operon-collection-"):
            nested = dep_name.removeprefix("operon-collection-")
            tool_types.extend(resolve_collection(nested, known_tools))

    if known_tools is not None:
        tool_types = [t for t in tool_types if t in known_tools]

    return tool_types
