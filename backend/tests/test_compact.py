from __future__ import annotations

import struct
from pathlib import Path

import pytest

from nexus.compact import compact_project
from nexus.db import get_connection, init_db
from nexus.db_concepts import (
    add_concept,
    add_edge,
    get_concept,
    get_edges,
    update_concept,
)


@pytest.fixture()
def conn(tmp_path: Path):
    init_db(tmp_path / "test.db")
    c = get_connection(tmp_path / "test.db")
    yield c
    c.close()


def _fake_embed(val: float) -> bytes:
    return struct.pack(f"{768}f", *([val] * 768))


class TestMergeSimilar:
    def test_merges_hyphen_vs_underscore(self, conn):
        a = add_concept(conn, "react-router")
        b = add_concept(conn, "react_router")
        update_concept(conn, a.id, embedding=_fake_embed(1.0), description="router")
        update_concept(conn, b.id, embedding=_fake_embed(1.0))
        stats = compact_project(conn, similarity_threshold=0.9)
        assert stats.merged == 1
        assert get_concept(conn, a.id) is not None
        assert get_concept(conn, b.id) is None

    def test_no_merge_different_names(self, conn):
        a = add_concept(conn, "react")
        b = add_concept(conn, "vue")
        update_concept(conn, a.id, embedding=_fake_embed(1.0))
        update_concept(conn, b.id, embedding=_fake_embed(1.0))
        stats = compact_project(conn, similarity_threshold=0.9)
        assert stats.merged == 0

    def test_merge_transfers_description(self, conn):
        a = add_concept(conn, "my-tool")
        b = add_concept(conn, "my_tool")
        update_concept(conn, a.id, embedding=_fake_embed(1.0))
        update_concept(conn, b.id, embedding=_fake_embed(1.0), description="great tool")
        compact_project(conn)
        kept = get_concept(conn, a.id)
        assert kept.description == "great tool"

    def test_merge_retargets_edges(self, conn):
        a = add_concept(conn, "my-lib")
        b = add_concept(conn, "my_lib")
        c = add_concept(conn, "consumer")
        update_concept(conn, a.id, embedding=_fake_embed(1.0))
        update_concept(conn, b.id, embedding=_fake_embed(1.0))
        add_edge(conn, c.id, b.id, "uses")
        compact_project(conn)
        edges = get_edges(conn, a.id)
        assert any(e.source_id == c.id and e.target_id == a.id for e in edges)

    def test_dry_run_no_changes(self, conn):
        a = add_concept(conn, "dry-tool")
        b = add_concept(conn, "dry_tool")
        update_concept(conn, a.id, embedding=_fake_embed(1.0))
        update_concept(conn, b.id, embedding=_fake_embed(1.0))
        stats = compact_project(conn, dry_run=True)
        assert stats.merged == 1
        assert get_concept(conn, b.id) is not None


class TestRemoveStale:
    def test_removes_old_auto_scan(self, conn):
        a = add_concept(conn, "stale-pkg", source="auto_scan")
        conn.execute(
            "UPDATE concepts SET updated_at = datetime('now', '-60 days') WHERE id = ?",
            (a.id,),
        )
        conn.commit()
        stats = compact_project(conn, stale_days=30)
        assert stats.stale_removed == 1
        assert get_concept(conn, a.id) is None

    def test_keeps_stale_with_notes(self, conn):
        a = add_concept(conn, "noted-pkg", source="auto_scan", notes="keep me")
        conn.execute(
            "UPDATE concepts SET updated_at = datetime('now', '-60 days') WHERE id = ?",
            (a.id,),
        )
        conn.commit()
        stats = compact_project(conn, stale_days=30)
        assert stats.stale_removed == 0

    def test_keeps_manual_source(self, conn):
        a = add_concept(conn, "manual-pkg")
        conn.execute(
            "UPDATE concepts SET updated_at = datetime('now', '-60 days') WHERE id = ?",
            (a.id,),
        )
        conn.commit()
        stats = compact_project(conn, stale_days=30)
        assert stats.stale_removed == 0

    def test_keeps_concepts_with_edges(self, conn):
        a = add_concept(conn, "connected-pkg", source="auto_scan")
        b = add_concept(conn, "other")
        add_edge(conn, a.id, b.id, "uses")
        conn.execute(
            "UPDATE concepts SET updated_at = datetime('now', '-60 days') WHERE id = ?",
            (a.id,),
        )
        conn.commit()
        stats = compact_project(conn, stale_days=30)
        assert stats.stale_removed == 0
