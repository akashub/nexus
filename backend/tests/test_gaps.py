"""Tests for gap detection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus.db import add_project, get_connection, init_db
from nexus.db_concepts import add_concept
from nexus.gaps import _detect_gaps_patterns, detect_gaps, format_gaps_report


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_connection(db_path)
    yield c
    c.close()


def _no_ai(conn, **kw):
    """Run gap detection with AI disabled — tests the pattern fallback."""
    with patch("nexus.ai.is_available", return_value=False):
        return detect_gaps(conn, **kw)


def test_react_without_testing_detects_gap(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    categories = [g["category"] for g in gaps]
    assert "testing" in categories
    testing_gap = next(g for g in gaps if g["category"] == "testing")
    assert "react" in testing_gap["have"]
    assert "vitest" in testing_gap["suggestions"]


def test_react_with_vitest_no_testing_gap(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    add_concept(conn, "vitest", category="devtool", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    categories = [g["category"] for g in gaps]
    assert "testing" not in categories


def test_no_signals_no_gaps(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "markdown", category="concept", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    assert gaps == []


def test_multiple_gaps_detected(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    categories = {g["category"] for g in gaps}
    assert len(gaps) >= 3
    assert "testing" in categories
    assert "linting" in categories
    assert "styling" in categories


def test_scoped_package_normalization(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    add_concept(conn, "@tanstack/react-query", category="framework", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    categories = {g["category"] for g in gaps}
    assert "testing" in categories


def test_empty_project_no_gaps(conn):
    p = add_project(conn, "empty", path="/tmp/empty")
    gaps = _no_ai(conn, project_id=p.id)
    assert gaps == []


def test_suffix_match_drizzle_orm(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "fastapi", category="framework", project_id=p.id)
    add_concept(conn, "drizzle-orm", category="devtool", project_id=p.id)

    gaps = _no_ai(conn, project_id=p.id)
    categories = [g["category"] for g in gaps]
    assert "database" not in categories


def test_pattern_fallback_directly(conn):
    """_detect_gaps_patterns works standalone."""
    from nexus.db_concepts import list_concepts
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    concepts = list_concepts(conn, project_id=p.id)
    gaps = _detect_gaps_patterns(concepts)
    assert any(g["category"] == "testing" for g in gaps)


def test_ai_gap_detection(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)
    add_concept(conn, "typescript", category="language", project_id=p.id)

    ai_response = json.dumps([{
        "category": "deployment",
        "reason": "No deployment tool detected",
        "have": ["react"],
        "missing_type": "deployment platform",
        "suggestions": ["vercel", "netlify"],
    }])

    with (
        patch("nexus.ai.is_available", return_value=True),
        patch("nexus.ai.smart_generate", return_value=ai_response),
    ):
        gaps = detect_gaps(conn, project_id=p.id)

    assert len(gaps) == 1
    assert gaps[0]["category"] == "deployment"
    assert "vercel" in gaps[0]["suggestions"]


def test_ai_fallback_on_failure(conn):
    p = add_project(conn, "myapp", path="/tmp/myapp")
    add_concept(conn, "react", category="framework", project_id=p.id)

    with (
        patch("nexus.ai.is_available", return_value=True),
        patch("nexus.ai.smart_generate", side_effect=Exception("timeout")),
    ):
        gaps = detect_gaps(conn, project_id=p.id)

    categories = [g["category"] for g in gaps]
    assert "testing" in categories


def test_format_gaps_report_no_gaps():
    result = format_gaps_report("myapp", [])
    assert "well-rounded" in result


def test_format_gaps_report_with_gaps():
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
