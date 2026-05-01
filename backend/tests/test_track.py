from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from nexus.cli_track import track_cmd, track_concept
from nexus.db import add_project, get_connection, get_project_by_path, init_db
from nexus.db_concepts import get_concept


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def test_track_new_concept(conn):
    p = add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "react", "/tmp/test-proj", source="npm")
    assert result["status"] == "added"
    c = get_concept(conn, result["id"])
    assert c is not None
    assert c.name == "react"
    assert c.source == "hook_capture"
    assert c.project_id == p.id
    assert c.category == "framework"


def test_track_existing_noop(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    r1 = track_concept(conn, "react", "/tmp/test-proj", source="npm")
    r2 = track_concept(conn, "react", "/tmp/test-proj", source="npm")
    assert r1["status"] == "added"
    assert r2["status"] == "exists"
    assert r1["id"] == r2["id"]


def test_track_auto_creates_project(conn, tmp_path):
    proj_dir = str(tmp_path / "my-app")
    (tmp_path / "my-app").mkdir()
    result = track_concept(conn, "express", proj_dir, source="npm")
    assert result["status"] == "added"
    proj = get_project_by_path(conn, proj_dir)
    assert proj is not None
    assert proj.name == "my-app"


def test_track_dev_dependency(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "vitest", "/tmp/test-proj", source="npm", dev=True)
    c = get_concept(conn, result["id"])
    assert c is not None
    assert "npm install -D vitest" in (c.setup_commands or [])


def test_track_pip_source(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "fastapi", "/tmp/test-proj", source="pip")
    c = get_concept(conn, result["id"])
    assert c.category == "framework"
    assert "pip install fastapi" in (c.setup_commands or [])


def test_track_brew_source(conn):
    add_project(conn, "brew-proj", path="/tmp/brew-proj")
    result = track_concept(conn, "ripgrep", "/tmp/brew-proj", source="brew")
    c = get_concept(conn, result["id"])
    assert c is not None
    assert c.category == "devtool"
    assert "brew install ripgrep" in (c.setup_commands or [])


def test_track_cargo_source(conn):
    add_project(conn, "cargo-proj", path="/tmp/cargo-proj")
    result = track_concept(conn, "serde", "/tmp/cargo-proj", source="cargo")
    c = get_concept(conn, result["id"])
    assert c is not None
    assert c.category == "framework"
    assert "cargo add serde" in (c.setup_commands or [])


def test_track_rejects_empty_name(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "", "/tmp/test-proj", source="npm")
    assert result["status"] == "error"


def test_track_rejects_whitespace_name(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "   ", "/tmp/test-proj", source="npm")
    assert result["status"] == "error"


def test_track_rejects_shell_injection_name(conn):
    add_project(conn, "test-proj", path="/tmp/test-proj")
    result = track_concept(conn, "$(rm -rf /)", "/tmp/test-proj", source="npm")
    assert result["status"] == "error"


def test_track_same_name_different_projects(conn, tmp_path):
    """Concept with same name in different projects does not crash."""
    a = tmp_path / "proj-a"
    a.mkdir()
    b = tmp_path / "proj-b"
    b.mkdir()
    r1 = track_concept(conn, "react", str(a), source="npm")
    assert r1["status"] == "added"
    r2 = track_concept(conn, "react", str(b), source="npm")
    assert r2["status"] == "exists"
    assert r2["id"] == r1["id"]


def test_track_same_dir_name_different_paths(conn, tmp_path):
    """Two directories named 'app' at different paths do not crash."""
    (tmp_path / "foo" / "app").mkdir(parents=True)
    (tmp_path / "bar" / "app").mkdir(parents=True)
    r1 = track_concept(conn, "react", str(tmp_path / "foo" / "app"), source="npm")
    assert r1["status"] == "added"
    r2 = track_concept(conn, "express", str(tmp_path / "bar" / "app"), source="npm")
    assert r2["status"] == "added"


def test_track_cli_added(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    monkeypatch.setattr(
        "nexus.cli_track.get_connection", lambda: get_connection(db_path),
    )
    proj_dir = tmp_path / "my-proj"
    proj_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        track_cmd,
        ["express", "--project-dir", str(proj_dir), "--source", "npm"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Tracked: express" in result.output


def test_track_cli_quiet(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    monkeypatch.setattr(
        "nexus.cli_track.get_connection", lambda: get_connection(db_path),
    )
    proj_dir = tmp_path / "my-proj"
    proj_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        track_cmd,
        ["express", "--project-dir", str(proj_dir), "--source", "npm", "--quiet"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == ""
