from __future__ import annotations

import json
from pathlib import Path

from nexus.scanners import ScannedConcept, ScannedRelationship, ScanResult

_MCP_PATHS = [
    Path.home() / ".claude" / "plugins.json",
    Path.home() / ".claude.json",
]

_SECRET_PREFIXES = ("--token", "--key", "--secret", "--password", "--api-key", "--apikey")


def _looks_secret(arg: str) -> bool:
    lower = arg.lower()
    return any(lower.startswith(p) for p in _SECRET_PREFIXES) or lower.startswith("sk-")


def _filter_secret_args(args: list[str]) -> list[str]:
    """Drop secret flags and their following values from arg lists."""
    safe: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if _looks_secret(arg):
            skip_next = "=" not in arg  # --token VAL vs --token=VAL
            continue
        safe.append(arg)
    return safe


def scan_mcp(project_path: Path) -> ScanResult:
    result = ScanResult()
    seen: set[str] = set()

    project_mcp = project_path / ".mcp.json"
    if project_mcp.exists():
        _parse_mcp_file(project_mcp, result, seen)

    for path in _MCP_PATHS:
        if path.exists():
            _parse_mcp_file(path, result, seen)

    return result


def _parse_mcp_file(
    path: Path, result: ScanResult, seen: set[str],
) -> None:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    servers = data.get("mcpServers", data.get("servers", {}))
    if not isinstance(servers, dict):
        return

    names_added: list[str] = []
    for name, config in servers.items():
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        cmd = ""
        if isinstance(config, dict):
            cmd = config.get("command", "")
            args = config.get("args", [])
            if isinstance(args, list):
                safe = _filter_secret_args([str(a) for a in args[:5]])
                cmd = f"{cmd} {' '.join(safe)}"

        result.concepts.append(ScannedConcept(
            name=name, source="mcp_config", category_hint="devtool",
            context=f"MCP server: {cmd.strip()[:80]}" if cmd.strip() else None,
        ))
        names_added.append(name)

    _infer_mcp_relationships(names_added, result)


def _infer_mcp_relationships(
    names: list[str], result: ScanResult,
) -> None:
    if len(names) < 2:
        return
    for i, src in enumerate(names):
        for tgt in names[i + 1:]:
            result.relationships.append(ScannedRelationship(
                source_name=src, target_name=tgt,
                relationship="related_to",
                reason="co-configured MCP servers",
            ))
