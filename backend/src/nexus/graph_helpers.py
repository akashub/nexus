from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime

from nexus.db import list_concepts
from nexus.db_concepts import add_edge, get_concept
from nexus.models import RELATIONSHIP_TYPES, Concept, Project


def compute_project_edges(
    conn: sqlite3.Connection, projects: list[Project],
) -> list[dict]:
    """Find shared-dependency edges between projects."""
    concept_projects: dict[str, set[str]] = defaultdict(set)
    for p in projects:
        for c in list_concepts(conn, project_id=p.id, limit=10000):
            concept_projects[c.name.lower()].add(p.id)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for _name, pids in concept_projects.items():
        pids_list = sorted(pids)
        for i, a in enumerate(pids_list):
            for b in pids_list[i + 1:]:
                pair_counts[(a, b)] += 1
    return [
        {"source_id": a, "target_id": b, "weight": count, "relationship": "shared_deps"}
        for (a, b), count in pair_counts.items() if count >= 2
    ]


def concept_dict(c: Concept) -> dict:
    """Convert a Concept to a summary dict for MCP responses."""
    return {
        "name": c.name, "category": c.category, "summary": c.summary,
        "description": c.description, "doc_url": c.doc_url,
    }


def build_concept_detail(conn: sqlite3.Connection, c: Concept, edges: list) -> dict:
    """Build a full concept detail dict with resolved edge names."""
    related_ids = {e.target_id for e in edges if e.source_id == c.id}
    related_ids |= {e.source_id for e in edges if e.target_id == c.id}
    related_ids.discard(c.id)
    name_map = {c.id: c.name}
    for rid in related_ids:
        rc = get_concept(conn, rid)
        if rc:
            name_map[rid] = rc.name
    return {
        **concept_dict(c),
        "tags": c.tags, "quickstart": c.quickstart,
        "edges": [
            {"target": name_map.get(e.target_id, e.target_id), "relationship": e.relationship}
            for e in edges if e.source_id == c.id
        ] + [
            {"source": name_map.get(e.source_id, e.source_id), "relationship": e.relationship}
            for e in edges if e.target_id == c.id
        ],
    }


def format_journey(weeks: list[dict]) -> str:
    """Format learning journey weeks as a tree-style text report."""
    if not weeks:
        return "No concepts found in this time range."
    lines: list[str] = []
    total = 0
    for w in weeks:
        dt = datetime.fromisoformat(w["week_start"])
        lines.append(f"\nWeek of {dt.strftime('%b %-d')}")
        concepts = w["concepts"]
        total += len(concepts)
        for i, c in enumerate(concepts):
            is_last = i == len(concepts) - 1
            prefix = "  └── " if is_last else "  ├── "
            cat = f" [{c.category}]" if c.category else ""
            desc = ""
            if c.summary:
                desc = f" — {c.summary[:60]}"
            elif c.description:
                desc = f" — {c.description[:60]}"
            lines.append(f"{prefix}{c.name}{cat}{desc}")
    lines.append(f"\n{len(weeks)} week(s) · {total} concept(s)")
    return "\n".join(lines)


def merge_concept_fields(
    existing: Concept, description, summary, category, quickstart, notes,
    overwrite: bool = False, doc_url=None,
):
    updates = {}
    if description and (overwrite or not existing.description):
        updates["description"] = description
    if summary and (overwrite or not existing.summary):
        updates["summary"] = summary
    if category and (overwrite or not existing.category):
        updates["category"] = category
    if quickstart and (overwrite or not existing.quickstart):
        updates["quickstart"] = quickstart
    if doc_url and (overwrite or not existing.doc_url):
        updates["doc_url"] = doc_url
    if notes:
        current = existing.notes or ""
        if notes not in current:
            updates["notes"] = f"{current}\n{notes}".strip()
    return updates


def create_concept_edges(conn: sqlite3.Connection, concept_id: str, relationships: list[dict]):
    if not relationships:
        return 0
    created = 0
    for rel in relationships:
        target_name = rel.get("target")
        rel_type = rel.get("type", "related_to")
        if not target_name or rel_type not in RELATIONSHIP_TYPES:
            continue
        target = get_concept(conn, target_name)
        if not target:
            continue
        try:
            add_edge(conn, concept_id, target.id, rel_type)
            created += 1
        except sqlite3.IntegrityError:
            pass
    return created
