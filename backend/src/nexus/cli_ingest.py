from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import click

from nexus.db import add_project, get_connection, get_project_by_path
from nexus.db_concepts import add_concept, add_edge, get_concept, update_concept

_VALID_REL_TYPES = frozenset({
    "uses", "depends_on", "similar_to", "part_of", "tested_with",
    "configured_by", "builds_into", "wraps", "serves", "deployed_via",
    "replaces", "related_to", "sends_data_to", "triggers",
})


@click.command("ingest")
@click.argument("ledger_path", type=click.Path(exists=True))
@click.option("--quiet", "-q", is_flag=True)
def ingest_cmd(ledger_path: str, quiet: bool) -> None:
    """Ingest a knowledge ledger (JSONL) into the graph."""
    path = Path(ledger_path)
    conn = get_connection()
    added = edges_created = errors = 0
    deferred_rels: list[tuple[str, dict]] = []
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    _process_entry(conn, entry)
                    added += 1
                    for rel in entry.get("relationships", []):
                        deferred_rels.append((entry["name"], rel))
                except (json.JSONDecodeError, KeyError):
                    errors += 1
        edges_created = _process_relationships(conn, deferred_rels)
    finally:
        conn.close()

    if not quiet:
        parts = [f"{added} concepts"]
        if edges_created:
            parts.append(f"{edges_created} edges")
        if errors:
            parts.append(f"{errors} errors")
        click.echo(f"Ingested: {', '.join(parts)}")

    if errors == 0:
        path.unlink(missing_ok=True)


def _process_entry(conn, entry: dict) -> None:
    name = entry["name"]
    project_dir = entry.get("project_dir")

    project_id = None
    if project_dir:
        p = get_project_by_path(conn, project_dir)
        if p:
            project_id = p.id
        else:
            proj_name = Path(project_dir).name
            project_id = add_project(conn, proj_name, path=project_dir).id

    existing = get_concept(conn, name)
    if existing:
        updates = {}
        if entry.get("description") and not existing.description:
            updates["description"] = entry["description"]
        if entry.get("summary") and not existing.summary:
            updates["summary"] = entry["summary"]
        if entry.get("category") and not existing.category:
            updates["category"] = entry["category"]
        ctx = entry.get("context")
        if ctx:
            current = existing.notes or ""
            if ctx not in current:
                updates["notes"] = f"{current}\n{ctx}".strip()
        if updates:
            update_concept(conn, existing.id, **updates)
        return

    add_concept(
        conn, name,
        description=entry.get("description"),
        summary=entry.get("summary"),
        category=entry.get("category"),
        notes=entry.get("context"),
        source="ledger",
        project_id=project_id,
    )


def _process_relationships(
    conn, rels: list[tuple[str, dict]],
) -> int:
    created = 0
    for source_name, rel in rels:
        target_name = rel.get("target")
        rel_type = rel.get("type", "related_to")
        if not target_name or rel_type not in _VALID_REL_TYPES:
            continue
        source = get_concept(conn, source_name)
        target = get_concept(conn, target_name)
        if not source or not target:
            continue
        try:
            add_edge(conn, source.id, target.id, rel_type)
            created += 1
        except sqlite3.IntegrityError:
            pass
    return created
