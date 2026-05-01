from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept, get_journey


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _backdate(conn, concept_id: str, dt: datetime) -> None:
    conn.execute(
        "UPDATE concepts SET created_at = ? WHERE id = ?",
        (dt.strftime("%Y-%m-%d %H:%M:%S"), concept_id),
    )
    conn.commit()


class TestGetJourney:
    def test_concepts_from_different_weeks(self, conn):
        now = _utcnow()
        c1 = add_concept(conn, "fastapi", category="framework")
        _backdate(conn, c1.id, now - timedelta(days=14))

        c2 = add_concept(conn, "click", category="library")
        _backdate(conn, c2.id, now - timedelta(days=14))

        c3 = add_concept(conn, "playwright", category="devtool")
        _backdate(conn, c3.id, now)

        weeks = get_journey(conn)
        assert len(weeks) >= 2

        all_names = [
            c.name for w in weeks for c in w["concepts"]
        ]
        assert "fastapi" in all_names
        assert "click" in all_names
        assert "playwright" in all_names

        # Weeks are in chronological order
        starts = [w["week_start"] for w in weeks]
        assert starts == sorted(starts)

        # Each week dict has the right keys
        for w in weeks:
            assert "week" in w
            assert "week_start" in w
            assert "concepts" in w
            assert w["week"].count("-W") == 1

    def test_filtered_by_project(self, conn):
        proj = add_project(conn, "myapp", path="/tmp/myapp")
        add_concept(conn, "react", category="framework", project_id=proj.id)
        add_concept(conn, "vue", category="framework")

        weeks = get_journey(conn, project_id=proj.id)
        all_names = [c.name for w in weeks for c in w["concepts"]]
        assert "react" in all_names
        assert "vue" not in all_names

    def test_empty_journey(self, conn):
        weeks = get_journey(conn)
        assert weeks == []

    def test_respects_days_filter(self, conn):
        now = _utcnow()
        c1 = add_concept(conn, "old_tool", category="devtool")
        _backdate(conn, c1.id, now - timedelta(days=100))

        c2 = add_concept(conn, "new_tool", category="devtool")
        _backdate(conn, c2.id, now)

        weeks_90 = get_journey(conn, days=90)
        names_90 = [c.name for w in weeks_90 for c in w["concepts"]]
        assert "new_tool" in names_90
        assert "old_tool" not in names_90

        weeks_200 = get_journey(conn, days=200)
        names_200 = [c.name for w in weeks_200 for c in w["concepts"]]
        assert "new_tool" in names_200
        assert "old_tool" in names_200

    def test_concepts_ordered_within_week(self, conn):
        now = _utcnow()
        c1 = add_concept(conn, "first", category="library")
        _backdate(conn, c1.id, now - timedelta(hours=2))

        c2 = add_concept(conn, "second", category="library")
        _backdate(conn, c2.id, now)

        weeks = get_journey(conn)
        # Both should be in the same week, ordered by created_at
        for w in weeks:
            names = [c.name for c in w["concepts"]]
            if "first" in names and "second" in names:
                assert names.index("first") < names.index("second")
