from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import httpx

SOURCES = ("context7", "pypi", "npm", "github", "libraries")
MODES = ("auto", "all", *SOURCES)


@dataclass
class DocResult:
    text: str
    library_id: str | None = None
    doc_url: str | None = None
    source: str = "unknown"
    merged: list[str] = field(default_factory=list)


_QUOTA_MARKERS = ("quota exceeded", "rate limit", "too many requests")


def _ctx7_key_args() -> list[str]:
    key = os.environ.get("CONTEXT7_API_KEY", "")
    if not key:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("CONTEXT7_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    return ["--api-key", key] if key else []


def _mcp_call(method: str, arguments: dict) -> str | None:
    msg = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
    })
    try:
        cmd = ["npx", "-y", "@upstash/context7-mcp", *_ctx7_key_args()]
        proc = subprocess.run(
            cmd, input=msg, capture_output=True, text=True, timeout=45,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        resp = json.loads(proc.stdout)
        content = resp.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item["text"]
                if any(m in text.lower() for m in _QUOTA_MARKERS):
                    return None
                return text
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def _fetch_context7(name: str) -> DocResult | None:
    text = _mcp_call("resolve-library-id", {"query": name, "libraryName": name})
    if not text:
        return None
    match = re.search(r"Context7-compatible library ID:\s*(\S+)", text)
    if not match:
        return None
    lib_id = match.group(1)
    docs = _mcp_call("query-docs", {"libraryId": lib_id, "query": "overview and getting started"})
    if not docs:
        return None
    return DocResult(text=docs[:4000], library_id=lib_id, source="context7")


def _fetch_pypi(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    try:
        r = httpx.get(f"https://pypi.org/pypi/{slug}/json", timeout=10)
        if r.status_code != 200:
            return None
        info = r.json().get("info", {})
        desc = info.get("description", "")
        if not desc or len(desc) < 50:
            return None
        url = info.get("project_url") or info.get("home_page")
        return DocResult(text=desc[:4000], doc_url=url, source="pypi")
    except Exception:
        return None


def _fetch_npm(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    try:
        r = httpx.get(f"https://registry.npmjs.org/{slug}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        readme = data.get("readme", "")
        if not readme or len(readme) < 50 or readme == "ERROR":
            return None
        return DocResult(text=readme[:4000], doc_url=data.get("homepage"), source="npm")
    except Exception:
        return None


def _fetch_github(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    headers = {"Accept": "application/vnd.github.raw+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    candidates = [f"{slug}/{slug}", f"{slug}python/{slug}", f"{slug}/{slug}-python"]
    for repo in candidates:
        try:
            url = f"https://api.github.com/repos/{repo}/readme"
            r = httpx.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                body = r.text[:4000] if isinstance(r.text, str) else r.content.decode()[:4000]
                return DocResult(text=body, doc_url=f"https://github.com/{repo}", source="github")
        except Exception:
            continue
    try:
        r = httpx.get(
            "https://api.github.com/search/repositories",
            params={"q": slug, "per_page": "1"}, headers=headers, timeout=10,
        )
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                full_name = items[0]["full_name"]
                url = f"https://api.github.com/repos/{full_name}/readme"
                r2 = httpx.get(url, headers=headers, timeout=10)
                if r2.status_code == 200:
                    gh_url = f"https://github.com/{full_name}"
                    return DocResult(text=r2.text[:4000], doc_url=gh_url, source="github")
    except Exception:
        pass
    return None


def _fetch_libraries(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    for platform in ("pypi", "npm", "go", "cargo"):
        try:
            r = httpx.get(f"https://libraries.io/api/{platform}/{slug}", timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            desc = data.get("description", "")
            if not desc or len(desc) < 20:
                continue
            parts = [desc]
            if data.get("repository_url"):
                parts.append(f"Repository: {data['repository_url']}")
            if data.get("homepage"):
                parts.append(f"Homepage: {data['homepage']}")
            if data.get("keywords"):
                parts.append(f"Keywords: {', '.join(data['keywords'][:10])}")
            return DocResult(
                text="\n".join(parts)[:2000], doc_url=data.get("homepage"),
                source="libraries",
            )
        except Exception:
            continue
    return None


_FETCHERS = {
    "context7": _fetch_context7, "pypi": _fetch_pypi, "npm": _fetch_npm,
    "github": _fetch_github, "libraries": _fetch_libraries,
}


def fetch_context(name: str, mode: str = "auto") -> DocResult | None:
    if mode in _FETCHERS:
        return _FETCHERS[mode](name)
    order = list(SOURCES)
    if mode == "auto":
        for src in order:
            result = _FETCHERS[src](name)
            if result:
                return result
        return None
    results = [_FETCHERS[src](name) for src in order]
    hits = [r for r in results if r]
    if not hits:
        return None
    merged = DocResult(
        text="\n\n---\n\n".join(r.text for r in hits)[:6000],
        library_id=next((r.library_id for r in hits if r.library_id), None),
        doc_url=next((r.doc_url for r in hits if r.doc_url), None),
        source="all",
        merged=[r.source for r in hits],
    )
    return merged


def fetch_quickstart(library_id: str) -> str | None:
    return _mcp_call(
        "query-docs",
        {"libraryId": library_id, "query": "installation and quick start code examples"},
    )


def resolve_library(name: str) -> tuple[str | None, str | None]:
    result = _fetch_context7(name)
    return (result.library_id, result.doc_url) if result else (None, None)
