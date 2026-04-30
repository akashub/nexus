from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class DocResult:
    text: str
    library_id: str | None = None
    doc_url: str | None = None


_QUOTA_MARKERS = ("quota exceeded", "rate limit", "too many requests")


def _ctx7_key_flag() -> str:
    key = os.environ.get("CONTEXT7_API_KEY", "")
    if not key:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("CONTEXT7_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    return f" --api-key {key}" if key else ""


def _mcp_call(method: str, arguments: dict) -> str | None:
    msg = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
    })
    try:
        proc = subprocess.run(
            f"echo '{msg}' | npx -y @upstash/context7-mcp{_ctx7_key_flag()}",
            capture_output=True, text=True, timeout=45, shell=True,
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


def resolve_library(name: str) -> tuple[str | None, str | None]:
    text = _mcp_call("resolve-library-id", {"query": name, "libraryName": name})
    if not text:
        return None, None
    match = re.search(r"Context7-compatible library ID:\s*(\S+)", text)
    if not match:
        return None, None
    return match.group(1), None


def query_docs(library_id: str, topic: str | None = None) -> str | None:
    query = topic or "overview and getting started"
    return _mcp_call("query-docs", {"libraryId": library_id, "query": query})


def fetch_context(name: str, topic: str | None = None) -> DocResult | None:
    lib_id, doc_url = resolve_library(name)
    if lib_id:
        text = query_docs(lib_id, topic)
        if text:
            return DocResult(text=text, library_id=lib_id, doc_url=doc_url)
    return _fetch_registry(name)


def _fetch_registry(name: str) -> DocResult | None:
    slug = name.lower().replace(" ", "-")
    for fetcher in (_fetch_pypi, _fetch_npm):
        result = fetcher(slug)
        if result:
            return result
    return None


def _fetch_pypi(name: str) -> DocResult | None:
    try:
        r = httpx.get(f"https://pypi.org/pypi/{name}/json", timeout=10)
        if r.status_code != 200:
            return None
        info = r.json().get("info", {})
        desc = info.get("description", "")
        if not desc or len(desc) < 50:
            return None
        url = info.get("project_url") or info.get("home_page")
        return DocResult(text=desc[:4000], doc_url=url)
    except Exception:
        return None


def _fetch_npm(name: str) -> DocResult | None:
    try:
        r = httpx.get(f"https://registry.npmjs.org/{name}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        readme = data.get("readme", "")
        if not readme or len(readme) < 50 or readme == "ERROR":
            return None
        url = data.get("homepage")
        return DocResult(text=readme[:4000], doc_url=url)
    except Exception:
        return None


def fetch_quickstart(library_id: str) -> str | None:
    return query_docs(library_id, "installation and quick start code examples")
