from __future__ import annotations

from pathlib import Path

import pytest

from nexus.db import (
    add_concept,
    add_conversation,
    add_edge,
    delete_concept,
    delete_edge,
    get_concept,
    get_connection,
    get_edges,
    init_db,
    list_concepts,
    search_fts,
    update_concept,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def conn(db_path: Path):
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


class TestInitDb:
    def test_creates_tables(self, conn):
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "concepts" in tables
        assert "edges" in tables
        assert "resources" in tables
        assert "conversations" in tables
        assert "_migrations" in tables

    def test_idempotent(self, db_path: Path):
        init_db(db_path)
        init_db(db_path)
        c = get_connection(db_path)
        migrations = c.execute("SELECT COUNT(*) FROM _migrations").fetchone()[0]
        c.close()
        assert migrations == 1

    def test_pragmas(self, conn):
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert journal == "wal"
        assert fk == 1


class TestConcepts:
    def test_add_and_get(self, conn):
        c = add_concept(conn, "React", category="framework", tags=["frontend"])
        assert c.name == "React" and c.category == "framework" and c.tags == ["frontend"]
        fetched = get_concept(conn, c.id)
        assert fetched is not None and fetched.name == "React"

    def test_get_by_name_case_insensitive(self, conn):
        add_concept(conn, "React")
        assert get_concept(conn, "react") is not None
        assert get_concept(conn, "REACT") is not None

    def test_get_nonexistent(self, conn):
        assert get_concept(conn, "nope") is None

    def test_list_empty(self, conn):
        assert list_concepts(conn) == []

    def test_list_with_category_filter(self, conn):
        add_concept(conn, "React", category="framework")
        add_concept(conn, "SQLite", category="concept")
        frameworks = list_concepts(conn, category="framework")
        assert len(frameworks) == 1
        assert frameworks[0].name == "React"

    def test_list_respects_limit(self, conn):
        for i in range(5):
            add_concept(conn, f"concept_{i}")
        assert len(list_concepts(conn, limit=3)) == 3

    def test_update(self, conn):
        c = add_concept(conn, "React")
        updated = update_concept(conn, c.id, category="framework", notes="Great lib")
        assert updated is not None
        assert updated.category == "framework"
        assert updated.notes == "Great lib"

    def test_update_tags(self, conn):
        c = add_concept(conn, "React")
        updated = update_concept(conn, c.id, tags=["frontend", "ui"])
        assert updated is not None
        assert updated.tags == ["frontend", "ui"]

    def test_delete(self, conn):
        c = add_concept(conn, "React")
        assert delete_concept(conn, c.id)
        assert get_concept(conn, c.id) is None

    def test_delete_nonexistent(self, conn):
        assert not delete_concept(conn, "fake-id")

    def test_unique_name(self, conn):
        add_concept(conn, "React")
        with pytest.raises(Exception, match="UNIQUE"):
            add_concept(conn, "React")


class TestEdges:
    def test_add_and_get(self, conn):
        a = add_concept(conn, "Claude Code")
        b = add_concept(conn, "MCP Servers")
        edge = add_edge(conn, a.id, b.id, "uses", description="Tool protocol")
        assert edge.relationship == "uses"
        assert edge.source_id == a.id
        assert edge.target_id == b.id

        edges = get_edges(conn, a.id)
        assert len(edges) == 1
        assert edges[0].id == edge.id

    def test_get_edges_both_directions(self, conn):
        a = add_concept(conn, "A")
        b = add_concept(conn, "B")
        add_edge(conn, a.id, b.id, "uses")
        assert len(get_edges(conn, a.id)) == 1
        assert len(get_edges(conn, b.id)) == 1

    def test_delete_edge(self, conn):
        a = add_concept(conn, "A")
        b = add_concept(conn, "B")
        edge = add_edge(conn, a.id, b.id, "uses")
        assert delete_edge(conn, edge.id)
        assert get_edges(conn, a.id) == []

    def test_cascade_on_concept_delete(self, conn):
        a = add_concept(conn, "A")
        b = add_concept(conn, "B")
        add_edge(conn, a.id, b.id, "uses")
        delete_concept(conn, a.id)
        assert get_edges(conn, b.id) == []

    def test_unique_constraint(self, conn):
        a = add_concept(conn, "A")
        b = add_concept(conn, "B")
        add_edge(conn, a.id, b.id, "uses")
        with pytest.raises(Exception, match="UNIQUE"):
            add_edge(conn, a.id, b.id, "uses")


class TestConversations:
    def test_add_and_retrieve(self, conn):
        c = add_concept(conn, "React")
        conv = add_conversation(conn, "What is React?", "A UI library.", [c.id])
        assert conv.question == "What is React?"
        assert conv.related_concepts == [c.id]
        no_concepts = add_conversation(conn, "General?", "An answer.")
        assert no_concepts.related_concepts == []


class TestFTS:
    def test_search_by_name(self, conn):
        add_concept(conn, "React", description="A JavaScript UI library")
        results = search_fts(conn, "React")
        assert len(results) == 1
        assert results[0].name == "React"

    def test_search_by_description(self, conn):
        add_concept(conn, "React", description="A JavaScript UI library")
        results = search_fts(conn, "JavaScript")
        assert len(results) == 1

    def test_search_no_results(self, conn):
        add_concept(conn, "React")
        assert search_fts(conn, "nonexistent") == []

    def test_search_after_update(self, conn):
        c = add_concept(conn, "React", description="old")
        update_concept(conn, c.id, description="A JavaScript UI library")
        results = search_fts(conn, "JavaScript")
        assert len(results) == 1

    def test_search_after_delete(self, conn):
        c = add_concept(conn, "React")
        delete_concept(conn, c.id)
        assert search_fts(conn, "React") == []
