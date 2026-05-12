from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

import click

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
SKILL_DIR = Path.home() / ".claude" / "skills" / "nexus"
SKILL_SRC = Path(__file__).parent / "skill" / "nexus.md"
HOOKS_DIR = Path.home() / ".nexus" / "hooks"
_PKG_HOOKS = Path(__file__).parent / "hooks"
_HOOK_SCRIPTS = ("post-tool-use.sh", "session-end.sh")


_VSCODE_PATH = (Path.home() / "Library/Application Support/Code/User/mcp.json"
                if sys.platform == "darwin"
                else Path.home() / ".config/Code/User/mcp.json")
_ENTRY = {"command": "nexus", "args": ["mcp", "serve"], "env": {}}

_JSON_TOOLS: dict[str, tuple[str, Path, str, dict]] = {
    "claude": ("Claude Code", Path.home() / ".claude.json", "mcpServers", _ENTRY),
    "cursor": ("Cursor", Path.home() / ".cursor/mcp.json", "mcpServers", _ENTRY),
    "windsurf": (
        "Windsurf", Path.home() / ".codeium/windsurf/mcp_config.json",
        "mcpServers", _ENTRY,
    ),
    "vscode": ("VS Code", _VSCODE_PATH, "servers",
               {"type": "stdio", "command": "nexus", "args": ["mcp", "serve"]}),
    "gemini": ("Gemini CLI", Path.home() / ".gemini/settings.json", "mcpServers", _ENTRY),
}
_CODEX_PATH = Path.home() / ".codex/config.toml"
_CODEX_SECTION = '\n[mcp_servers.nexus]\ncommand = "nexus"\nargs = ["mcp", "serve"]\n'
ALL_TOOLS = list(_JSON_TOOLS) + ["codex"]

CLAUDE_JSON = _JSON_TOOLS["claude"][1]
MCP_ENTRY = _ENTRY


def _read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _detect_tools() -> list[str]:
    h = Path.home()
    m = {"claude": h / ".claude", "cursor": h / ".cursor", "windsurf": h / ".codeium",
         "vscode": _VSCODE_PATH.parent.parent, "codex": h / ".codex", "gemini": h / ".gemini"}
    return [k for k, p in m.items() if p.exists()]


def _install_mcp_json(key: str, quiet: bool) -> None:
    name, path, root_key, entry = _JSON_TOOLS[key]
    data = _read_json(path)
    servers = data.setdefault(root_key, {})
    if servers.get("nexus") == entry:
        if not quiet:
            click.echo(f"  {name}: already configured")
        return
    servers["nexus"] = entry
    _write_json(path, data)
    if not quiet:
        click.echo(f"  {name}: configured")


def _install_codex(quiet: bool) -> None:
    text = _CODEX_PATH.read_text() if _CODEX_PATH.exists() else ""
    if "[mcp_servers.nexus]" in text:
        if not quiet:
            click.echo("  Codex: already configured")
        return
    _CODEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CODEX_PATH, "a") as f:
        f.write(_CODEX_SECTION)
    if not quiet:
        click.echo("  Codex: configured")


_HOOK_MARKERS = ("nexus/hooks/post-tool-use.sh", "nexus/hooks/session-end.sh")


def _is_nexus_hook(entry: dict) -> bool:
    return any(any(m in h.get("command", "") for m in _HOOK_MARKERS)
               for h in entry.get("hooks", []))


