from __future__ import annotations

import struct
from pathlib import Path

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept, add_edge, get_concept, update_concept
from nexus.mcp_server import (
    add_concept as mcp_add_concept,
    get_concept_detail,
    get_expertise,
    list_projects,
    search_concepts,
    track_install,
)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    monkeypatch.setattr("nexus.mcp_server.get_connection", lambda: get_connection(db_path))
    yield c
    c.close()


def _fake_embedding() -> bytes:
    return struct.pack("4f", 0.1, 0.2, 0.3, 0.4)


def test_search_concepts_fts(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c = add_concept(conn, "react", category="framework", project_id=p.id)
    update_concept(conn, c.id, description="A JavaScript UI library")

    results = search_concepts("react")
    assert len(results) >= 1
    assert any(r["name"] == "react" for r in results)


def test_get_concept_with_edges(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c1 = add_concept(conn, "react", category="framework", project_id=p.id)
    c2 = add_concept(conn, "redux", category="framework", project_id=p.id)
    add_edge(conn, c1.id, c2.id, "uses")

    detail = get_concept_detail("react")
    assert detail["name"] == "react"
    assert len(detail["edges"]) == 1
    assert detail["edges"][0]["target"] == "redux"


def test_get_concept_not_found(conn):
    result = get_concept_detail("nonexistent")
    assert "error" in result


def test_list_projects(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", project_id=p.id)
    add_concept(conn, "vite", project_id=p.id)

    projects = list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "myapp"
    assert projects[0]["concept_count"] == 2


def test_get_expertise(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    p = add_project(conn, "myapp", path=str(proj_dir))
    c = add_concept(conn, "react", category="framework", project_id=p.id)
    update_concept(conn, c.id, description="UI lib", embedding=_fake_embedding())
    c2 = add_concept(conn, "vite", category="devtool", project_id=p.id)
    add_edge(conn, c.id, c2.id, "uses")

    result = get_expertise(project_id=p.id)
    assert result["project"] == "myapp"
    assert len(result["known_well"]) == 1
    assert len(result["seen"]) == 1


def test_track_install_new(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    add_project(conn, "myapp", path=str(proj_dir))

    result = track_install("express", "npm", str(proj_dir))
    assert result["status"] == "added"
    c = get_concept(conn, result["id"])
    assert c.name == "express"


def test_track_install_existing(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    add_project(conn, "myapp", path=str(proj_dir))

    r1 = track_install("express", "npm", str(proj_dir))
    r2 = track_install("express", "npm", str(proj_dir))
    assert r1["status"] == "added"
    assert r2["status"] == "exists"
