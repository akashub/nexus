from __future__ import annotations

import json

import click

from nexus.cli_mcp import CLAUDE_JSON, CLAUDE_SETTINGS, MCP_ENTRY, SKILL_DIR
from nexus.db import DB_PATH, get_connection, list_projects
from nexus.db_concepts import count_concepts, count_edges


def _check(label: str, ok: bool, detail: str) -> None:
    mark = click.style("ok", fg="green") if ok else click.style("--", fg="red")
    click.echo(f"  {label:<14} {mark}  {detail}")


@click.command("status")
def status_cmd() -> None:
    """Show Nexus integration status."""
    click.echo("Nexus Integration Status\n")

    db_exists = DB_PATH.exists()
    if db_exists:
        conn = get_connection()
        try:
            n_concepts = count_concepts(conn)
            n_edges = count_edges(conn)
            n_projects = len(list_projects(conn))
        finally:
            conn.close()
        _check(
            "Database", True,
            f"{DB_PATH} ({n_concepts} concepts, {n_projects} projects, {n_edges} edges)",
        )
    else:
        _check("Database", False, f"{DB_PATH} (not found)")

    data = {}
    if CLAUDE_JSON.exists():
        data = json.loads(CLAUDE_JSON.read_text())
    mcp_ok = data.get("mcpServers", {}).get("nexus") == MCP_ENTRY
    _check(
        "MCP Server", mcp_ok,
        "in ~/.claude.json" if mcp_ok else "not installed",
    )

    hooks_ok = False
    if CLAUDE_SETTINGS.exists():
        settings = json.loads(CLAUDE_SETTINGS.read_text())
        hooks = settings.get("hooks", {})
        has_ptu = any("post-tool-use" in str(e) for e in hooks.get("PostToolUse", []))
        has_se = any("session-end" in str(e) for e in hooks.get("SessionEnd", []))
        hooks_ok = has_ptu and has_se
    _check("Hooks", hooks_ok, "PostToolUse + SessionEnd" if hooks_ok else "not installed")

    skill_ok = (SKILL_DIR / "SKILL.md").exists()
    _check("Skill", skill_ok, str(SKILL_DIR / "SKILL.md") if skill_ok else "not installed")

    try:
        import httpx

        from nexus.ai import EMBED_MODEL, LLM_MODEL
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        has_llm = any(LLM_MODEL in m for m in models)
        has_embed = any(EMBED_MODEL in m for m in models)
        if has_llm and has_embed:
            _check("Ollama", True, f"{LLM_MODEL} + {EMBED_MODEL}")
        else:
            missing = []
            if not has_llm:
                missing.append(LLM_MODEL)
            if not has_embed:
                missing.append(EMBED_MODEL)
            _check("Ollama", False, f"missing: {', '.join(missing)}")
    except Exception:
        _check("Ollama", False, "not running")