def _install_hooks(quiet: bool) -> None:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for name in _HOOK_SCRIPTS:
        src = _PKG_HOOKS / name
        if src.exists():
            dest = HOOKS_DIR / name
            shutil.copy2(src, dest)
            os.chmod(dest, 0o755)
    data = _read_json(CLAUDE_SETTINGS)
    hooks = data.setdefault("hooks", {})
    ptu = str(HOOKS_DIR / "post-tool-use.sh")
    se = str(HOOKS_DIR / "session-end.sh")
    hooks["PostToolUse"] = [e for e in hooks.get("PostToolUse", []) if not _is_nexus_hook(e)]
    hooks["PostToolUse"].append({"matcher": "Bash", "hooks": [{"type": "command", "command": ptu}]})
    hooks["SessionEnd"] = [e for e in hooks.get("SessionEnd", []) if not _is_nexus_hook(e)]
    hooks["SessionEnd"].append({"hooks": [{"type": "command", "command": se}]})
    _write_json(CLAUDE_SETTINGS, data)
    if not quiet:
        click.echo("  Hooks: installed (Claude Code PostToolUse + SessionEnd)")


def _install_skill(quiet: bool) -> None:
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    dest = SKILL_DIR / "SKILL.md"
    if SKILL_SRC.exists():
        shutil.copy2(SKILL_SRC, dest)
        if not quiet:
            click.echo("  Skill: installed (Claude Code)")
    elif not quiet:
        click.echo("  Skill: source not found, skipping")


def _uninstall(quiet: bool) -> None:
    for _key, (name, path, root_key, _) in _JSON_TOOLS.items():
        data = _read_json(path)
        if root_key in data and "nexus" in data[root_key]:
            del data[root_key]["nexus"]
            _write_json(path, data)
            if not quiet:
                click.echo(f"  {name}: removed")
    if _CODEX_PATH.exists():
        text = _CODEX_PATH.read_text()
        if "[mcp_servers.nexus]" in text:
            text = re.sub(r"\n?\[mcp_servers\.nexus\][^\[]*", "", text)
            _CODEX_PATH.write_text(text.strip() + "\n" if text.strip() else "")
            if not quiet:
                click.echo("  Codex: removed")
    for name in ("SKILL.md", "nexus.md"):
        p = SKILL_DIR / name
        if p.exists():
            p.unlink()
    if not quiet:
        click.echo("  Skill: removed")


@click.group("mcp")
def mcp_group() -> None:
    """MCP server management."""


@mcp_group.command("install")
@click.option("--check", is_flag=True, help="Check installation status.")
@click.option("--uninstall", is_flag=True, help="Remove Nexus integration.")
@click.option("--tool", "tool_name", help="Target one tool.")
@click.option("--quiet", "-q", is_flag=True)
def install_cmd(check: bool, uninstall: bool, tool_name: str | None, quiet: bool) -> None:
    """Install Nexus MCP server into AI coding tools."""
    if check:
        for _k, (name, path, root_key, entry) in _JSON_TOOLS.items():
            ok = _read_json(path).get(root_key, {}).get("nexus") == entry
            click.echo(f"  {name:<14} {'ok' if ok else '--'}")
        codex_ok = _CODEX_PATH.exists() and "[mcp_servers.nexus]" in _CODEX_PATH.read_text()
        click.echo(f"  {'Codex':<14} {'ok' if codex_ok else '--'}")
        click.echo(f"  {'Skill':<14} {'ok' if (SKILL_DIR / 'SKILL.md').exists() else '--'}")
        return
    if uninstall:
        _uninstall(quiet)
        return
    if tool_name:
        if tool_name not in ALL_TOOLS:
            opts = ", ".join(ALL_TOOLS)
            raise click.ClickException(f"Unknown tool: {tool_name}. Options: {opts}")
        tools = [tool_name]
    else:
        tools = _detect_tools() or ["claude"]
        if not quiet:
            names = [_JSON_TOOLS[k][0] if k != "codex" else "Codex" for k in tools]
            click.echo(f"Detected: {', '.join(names)}")
    for key in tools:
        _install_codex(quiet) if key == "codex" else _install_mcp_json(key, quiet)
    if not tool_name or tool_name == "claude":
        _install_hooks(quiet)
        _install_skill(quiet)
    if not quiet:
        click.echo("Done.")


@mcp_group.command("serve")
def serve_cmd() -> None:
    """Start the Nexus MCP server (stdio transport)."""
    from nexus.mcp_server import run_server
    run_server()
