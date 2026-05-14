from __future__ import annotations

import sqlite3

import click

from nexus.ai import cosine_similarity
from nexus.db_concepts import add_edge, list_concepts

_SIM_THRESHOLD = 0.80


def similarity_pass(
    conn: sqlite3.Connection, *, project_id: str | None = None,
) -> dict:
    concepts = list_concepts(conn, limit=500, project_id=project_id)
    with_embed = [c for c in concepts if c.embedding and c.category]
    existing = _load_existing_edges(conn)
    stats = {"created": 0, "skipped": 0}

    for i, a in enumerate(with_embed):
        for b in with_embed[i + 1:]:
            if a.category != b.category:
                continue
            if (
                "/" in a.name and "/" in b.name
                and a.name.rsplit("/", 1)[0] == b.name.rsplit("/", 1)[0]
            ):
                continue
            sim = cosine_similarity(a.embedding, b.embedding)
            if sim < _SIM_THRESHOLD:
                continue
            pk = _pair_key(a.id, b.id)
            if pk in existing:
                stats["skipped"] += 1
                continue
            try:
                add_edge(
                    conn, a.id, b.id, "similar_to",
                    description=f"similar ({sim:.2f})",
                    weight=round(sim, 3), confidence="similarity",
                )
                existing.add(pk)
                stats["created"] += 1
            except sqlite3.IntegrityError:
                stats["skipped"] += 1
    return stats


def llm_gap_fill(
    conn: sqlite3.Connection, *,
    project_id: str | None = None,
    project_name: str | None = None,
    project_path: str | None = None,
) -> dict:
    # Disabled: LLM gap-fill produced unreliable edges by asking leading
    # questions that the model never answered with []. Similarity pass is
    # the only reliable automated edge source.
    return {"filled": 0, "skipped": 0, "errors": 0}


def _load_existing_edges(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    rows = conn.execute("SELECT source_id, target_id FROM edges").fetchall()
    return {_pair_key(r["source_id"], r["target_id"]) for r in rows}


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (min(a, b), max(a, b))


def infer_relationships(
    conn: sqlite3.Connection, *, project_id: str | None = None,
    project_name: str | None = None, project_path: str | None = None,
    verbose: bool = False,
) -> dict:
    sim = similarity_pass(conn, project_id=project_id)
    gap = llm_gap_fill(
        conn, project_id=project_id,
        project_name=project_name, project_path=project_path,
    )
    if verbose:
        click.echo(f"  similarity: {sim['created']}, gap-fill: {gap['filled']}")
    return {"similarity": sim["created"], "inferred": gap["filled"],
            "skipped": sim["skipped"] + gap["skipped"], "errors": gap.get("errors", 0)}
