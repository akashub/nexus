from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def settings_path(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_SETTINGS", path)
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_JSON", tmp_path / ".claude.json")
    monkeypatch.setattr("nexus.cli_mcp.SKILL_DIR", tmp_path / "skills" / "nexus")
    return path


def test_merges_with_existing_hooks(settings_path):
    from nexus.cli_mcp import _install_hooks
    settings_path.write_text(json.dumps({
        "hooks": {
            "PostToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "/path/to/eagle-mem.sh"}]},
            ],
            "SessionEnd": [
                {"hooks": [{"type": "command", "command": "/path/to/eagle-summary.sh"}]},
            ],
        }
    }))

    _install_hooks(quiet=True)
    data = json.loads(settings_path.read_text())

    ptu = data["hooks"]["PostToolUse"]
    assert len(ptu) == 2
    assert any("eagle-mem" in str(e) for e in ptu)
    assert any("post-tool-use" in str(e) for e in ptu)

    se = data["hooks"]["SessionEnd"]
    assert len(se) == 2
    assert any("eagle-summary" in str(e) for e in se)
    assert any("session-end" in str(e) for e in se)


def test_no_duplicate_hooks(settings_path):
    from nexus.cli_mcp import _install_hooks
    _install_hooks(quiet=True)
    _install_hooks(quiet=True)

    data = json.loads(settings_path.read_text())
    ptu = data["hooks"]["PostToolUse"]
    nexus_hooks = [e for e in ptu if "post-tool-use" in str(e)]
    assert len(nexus_hooks) == 1
