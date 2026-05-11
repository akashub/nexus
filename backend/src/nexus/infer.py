from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import click

from nexus.ai import cosine_similarity, generate, is_available
from nexus.db_concepts import add_edge, get_edges, list_concepts
from nexus.models import RELATIONSHIP_TYPES

_SIM_THRESHOLD = 0.7
_VALID_TYPES = sorted(RELATIONSHIP_TYPES)


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
    if not is_available():
        return {"filled": 0, "skipped": 0, "errors": 0}

    concepts = list_concepts(conn, limit=500, project_id=project_id)
    project_layer = [c for c in concepts if c.layer == "project"]

    orphans, connected = [], []
    for c in project_layer:
        (connected if get_edges(conn, c.id) else orphans).append(c)
    connected_names = [c.name for c in connected]

    if not orphans or not connected_names:
        return {"filled": 0, "skipped": 0, "errors": 0}

    overview = _get_project_overview(project_name)
    claude_md = _read_claude_md(project_path)
    skeleton = ", ".join(connected_names[:50])
    stats = {"filled": 0, "skipped": 0, "errors": 0}
    existing = _load_existing_edges(conn)
    concept_map = {c.name.lower(): c for c in project_layer}

    for orphan in orphans:
        rels = _fill_orphan(orphan, skeleton, overview, claude_md, connected_names)
        if not rels:
            stats["skipped"] += 1
            continue
        for rel in rels:
            target_name = rel.get("target", "").lower()
            target = concept_map.get(target_name)
            if not target or target.id == orphan.id:
                continue
            pk = _pair_key(orphan.id, target.id)
            if pk in existing:
                continue
            rel_type = rel.get("relationship", "related_to")
            if rel_type not in RELATIONSHIP_TYPES:
                rel_type = "related_to"
            try:
                add_edge(
                    conn, orphan.id, target.id, rel_type,
                    description=rel.get("reason"),
                    confidence="inferred",
                )
                existing.add(pk)
                stats["filled"] += 1
            except sqlite3.IntegrityError:
                pass
    return stats


_GAP_SYSTEM = (
    "You connect orphaned software concepts to a project's dependency graph. "
    "Reply ONLY with a JSON array of objects: "
    '[{"target": "<existing concept name>", "relationship": "<type>", '
    '"reason": "<one sentence>"}]. '
    f"Valid types: {', '.join(_VALID_TYPES)}. "
    "Return [] if no confident connection exists. Max 3 connections."
)


def _fill_orphan(
    orphan, skeleton: str, overview: str, claude_md: str,
    connected: list[str],
) -> list[dict]:
    prompt = f"Orphan concept: {orphan.name}"
    if orphan.description:
        prompt += f"\nDescription: {orphan.description[:200]}"
    prompt += f"\n\nConnected concepts in this project:\n{skeleton}"
    if overview:
        prompt += f"\n\nProject overview:\n{overview[:500]}"
    if claude_md:
        prompt += f"\n\nProject CLAUDE.md:\n{claude_md[:800]}"
    prompt += (
        f"\n\nWhich of the connected concepts does '{orphan.name}' "
        "relate to, and how?"
    )
    try:
        raw = generate(prompt, system=_GAP_SYSTEM)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start < 0 or end <= start:
            return []
        data = json.loads(raw[start:end])
        if not isinstance(data, list):
            return []
        valid = [
            r for r in data
            if isinstance(r, dict) and r.get("target", "").lower()
            in {n.lower() for n in connected}
        ]
        return valid[:3]
    except Exception:
        return []


def _get_project_overview(name: str | None) -> str:
    if not name:
        return ""
    try:
        from nexus.context import get_eagle_overview
        return get_eagle_overview(name) or ""
    except Exception:
        return ""


def _read_claude_md(project_path: str | None) -> str:
    if not project_path:
        return ""
    p = Path(project_path) / "CLAUDE.md"
    if p.exists():
        try:
            return p.read_text()[:2000]
        except OSError:
            pass
    return ""


def _load_existing_edges(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    rows = conn.execute("SELECT source_id, target_id FROM edges LIMIT 10000").fetchall()
    pairs: set[tuple[str, str]] = set()
    for r in rows:
        pairs.add(_pair_key(r["source_id"], r["target_id"]))
    return pairs


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
