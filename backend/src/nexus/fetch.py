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


def fetch_web(url: str) -> str | None:
    try:
        r = httpx.get(
            url,
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Nexus/0.1"},
        )
        r.raise_for_status()
        text = r.text
        if "<html" in text.lower():
            return _extract_text_from_html(text)
        return text[:10000]
    except httpx.HTTPError:
        return None


def _extract_text_from_html(html: str) -> str:
    import re

    for tag in ["script", "style", "nav", "header", "footer"]:
        html = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:10000]


def fetch_context(name: str, topic: str | None = None) -> str | None:
    lib_id = resolve_library(name)
    if lib_id:
        return query_docs(lib_id, topic)
    return None
