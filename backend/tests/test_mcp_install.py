from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.cli_mcp import MCP_ENTRY


@pytest.fixture()
def claude_json(tmp_path, monkeypatch):
    path = tmp_path / ".claude.json"
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_JSON", path)
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_SETTINGS", tmp_path / "settings.json")
    monkeypatch.setattr("nexus.cli_mcp.SKILL_DIR", tmp_path / "skills" / "nexus")
    return path


def _install(claude_json):
    from nexus.cli_mcp import _install_mcp
    _install_mcp(quiet=True)
    return json.loads(claude_json.read_text())


def test_install_fresh(claude_json):
    data = _install(claude_json)
    assert data["mcpServers"]["nexus"] == MCP_ENTRY


def test_install_idempotent(claude_json):
    _install(claude_json)
    data = _install(claude_json)
    assert data["mcpServers"]["nexus"] == MCP_ENTRY


def test_install_preserves_other_servers(claude_json):
    claude_json.write_text(json.dumps({
        "mcpServers": {"other-tool": {"command": "other", "args": []}},
    }))
    data = _install(claude_json)
    assert "other-tool" in data["mcpServers"]
    assert "nexus" in data["mcpServers"]


def test_uninstall(claude_json, monkeypatch):
    from nexus.cli_mcp import _uninstall
    _install(claude_json)
    monkeypatch.setattr("nexus.cli_mcp.SKILL_DIR", claude_json.parent / "skills" / "nexus")
    _uninstall(quiet=True)
    data = json.loads(claude_json.read_text())
    assert "nexus" not in data.get("mcpServers", {})


def test_check_installed(claude_json):
    _install(claude_json)
    data = json.loads(claude_json.read_text())
    assert data.get("mcpServers", {}).get("nexus") == MCP_ENTRY
