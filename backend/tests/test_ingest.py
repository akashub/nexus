from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept, get_concept, list_concepts
from nexus.cli_ingest import _process_entry


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def test_ingest_new_concept(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    _process_entry(conn, {"name": "react", "project_dir": "/tmp/proj", "category": "framework"})
    c = get_concept(conn, "react")
    assert c is not None
    assert c.source == "ledger"
    assert c.category == "framework"


def test_ingest_existing_adds_notes(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    c = add_concept(conn, "react", project_id=p.id)
    _process_entry(conn, {"name": "react", "notes": "good for UI"})
    updated = get_concept(conn, c.id)
    assert "good for UI" in updated.notes


def test_ingest_existing_no_overwrite_description(conn):
    p = add_project(conn, "proj", path="/tmp/proj")
    from nexus.db_concepts import update_concept
    c = add_concept(conn, "react", project_id=p.id)
    update_concept(conn, c.id, description="Original desc")
    _process_entry(conn, {"name": "react", "description": "New desc"})
    updated = get_concept(conn, c.id)
    assert updated.description == "Original desc"


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

    db_path = tmp_path / "test.db"
    monkeypatch.setattr("nexus.cli_ingest.get_connection", lambda: conn)

    add_project(conn, "proj", path="/tmp/proj")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"name": "react", "project_dir": "/tmp/proj"}) + "\n"
        + json.dumps({"name": "vue", "project_dir": "/tmp/proj"}) + "\n"
    )

    runner = CliRunner()
    result = runner.invoke(ingest_cmd, [str(ledger)])
    assert result.exit_code == 0
    assert "2 entries" in result.output
    assert not ledger.exists()
