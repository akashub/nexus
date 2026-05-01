from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from nexus.ai import cosine_similarity
from nexus.db_concepts import (
    delete_concept,
    delete_edge,
    get_edges,
    list_concepts,
    update_concept,
)


@dataclass
class CompactStats:
    merged: int = 0
    stale_removed: int = 0
    edges_deduped: int = 0
    reembedded: int = 0
    errors: list[str] = field(default_factory=list)


def compact_project(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    *,
    stale_days: int = 30,
    similarity_threshold: float = 0.92,
    dry_run: bool = False,
) -> CompactStats:
    stats = CompactStats()
    kw = {"limit": 10000}
    if project_id:
        kw["project_id"] = project_id
    concepts = list_concepts(conn, **kw)

    _dedup_edges(conn, concepts, stats, dry_run)
    _merge_similar(conn, concepts, similarity_threshold, stats, dry_run)
    _remove_stale(conn, concepts, stale_days, stats, dry_run)

    return stats


def _dedup_edges(conn, concepts, stats: CompactStats, dry_run: bool) -> None:
    for c in concepts:
        edges = get_edges(conn, c.id)
        seen: dict[tuple, str] = {}
        for e in edges:
            key = (e.source_id, e.target_id, e.relationship)
            if key in seen:
                stats.edges_deduped += 1
                if not dry_run:
                    delete_edge(conn, e.id)
            else:
                seen[key] = e.id


def _merge_similar(
    conn, concepts, threshold: float, stats: CompactStats, dry_run: bool,
) -> None:
    merged_ids: set[str] = set()
    embedded = [(c, c.embedding) for c in concepts if c.embedding]

    for i, (a, a_emb) in enumerate(embedded):
        if a.id in merged_ids:
            continue
        for b, b_emb in embedded[i + 1:]:
            if b.id in merged_ids:
                continue
            sim = 1.0 if a.name.lower() == b.name.lower() else cosine_similarity(a_emb, b_emb)
            if sim < threshold:
                continue
            if not _names_similar(a.name, b.name):
                continue
            stats.merged += 1
            merged_ids.add(b.id)
            if dry_run:
                continue
            _do_merge(conn, keep=a, remove=b)


def _names_similar(a: str, b: str) -> bool:
    a_norm = a.lower().replace("-", "").replace("_", "").replace(".", "")
    b_norm = b.lower().replace("-", "").replace("_", "").replace(".", "")
    return a_norm == b_norm or a_norm.startswith(b_norm) or b_norm.startswith(a_norm)


def _do_merge(conn, *, keep, remove) -> None:
    if not keep.description and remove.description:
        update_concept(conn, keep.id, description=remove.description)
    if not keep.notes and remove.notes:
        update_concept(conn, keep.id, notes=remove.notes)
    if not keep.embedding and remove.embedding:
        update_concept(conn, keep.id, embedding=remove.embedding)

    for e in get_edges(conn, remove.id):
        new_src = keep.id if e.source_id == remove.id else e.source_id
        new_tgt = keep.id if e.target_id == remove.id else e.target_id
        if new_src == new_tgt:
            delete_edge(conn, e.id)
            continue
        try:
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relationship, description, weight) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (e.id + "_m", new_src, new_tgt, e.relationship, e.description, e.weight),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        delete_edge(conn, e.id)

    delete_concept(conn, remove.id)


def _remove_stale(conn, concepts, stale_days: int, stats: CompactStats, dry_run: bool) -> None:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=stale_days)
    for c in concepts:
        if c.source != "auto_scan":
            continue
        if c.notes or c.description:
            continue
        if not c.updated_at:
            continue
        try:
            updated = datetime.fromisoformat(c.updated_at)
        except ValueError:
            continue
        if updated > cutoff:
            continue
        if get_edges(conn, c.id):
            continue
        stats.stale_removed += 1
        if not dry_run:
            delete_concept(conn, c.id)
