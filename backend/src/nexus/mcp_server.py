from __future__ import annotations

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from nexus.cli_track import SOURCE_CATEGORIES, track_concept
from nexus.db import (
    get_connection,
    get_project_by_path,
    search_fts,
)
from nexus.db import (
    list_projects as db_list_projects,
)
from nexus.db_concepts import (
    add_concept as db_add_concept,
)
from nexus.db_concepts import (
    count_concepts,
    get_concept,
    get_edges,
)
from nexus.expertise import classify_expertise

VALID_SOURCES = frozenset(SOURCE_CATEGORIES.keys())

mcp = FastMCP(
    "nexus",
    instructions="Nexus personal knowledge graph. Search, query, and track concepts.",
)


def _concept_dict(c) -> dict:
    return {
        "name": c.name, "category": c.category, "summary": c.summary,
        "description": c.description, "doc_url": c.doc_url,
    }


@mcp.tool()
def search_concepts(query: str, project_id: str | None = None, limit: int = 10) -> list[dict]:
    """Search the knowledge graph by keyword."""
    conn = get_connection()
    try:
        results = search_fts(conn, query)
        if project_id:
            results = [c for c in results if c.project_id == project_id]
        return [_concept_dict(c) for c in results[:limit]]
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
        related_ids = {e.target_id for e in edges if e.source_id == c.id}
        related_ids |= {e.source_id for e in edges if e.target_id == c.id}
        related_ids.discard(c.id)
        name_map = {c.id: c.name}
        for rid in related_ids:
            rc = get_concept(conn, rid)
            if rc:
                name_map[rid] = rc.name
        return {
            **_concept_dict(c),
            "tags": c.tags, "quickstart": c.quickstart,
            "edges": [
                {"target": name_map.get(e.target_id, e.target_id), "relationship": e.relationship}
                for e in edges if e.source_id == c.id
            ] + [
                {"source": name_map.get(e.source_id, e.source_id), "relationship": e.relationship}
                for e in edges if e.target_id == c.id
            ],
        }
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
        pid = project_id
        if not pid and project_dir:
            p = get_project_by_path(conn, str(Path(project_dir).resolve()))
            if p:
                pid = p.id
        if not pid:
            return {"error": "provide project_id or project_dir"}
        return classify_expertise(conn, pid).to_dict()
    finally:
        conn.close()


@mcp.tool()
def onboard(project_id: str | None = None, project_dir: str | None = None) -> dict:
    """Get full onboarding context for a project — expertise + project metadata."""
    conn = get_connection()
    try:
        pid = project_id
        proj = None
        if not pid and project_dir:
            proj = get_project_by_path(conn, str(Path(project_dir).resolve()))
            if proj:
                pid = proj.id
        if not pid:
            return {"error": "provide project_id or project_dir"}
        if not proj:
            from nexus.db import get_project
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
        project_id = None
        if project_dir:
            p = get_project_by_path(conn, str(Path(project_dir).resolve()))
            if p:
                project_id = p.id
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


def run_server():
    mcp.run(transport="stdio")
