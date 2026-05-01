from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept, add_edge, update_concept
from nexus.expertise import classify_expertise


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def _fake_embedding() -> bytes:
    return struct.pack("4f", 0.1, 0.2, 0.3, 0.4)


def test_known_well_all_signals(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c1 = add_concept(conn, "react", category="framework", project_id=p.id)
    update_concept(conn, c1.id, description="A UI library", embedding=_fake_embedding())
    c2 = add_concept(conn, "redux", category="framework", project_id=p.id)
    update_concept(conn, c2.id, description="State management", embedding=_fake_embedding())
    add_edge(conn, c1.id, c2.id, "uses")

    profile = classify_expertise(conn, p.id)
    names = [e.name for e in profile.known_well]
    assert "react" in names
    assert any("desc" in e.signals for e in profile.known_well if e.name == "react")


def test_seen_missing_embedding(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c1 = add_concept(conn, "tailwind", category="framework", project_id=p.id)
    update_concept(conn, c1.id, description="CSS utility framework")
    c2 = add_concept(conn, "react", category="framework", project_id=p.id)
    add_edge(conn, c1.id, c2.id, "uses")

    profile = classify_expertise(conn, p.id)
    names = [e.name for e in profile.seen]
    assert "tailwind" in names


def test_seen_no_edges(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c = add_concept(conn, "vite", category="devtool", project_id=p.id)
    update_concept(conn, c.id, description="Build tool", embedding=_fake_embedding())

    profile = classify_expertise(conn, p.id)
    names = [e.name for e in profile.seen]
    assert "vite" in names


def test_gap_detection(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18.0.0", "express": "^4.0.0"},
    }))
    p = add_project(conn, "myapp", path=str(proj_dir))
    add_concept(conn, "react", category="framework", project_id=p.id)

    profile = classify_expertise(conn, p.id)
    gap_names = [e.name for e in profile.gaps]
    assert "express" in gap_names
    assert "react" not in gap_names


def test_no_false_gaps(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18.0.0"},
    }))
    p = add_project(conn, "myapp", path=str(proj_dir))
    add_concept(conn, "react", category="framework", project_id=p.id)

    profile = classify_expertise(conn, p.id)
    gap_names = [e.name for e in profile.gaps]
    assert len(gap_names) == 0


def test_mixed_profile(conn, tmp_path):
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18", "express": "^4", "playwright": "^1"},
    }))
    p = add_project(conn, "myapp", path=str(proj_dir))

    c1 = add_concept(conn, "react", category="framework", project_id=p.id)
    update_concept(conn, c1.id, description="UI lib", embedding=_fake_embedding())
    c2 = add_concept(conn, "express", category="framework", project_id=p.id)
    add_edge(conn, c1.id, c2.id, "uses")

    profile = classify_expertise(conn, p.id)
    assert len(profile.known_well) == 1
    assert profile.known_well[0].name == "react"
    assert len(profile.seen) == 1
    assert profile.seen[0].name == "express"
    assert len(profile.gaps) == 1
    assert profile.gaps[0].name == "playwright"
    assert profile.total == 3
