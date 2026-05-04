from __future__ import annotations

import json

import pytest


@pytest.fixture()
def settings_path(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_SETTINGS", path)
    monkeypatch.setattr("nexus.cli_mcp.CLAUDE_JSON", tmp_path / ".claude.json")
    monkeypatch.setattr("nexus.cli_mcp.SKILL_DIR", tmp_path / "skills" / "nexus")
    monkeypatch.setattr("nexus.cli_mcp.HOOKS_DIR", tmp_path / ".nexus" / "hooks")
    return path


def test_merges_with_existing_hooks(settings_path):
    from nexus.cli_mcp import _install_hooks
    settings_path.write_text(json.dumps({
        "hooks": {
            "PostToolUse": [
                {"matcher": "Bash", "hooks": [
                    {"type": "command", "command": "/path/to/eagle-mem.sh"},
                ]},
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


def test_preserves_eagle_mem_hooks(settings_path):
    from nexus.cli_mcp import _install_hooks
    settings_path.write_text(json.dumps({
        "hooks": {
            "PostToolUse": [
                {"matcher": "Read|Write|Edit|Bash", "hooks": [
                    {"type": "command", "command": "/home/user/.eagle-mem/hooks/post-tool-use.sh"},
                ]},
            ],
            "SessionEnd": [
                {"hooks": [
                    {"type": "command", "command": "/home/user/.eagle-mem/hooks/session-end.sh"},
                ]},
            ],
        }
    }))

    _install_hooks(quiet=True)
    data = json.loads(settings_path.read_text())

    ptu = data["hooks"]["PostToolUse"]
    assert len(ptu) == 2
    assert any("eagle-mem" in str(e) for e in ptu)
    assert any("nexus" in str(e) for e in ptu)

    se = data["hooks"]["SessionEnd"]
    assert len(se) == 2
    assert any("eagle-mem" in str(e) for e in se)
    assert any("nexus" in str(e) for e in se)


def test_cleans_stale_entries(settings_path):
    from nexus.cli_mcp import _install_hooks
    settings_path.write_text(json.dumps({
        "hooks": {
            "PostToolUse": [
                {"matcher": "Bash", "hooks": [
                    {"type": "command", "command": "/tmp/dead1/nexus/hooks/post-tool-use.sh"},
                ]},
                {"matcher": "Bash", "hooks": [
                    {"type": "command", "command": "/tmp/dead2/nexus/hooks/post-tool-use.sh"},
                ]},
                {"matcher": "Bash", "hooks": [{
                    "type": "command",
                    "command": "/real/nexus/src/nexus/hooks/post-tool-use.sh",
                }]},
                {"matcher": "Bash", "hooks": [
                    {"type": "command", "command": "/path/to/eagle-mem.sh"},
                ]},
            ],
            "SessionEnd": [
                {"hooks": [
                    {"type": "command", "command": "/tmp/dead1/nexus/hooks/session-end.sh"},
                ]},
            ],
        }
    }))

    _install_hooks(quiet=True)
    data = json.loads(settings_path.read_text())

    ptu = data["hooks"]["PostToolUse"]
    nexus_hooks = [e for e in ptu if "post-tool-use" in str(e)]
    assert len(nexus_hooks) == 1, f"Expected 1 nexus hook, got {len(nexus_hooks)}: {nexus_hooks}"

    assert any("eagle-mem" in str(e) for e in ptu)
    assert len(ptu) == 2

    se = data["hooks"]["SessionEnd"]
    nexus_se = [e for e in se if "session-end" in str(e)]
    assert len(nexus_se) == 1
