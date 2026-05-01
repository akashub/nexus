from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path

import click

CLAUDE_JSON = Path.home() / ".claude.json"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
SKILL_DIR = Path.home() / ".claude" / "skills" / "nexus"
SKILL_SRC = Path(__file__).parent / "skill" / "nexus.md"

MCP_ENTRY = {"command": "nexus", "args": ["mcp", "serve"], "env": {}}


def _hook_path(name: str) -> str:
    return str(files("nexus") / "hooks" / name)


def _read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _install_mcp(quiet: bool) -> None:
    data = _read_json(CLAUDE_JSON)
    servers = data.setdefault("mcpServers", {})
    if servers.get("nexus") == MCP_ENTRY:
        if not quiet:
            click.echo("  MCP server: already installed")
        return
    servers["nexus"] = MCP_ENTRY
    _write_json(CLAUDE_JSON, data)
    if not quiet:
        click.echo("  MCP server: installed")


def _install_hooks(quiet: bool) -> None:
    data = _read_json(CLAUDE_SETTINGS)
    hooks = data.setdefault("hooks", {})

    post_tool = hooks.setdefault("PostToolUse", [])
    ptu_cmd = _hook_path("post-tool-use.sh")
    if not any(_has_command(entry, ptu_cmd) for entry in post_tool):
        post_tool.append({
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": ptu_cmd}],
        })
        if not quiet:
            click.echo("  PostToolUse hook: installed")
    elif not quiet:
        click.echo("  PostToolUse hook: already installed")

    session_end = hooks.setdefault("SessionEnd", [])
    se_cmd = _hook_path("session-end.sh")
    if not any(_has_command(entry, se_cmd) for entry in session_end):
        session_end.append({
            "hooks": [{"type": "command", "command": se_cmd}],
        })
        if not quiet:
            click.echo("  SessionEnd hook: installed")
    elif not quiet:
        click.echo("  SessionEnd hook: already installed")

    _write_json(CLAUDE_SETTINGS, data)


def _has_command(entry: dict, cmd: str) -> bool:
    return any(h.get("command") == cmd for h in entry.get("hooks", []))


def _install_skill(quiet: bool) -> None:
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    dest = SKILL_DIR / "SKILL.md"
    old = SKILL_DIR / "nexus.md"
    if old.exists():
        old.unlink()
    if SKILL_SRC.exists():
        shutil.copy2(SKILL_SRC, dest)
        if not quiet:
            click.echo(f"  Skill file: installed to {dest}")
    elif not quiet:
        click.echo("  Skill file: source not found, skipping")


def _uninstall(quiet: bool) -> None:
    data = _read_json(CLAUDE_JSON)
    if "mcpServers" in data and "nexus" in data["mcpServers"]:
        del data["mcpServers"]["nexus"]
        _write_json(CLAUDE_JSON, data)
    if not quiet:
        click.echo("  MCP server: removed")

    for name in ("SKILL.md", "nexus.md"):
        p = SKILL_DIR / name
        if p.exists():
            p.unlink()
    if not quiet:
        click.echo("  Skill file: removed")


@click.group("mcp")
def mcp_group() -> None:
    """MCP server management."""


@mcp_group.command("install")
@click.option("--check", is_flag=True, help="Check installation status.")
@click.option("--uninstall", is_flag=True, help="Remove Nexus integration.")
@click.option("--quiet", "-q", is_flag=True)
def install_cmd(check: bool, uninstall: bool, quiet: bool) -> None:
    """Install Nexus MCP server, hooks, and skill into Claude Code."""
    if check:
        data = _read_json(CLAUDE_JSON)
        installed = data.get("mcpServers", {}).get("nexus") == MCP_ENTRY
        click.echo(f"MCP server: {'installed' if installed else 'not installed'}")
        skill = (SKILL_DIR / "SKILL.md").exists()
        click.echo(f"Skill file: {'installed' if skill else 'not installed'}")
        return

    if uninstall:
        _uninstall(quiet)
        return

    if not quiet:
        click.echo("Installing Nexus into Claude Code...")
    _install_mcp(quiet)
    _install_hooks(quiet)
    _install_skill(quiet)
    if not quiet:
        click.echo("Done.")


@mcp_group.command("serve")
def serve_cmd() -> None:
    """Start the Nexus MCP server (stdio transport)."""
    from nexus.mcp_server import run_server
    run_server()
