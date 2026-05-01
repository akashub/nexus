from __future__ import annotations

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from nexus.cli_track import SOURCE_CATEGORIES, track_concept
from nexus.db import get_connection, get_project_by_path, search_fts
from nexus.db import list_projects as db_list_projects
from nexus.db_concepts import (
    add_concept as db_add_concept,
)
from nexus.db_concepts import (
    count_concepts,
    get_concept,
    get_edges,
)
from nexus.db_concepts import (
    get_journey as db_get_journey,
)
from nexus.expertise import classify_expertise
from nexus.graph_helpers import build_concept_detail, concept_dict

VALID_SOURCES = frozenset(SOURCE_CATEGORIES.keys())

mcp = FastMCP(
    "nexus",
    instructions="Nexus personal knowledge graph. Search, query, and track concepts.",
)


def _resolve_pid(conn, project_id: str | None, project_dir: str | None) -> str | None:
    """Resolve a project ID from either an explicit ID or a directory path."""
    if project_id:
        return project_id
    if project_dir:
        p = get_project_by_path(conn, str(Path(project_dir).resolve()))
        if p:
            return p.id
    return None


@mcp.tool()
def search_concepts(query: str, project_id: str | None = None, limit: int = 10) -> list[dict]:
    """Search the knowledge graph by keyword."""
    conn = get_connection()
    try:
        results = search_fts(conn, query)
        if project_id:
            results = [c for c in results if c.project_id == project_id]
        return [concept_dict(c) for c in results[:limit]]
    finally:
        conn.close()


@mcp.tool()
def get_concept_detail(name: str) -> dict:
    """Get full detail for a concept including edges."""
    conn = get_connection()
    try:
        c = get_concept(conn, name)
        if not c:
            return {"error": f"not found: {name}"}
        edges = get_edges(conn, c.id)
        return build_concept_detail(conn, c, edges)
    finally:
        conn.close()


@mcp.tool()
def list_projects() -> list[dict]:
    """List all tracked projects with concept counts."""
    conn = get_connection()
    try:
        projects = db_list_projects(conn)
        result = []
        for p in projects:
            result.append({
                "name": p.name, "path": p.path,
                "concept_count": count_concepts(conn, project_id=p.id),
                "last_scanned_at": p.last_scanned_at,
            })
        return result
    finally:
        conn.close()


@mcp.tool()
def get_expertise(project_id: str | None = None, project_dir: str | None = None) -> dict:
    """Get expertise profile — what you know well, have seen, and are missing."""
    conn = get_connection()
    try:
        pid = _resolve_pid(conn, project_id, project_dir)
        if not pid:
            return {"error": "provide project_id or project_dir"}
        return classify_expertise(conn, pid).to_dict()
    finally:
        conn.close()


@mcp.tool()
def onboard(project_id: str | None = None, project_dir: str | None = None) -> dict:
    """Get full onboarding context for a project — expertise + project metadata."""
    from nexus.db import get_project
    conn = get_connection()
    try:
        pid = _resolve_pid(conn, project_id, project_dir)
        if not pid:
            return {"error": "provide project_id or project_dir"}
        proj = get_project(conn, pid)
        profile = classify_expertise(conn, pid)
        return {
            **profile.to_dict(),
            "project_path": proj.path if proj else None,
            "project_description": proj.description if proj else None,
        }
    finally:
        conn.close()


@mcp.tool()
def add_concept(name: str, project_dir: str | None = None, category: str | None = None) -> dict:
    """Add a concept to the knowledge graph."""
    conn = get_connection()
    try:
        existing = get_concept(conn, name)
        if existing:
            return {"status": "exists", "id": existing.id, "name": existing.name}
        project_id = _resolve_pid(conn, None, project_dir)
        try:
            c = db_add_concept(conn, name, category=category, project_id=project_id)
        except sqlite3.IntegrityError:
            c = get_concept(conn, name)
            if c:
                return {"status": "exists", "id": c.id, "name": c.name}
            return {"error": f"Failed to add concept: {name}"}
        return {"status": "added", "id": c.id, "name": c.name, "category": c.category}
    finally:
        conn.close()


@mcp.tool()
def track_install(name: str, source: str, project_dir: str, dev: bool = False) -> dict:
    """Record a package install in the knowledge graph."""
    conn = get_connection()
    try:
        return track_concept(conn, name, project_dir, source=source, dev=dev)
    finally:
        conn.close()


@mcp.tool()
def detect_gaps(project_id: str | None = None, project_dir: str | None = None) -> str:
    """Detect missing companion tools for a project's stack."""
    from nexus.db import get_project
    from nexus.gaps import detect_gaps as _detect_gaps
    from nexus.gaps import format_gaps_report
    conn = get_connection()
    try:
        pid = _resolve_pid(conn, project_id, project_dir)
        proj = get_project(conn, pid) if pid else None
        gaps = _detect_gaps(conn, project_id=pid)
        return format_gaps_report(proj.name if proj else None, gaps)
    finally:
        conn.close()


@mcp.tool()
def get_journey(
    project_dir: str | None = None, days: int = 90,
) -> str:
    """Show learning journey -- concepts grouped by week over time."""
    from nexus.graph_helpers import format_journey
    conn = get_connection()
    try:
        pid = _resolve_pid(conn, None, project_dir)
        weeks = db_get_journey(conn, project_id=pid, days=days)
        return format_journey(weeks)
    finally:
        conn.close()


def run_server():
    mcp.run(transport="stdio")
