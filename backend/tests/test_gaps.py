"""Tests for gap detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept
from nexus.gaps import detect_gaps, format_gaps_report


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def test_react_without_testing_detects_gap(conn):
    """Project with react but no testing tool -> testing gap."""
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)

    gaps = detect_gaps(conn, project_id=p.id)
    categories = [g["category"] for g in gaps]
    assert "testing" in categories
    testing_gap = next(g for g in gaps if g["category"] == "testing")
    assert "react" in testing_gap["have"]
    assert "vitest" in testing_gap["suggestions"]


def test_react_with_vitest_no_testing_gap(conn):
    """Project with react + vitest -> no testing gap."""
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    add_concept(conn, "vitest", category="devtool", project_id=p.id)

    gaps = detect_gaps(conn, project_id=p.id)
    categories = [g["category"] for g in gaps]
    assert "testing" not in categories


def test_no_signals_no_gaps(conn):
    """Project with no framework signals -> no gaps."""
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "markdown", category="concept", project_id=p.id)

    gaps = detect_gaps(conn, project_id=p.id)
    assert gaps == []


def test_multiple_gaps_detected(conn):
    """Project with react only -> multiple gaps (testing, linting, styling, state)."""
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)

    gaps = detect_gaps(conn, project_id=p.id)
    categories = {g["category"] for g in gaps}
    assert len(gaps) >= 3
    assert "testing" in categories
    assert "linting" in categories
    assert "styling" in categories


def test_scoped_package_normalization(conn):
    """@scope/package names are normalized to match companions."""
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    add_concept(conn, "@tanstack/react-query", category="framework", project_id=p.id)

    gaps = detect_gaps(conn, project_id=p.id)
    # tanstack-query is a companion for state_management but the concept is
    # @tanstack/react-query which normalizes to react-query, not tanstack-query.
    # So state_management gap should still be present.
    categories = {g["category"] for g in gaps}
    assert "state_management" in categories


def test_empty_project_no_gaps(conn):
    """Project with no concepts -> no gaps."""
    p = add_project(conn, "empty", path="/tmp/empty")
    gaps = detect_gaps(conn, project_id=p.id)
    assert gaps == []


def test_format_gaps_report_no_gaps():
    """Formatting with no gaps returns well-rounded message."""
    result = format_gaps_report("myapp", [])
    assert "well-rounded" in result


def test_format_gaps_report_with_gaps():
    """Formatting with gaps shows structured output."""
    gaps = [{
        "category": "testing",
        "reason": "Projects with frameworks typically need testing tools",
        "have": ["react"],
        "missing_type": "test runner",
        "suggestions": ["vitest", "jest", "pytest"],
    }]
    result = format_gaps_report("myapp", gaps)
    assert "Gaps detected for myapp:" in result
    assert "You have: react" in result
    assert "test runner" in result
    assert "1 gap detected" in result
