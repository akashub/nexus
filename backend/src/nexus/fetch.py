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
_GENERIC_NAMES = frozenset({
    "framework", "library", "tool", "plugin", "extension", "module", "package",
    "app", "application", "service", "server", "client", "api", "sdk", "cli",
    "ui", "backend", "frontend", "database", "testing", "linting", "styling",
    "auth", "config", "utils", "helpers", "core", "common", "shared", "base", "main",
})


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
    msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": method, "arguments": arguments}})
    try:
        proc = subprocess.run(
            ["npx", "-y", "@upstash/context7-mcp", *_ctx7_key_args()],
            input=msg, capture_output=True, text=True, timeout=45,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        content = json.loads(proc.stdout).get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item["text"]
                return None if any(m in text.lower() for m in _QUOTA_MARKERS) else text
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None

def _fetch_context7(name: str) -> DocResult | None:
    if name.lower().strip() in _GENERIC_NAMES:
        return None
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


def _gh_readme(repo: str, headers: dict) -> DocResult | None:
    try:
        url = f"https://api.github.com/repos/{repo}/readme"
        r = httpx.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            gh_url = f"https://github.com/{repo}"
            return DocResult(text=r.text[:4000], doc_url=gh_url, source="github")
    except Exception:
        return None


def _fetch_github(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    headers = {"Accept": "application/vnd.github.raw+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for repo in (f"{slug}/{slug}", f"{slug}python/{slug}", f"{slug}/{slug}-python"):
        if result := _gh_readme(repo, headers):
            return result
    try:
        r = httpx.get("https://api.github.com/search/repositories",
                       params={"q": slug, "per_page": "1"}, headers=headers, timeout=10)
        if r.status_code == 200 and (items := r.json().get("items")):
            return _gh_readme(items[0]["full_name"], headers)
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
            extras = [desc]
            for key, label in (("repository_url", "Repository"), ("homepage", "Homepage")):
                if data.get(key):
                    extras.append(f"{label}: {data[key]}")
            if data.get("keywords"):
                extras.append(f"Keywords: {', '.join(data['keywords'][:10])}")
            return DocResult(
                text="\n".join(extras)[:2000], doc_url=data.get("homepage"),
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
    if mode == "auto":
        for src in SOURCES:
            if result := _FETCHERS[src](name):
                return result
        return None
    hits = [r for r in (_FETCHERS[s](name) for s in SOURCES) if r]
    if not hits:
        return None
    return DocResult(
        text="\n\n---\n\n".join(r.text for r in hits)[:6000],
        library_id=next((r.library_id for r in hits if r.library_id), None),
        doc_url=next((r.doc_url for r in hits if r.doc_url), None),
        source="all", merged=[r.source for r in hits],
    )


def fetch_quickstart(library_id: str) -> str | None:
    return _mcp_call("query-docs", {
        "libraryId": library_id, "query": "installation and quick start code examples",
    })


def resolve_library(name: str) -> tuple[str | None, str | None]:
    result = _fetch_context7(name)
    return (result.library_id, result.doc_url) if result else (None, None)
