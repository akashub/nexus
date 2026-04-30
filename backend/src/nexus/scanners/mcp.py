from __future__ import annotations

import json
from pathlib import Path

from nexus.scanners import ScannedConcept, ScanResult

_MCP_PATHS = [
    Path.home() / ".claude" / "plugins.json",
    Path.home() / ".claude.json",
]


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

    for name, config in servers.items():
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        cmd = ""
        if isinstance(config, dict):
            cmd = config.get("command", "")
            args = config.get("args", [])
            if isinstance(args, list):
                cmd = f"{cmd} {' '.join(str(a) for a in args[:3])}"

        result.concepts.append(ScannedConcept(
            name=name, source="mcp_config", category_hint="devtool",
            context=f"MCP server: {cmd.strip()[:80]}" if cmd.strip() else None,
        ))
