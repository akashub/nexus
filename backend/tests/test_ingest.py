from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.cli_ingest import _process_entry, _process_relationships
from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept, get_concept, get_edges


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def test_ingest_new_concept(conn):
    add_project(conn, "proj", path="/tmp/proj")
    _process_entry(conn, {"name": "react", "project_dir": "/tmp/proj", "category": "framework"})
    c = get_concept(conn, "react")
    assert c is not None
    assert c.source == "ledger"
    assert c.category == "framework"


def test_ingest_rich_entry(conn):
    add_project(conn, "proj", path="/tmp/proj")
    _process_entry(conn, {
        "name": "playwright",
        "description": "E2E testing framework with multi-browser support",
        "summary": "E2E browser testing with auto-wait",
        "category": "devtool",
        "context": "Added for auth flow E2E tests",
        "project_dir": "/tmp/proj",
    })
    c = get_concept(conn, "playwright")
    assert c.description == "E2E testing framework with multi-browser support"
    assert c.summary == "E2E browser testing with auto-wait"
    assert c.category == "devtool"
    assert "auth flow" in c.notes


def test_ingest_existing_fills_gaps(conn):
    add_project(conn, "proj", path="/tmp/proj")
    add_concept(conn, "react", project_id=None)
    _process_entry(conn, {
        "name": "react",
        "description": "UI library",
        "summary": "Component-based UI",
        "category": "framework",
        "context": "Used for dashboard",
    })
    c = get_concept(conn, "react")
    assert c.description == "UI library"
    assert c.summary == "Component-based UI"
    assert c.category == "framework"
    assert "dashboard" in c.notes


def test_ingest_existing_no_overwrite_description(conn):
    from nexus.db_concepts import update_concept
    c = add_concept(conn, "react")
    update_concept(conn, c.id, description="Original desc")
    _process_entry(conn, {"name": "react", "description": "New desc"})
    updated = get_concept(conn, c.id)
    assert updated.description == "Original desc"


def test_ingest_relationships(conn):
    add_concept(conn, "vitest")
    add_concept(conn, "react")
    created = _process_relationships(conn, [
        ("vitest", {"target": "react", "type": "tested_with"}),
    ])
    assert created == 1
    edges = get_edges(conn, get_concept(conn, "vitest").id)
    assert len(edges) == 1
    assert edges[0].relationship == "tested_with"


def test_ingest_relationships_skips_missing_target(conn):
    add_concept(conn, "vitest")
    created = _process_relationships(conn, [
        ("vitest", {"target": "nonexistent", "type": "uses"}),
    ])
    assert created == 0


def test_ingest_relationships_skips_invalid_type(conn):
    add_concept(conn, "vitest")
    add_concept(conn, "react")
    created = _process_relationships(conn, [
        ("vitest", {"target": "react", "type": "invented_rel"}),
    ])
    assert created == 0


def test_ingest_relationships_dedup(conn):
    add_concept(conn, "vitest")
    add_concept(conn, "react")
    _process_relationships(conn, [
        ("vitest", {"target": "react", "type": "uses"}),
    ])
    created = _process_relationships(conn, [
        ("vitest", {"target": "react", "type": "uses"}),
    ])
    assert created == 0


def test_ingest_auto_creates_project(conn, tmp_path):
    proj_dir = tmp_path / "my-app"
    proj_dir.mkdir()
    _process_entry(conn, {"name": "express", "project_dir": str(proj_dir)})
    c = get_concept(conn, "express")
    assert c is not None
    assert c.project_id is not None


def test_ingest_ledger_file(conn, tmp_path, monkeypatch):
    from click.testing import CliRunner

    from nexus.cli_ingest import ingest_cmd

    monkeypatch.setattr("nexus.cli_ingest.get_connection", lambda: conn)

    add_project(conn, "proj", path="/tmp/proj")
    add_concept(conn, "react")
    ledger = tmp_path / "ledger.jsonl"
    entry1 = {
        "name": "playwright", "description": "E2E testing",
        "category": "devtool", "project_dir": "/tmp/proj",
        "relationships": [{"target": "react", "type": "tested_with"}],
    }
    entry2 = {"name": "vitest", "project_dir": "/tmp/proj"}
    ledger.write_text(json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n")

    runner = CliRunner()
    result = runner.invoke(ingest_cmd, [str(ledger)])
    assert result.exit_code == 0
    assert "2 concepts" in result.output
    assert "1 edges" in result.output
    assert not ledger.exists()
