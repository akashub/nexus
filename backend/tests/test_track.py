from __future__ import annotations

from pathlib import Path

import pytest

from nexus.cli_track import track_concept
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
