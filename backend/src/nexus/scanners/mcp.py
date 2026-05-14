from __future__ import annotations

import json
import re
from pathlib import Path

from nexus.scanners import ScannedConcept, ScannedRelationship, ScanResult, is_valid_concept_name

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


def _extract_tool_name(key: str, config) -> str:
    """Derive a meaningful tool name from the MCP server key and config.

    Prefer the dict key when it's a valid concept name — users typically
    choose short, meaningful keys like "context7" or "shadcn". Only fall
    back to parsing args when the key is invalid.
    """
    if is_valid_concept_name(key):
        return key
    if not isinstance(config, dict):
        return key
    args = config.get("args", [])
    if not isinstance(args, list):
        return key
    for arg in args:
        arg = str(arg)
        if arg.startswith("-"):
            continue
        if "/" in arg and not arg.startswith("/"):
            pkg = arg.rsplit("/", 1)[-1]
            pkg = re.sub(r"[_-]mcp(@.*)?$", "", pkg)
            if pkg and is_valid_concept_name(pkg):
                return pkg
        base = arg.rsplit("/", 1)[-1]
        base = re.sub(r"[_-]mcp(@.*)?$", "", base)
        if base and is_valid_concept_name(base):
            return base
    return key


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
    for key, config in servers.items():
        name = _extract_tool_name(key, config)
        if name.lower() in seen:
            continue
        if not is_valid_concept_name(name):
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
