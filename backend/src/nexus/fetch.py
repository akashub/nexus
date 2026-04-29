from __future__ import annotations

import httpx

_CONTEXT7_BASE = "https://api.context7.com/v1"
_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def resolve_library(name: str) -> str | None:
    try:
        r = httpx.get(
            f"{_CONTEXT7_BASE}/resolve",
            params={"query": name, "libraryName": name},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        results = r.json()
        if results and isinstance(results, list):
            return results[0].get("id")
        return None
    except (httpx.HTTPError, KeyError, IndexError):
        return None


def query_docs(library_id: str, topic: str | None = None) -> str | None:
    query = topic or "overview and getting started"
    try:
        r = httpx.get(
            f"{_CONTEXT7_BASE}/query",
            params={"libraryId": library_id, "query": query},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get("text") or data.get("content")
        if isinstance(data, str):
            return data
        return None
    except (httpx.HTTPError, KeyError):
        return None


def fetch_context(name: str, topic: str | None = None) -> str | None:
    lib_id = resolve_library(name)
    if lib_id:
        return query_docs(lib_id, topic)
    return None
