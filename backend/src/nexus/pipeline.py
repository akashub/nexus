from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

from nexus.db_concepts import add_edge, list_concepts
from nexus.infer import llm_gap_fill, similarity_pass
from nexus.scanner import scan_project
from nexus.sync import sync_scan_results

log = logging.getLogger(__name__)


def rebuild_project_edges(
    conn: sqlite3.Connection, project_id: str, *,
    project_path: str | None = None,
    project_name: str | None = None,
    depth: int = 0,
    status_cb: Callable[[str], None] | None = None,
) -> dict:
    stats = {"structural": 0, "similarity": 0, "inferred": 0, "orphans": 0}

    if status_cb:
        status_cb("deleting old edges")
    _delete_non_manual_edges(conn, project_id)

    if project_path:
        if status_cb:
            status_cb("scanning project files")
        path = Path(project_path)
        if path.is_dir():
            result = scan_project(path, import_depth=depth)
            sync_stats = sync_scan_results(conn, project_path, result)
            stats["structural"] = sync_stats.get("edges_added", 0)

        if status_cb:
            status_cb("cross-referencing architecture")
        stats["structural"] += _claude_md_cross_ref(conn, project_id, path)

    if status_cb:
        status_cb("similarity pass")
    sim = similarity_pass(conn, project_id=project_id)
    stats["similarity"] = sim["created"]

    if status_cb:
        status_cb("LLM gap-fill")
    gap = llm_gap_fill(
        conn, project_id=project_id,
        project_name=project_name, project_path=project_path,
    )
    stats["inferred"] = gap["filled"]

    orphans = [
        c for c in list_concepts(conn, limit=500, project_id=project_id)
        if c.layer == "project" and not _has_edges(conn, c.id)
    ]
    stats["orphans"] = len(orphans)

    if status_cb:
        status_cb("done")
    return stats


def _delete_non_manual_edges(
    conn: sqlite3.Connection, project_id: str,
) -> int:
    concept_ids = conn.execute(
        "SELECT id FROM concepts WHERE project_id = ?", (project_id,),
    ).fetchall()
    if not concept_ids:
        return 0
    ids = [r["id"] for r in concept_ids]
    placeholders = ",".join("?" * len(ids))
    cur = conn.execute(
        f"DELETE FROM edges WHERE "
        f"(source_id IN ({placeholders}) OR target_id IN ({placeholders})) "
        f"AND confidence != 'manual'",
        ids + ids,
    )
    conn.commit()
    return cur.rowcount


_REL_HINTS = {
    "built on": "depends_on", "powered by": "depends_on",
    "wraps": "wraps", "calls": "uses", "uses": "uses",
    "runs": "uses", "via": "uses", "with": "uses",
}


def _claude_md_cross_ref(
    conn: sqlite3.Connection, project_id: str, project_path: Path,
) -> int:
    claude_md = project_path / "CLAUDE.md"
    if not claude_md.exists():
        return 0
    try:
        text = claude_md.read_text()
    except OSError:
        return 0

    concepts = list_concepts(conn, limit=500, project_id=project_id)
    by_lower = {c.name.lower(): c for c in concepts}
    existing = {
        (r["source_id"], r["target_id"])
        for r in conn.execute(
            "SELECT source_id, target_id FROM edges",
        ).fetchall()
    }
    created = 0
    text_lower = text.lower()

    for concept in concepts:
        if concept.source != "claude_md":
            continue
        ctx = concept.description or ""
        ctx_lower = ctx.lower()
        for other_name, other in by_lower.items():
            if other.id == concept.id or len(other_name) < 3:
                continue
            if other_name not in ctx_lower and not re.search(
                r'\b' + re.escape(other_name) + r'\b', text_lower,
            ):
                continue
            pair = (concept.id, other.id)
            rev = (other.id, concept.id)
            if pair in existing or rev in existing:
                continue
            rel = "uses"
            for kw, rel_type in _REL_HINTS.items():
                if kw in ctx_lower:
                    rel = rel_type
                    break
            try:
                add_edge(
                    conn, concept.id, other.id, rel,
                    description=f"CLAUDE.md: {ctx[:60]}",
                    confidence="structural",
                )
                existing.add(pair)
                created += 1
            except sqlite3.IntegrityError:
                pass
    return created


def _has_edges(conn: sqlite3.Connection, concept_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM edges WHERE source_id = ? OR target_id = ? LIMIT 1",
        (concept_id, concept_id),
    ).fetchone()
    return row is not None
