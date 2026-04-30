from __future__ import annotations

import json
import sqlite3
from itertools import combinations

import click

from nexus.ai import cosine_similarity, generate, is_available
from nexus.db_concepts import add_edge, list_concepts
from nexus.models import RELATIONSHIP_TYPES

_SIM_THRESHOLD = 0.55
_TOP_K = 3
_VALID_TYPES = sorted(RELATIONSHIP_TYPES)

_SYSTEM = (
    "You label relationships between software concepts in a project. "
    'Reply with ONLY a JSON object: {"relationship": "<type>", '
    '"reason": "<one sentence about how they relate IN THIS PROJECT>"}. '
    f"Valid types: {', '.join(_VALID_TYPES)}. "
    "Pick the most specific type. If none fit, use related_to."
)


def infer_relationships(
    conn: sqlite3.Connection,
    *,
    project_id: str | None = None,
    project_name: str | None = None,
    project_path: str | None = None,
    verbose: bool = False,
) -> dict:
    if not is_available():
        click.echo("ollama not available — skipping relationship inference")
        return {"inferred": 0, "skipped": 0, "errors": 0}

    concepts = list_concepts(conn, limit=500, project_id=project_id)
    with_embed = [c for c in concepts if c.embedding]
    if len(with_embed) < 2:
        click.echo("need at least 2 concepts with embeddings")
        return {"inferred": 0, "skipped": 0, "errors": 0}

    overview = _get_project_overview(project_name)
    existing = _load_existing_edges(conn)
    candidates = _find_candidates(with_embed)
    stats = {"inferred": 0, "skipped": 0, "errors": 0}

    for a, b, sim in candidates:
        pair_key = _pair_key(a.id, b.id)
        if pair_key in existing:
            stats["skipped"] += 1
            continue
        ctx = _gather_context(project_name, project_path, a.name, b.name)
        rel = _label_pair(a, b, overview, ctx)
        if not rel:
            stats["errors"] += 1
            continue
        try:
            add_edge(
                conn, a.id, b.id, rel["relationship"],
                description=rel.get("reason"), weight=round(sim, 3),
            )
            existing.add(pair_key)
            stats["inferred"] += 1
            if verbose:
                click.echo(
                    f"  ~ {a.name} --[{rel['relationship']}]--> "
                    f"{b.name} ({sim:.2f})",
                )
        except sqlite3.IntegrityError:
            stats["skipped"] += 1
    return stats


def _get_project_overview(name: str | None) -> str:
    if not name:
        return ""
    try:
        from nexus.context import get_eagle_overview
        return get_eagle_overview(name) or ""
    except Exception:
        return ""


def _gather_context(
    project_name: str | None, project_path: str | None,
    name_a: str, name_b: str,
) -> str:
    if not project_name:
        return ""
    try:
        from nexus.context import get_concept_context
        path = project_path or ""
        ctx_a = get_concept_context(project_name, path, name_a)
        ctx_b = get_concept_context(project_name, path, name_b)
        parts = []
        if ctx_a:
            parts.append(f"Context for {name_a}:\n{ctx_a[:300]}")
        if ctx_b:
            parts.append(f"Context for {name_b}:\n{ctx_b[:300]}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def _load_existing_edges(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    rows = conn.execute("SELECT source_id, target_id FROM edges").fetchall()
    pairs: set[tuple[str, str]] = set()
    for r in rows:
        pairs.add(_pair_key(r["source_id"], r["target_id"]))
    return pairs


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (min(a, b), max(a, b))


def _find_candidates(concepts: list) -> list[tuple]:
    scored: dict[str, list[tuple]] = {c.id: [] for c in concepts}
    for a, b in combinations(concepts, 2):
        sim = cosine_similarity(a.embedding, b.embedding)
        if sim >= _SIM_THRESHOLD:
            scored[a.id].append((a, b, sim))
            scored[b.id].append((b, a, sim))
    seen: set[tuple[str, str]] = set()
    result: list[tuple] = []
    for cid in scored:
        top = sorted(scored[cid], key=lambda x: x[2], reverse=True)[:_TOP_K]
        for a, b, sim in top:
            pk = _pair_key(a.id, b.id)
            if pk not in seen:
                seen.add(pk)
                result.append((a, b, sim))
    return sorted(result, key=lambda x: x[2], reverse=True)


def _label_pair(a, b, overview: str, context: str) -> dict | None:
    prompt = f"Concept A: {a.name}"
    if a.description:
        prompt += f" — {a.description[:200]}"
    prompt += f"\nConcept B: {b.name}"
    if b.description:
        prompt += f" — {b.description[:200]}"
    if overview:
        prompt += f"\n\nProject context:\n{overview[:400]}"
    if context:
        prompt += f"\n\nUsage context:\n{context[:400]}"
    prompt += "\n\nWhat is the relationship from A to B in this project?"
    try:
        raw = generate(prompt, system=_SYSTEM)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start:end])
        rel = data.get("relationship", "related_to")
        if rel not in RELATIONSHIP_TYPES:
            rel = "related_to"
        return {"relationship": rel, "reason": data.get("reason")}
    except (json.JSONDecodeError, Exception):
        return None
