from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass


@dataclass
class DocResult:
    text: str
    library_id: str | None = None
    doc_url: str | None = None


def _mcp_call(method: str, arguments: dict) -> str | None:
    msg = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
    })
    try:
        proc = subprocess.run(
            f"echo '{msg}' | npx -y @upstash/context7-mcp",
            capture_output=True, text=True, timeout=45, shell=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        resp = json.loads(proc.stdout)
        content = resp.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                return item["text"]
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
    return None


def fetch_quickstart(library_id: str) -> str | None:
    return query_docs(library_id, "installation and quick start code examples")
