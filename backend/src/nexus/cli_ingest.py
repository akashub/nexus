from __future__ import annotations

import json
from pathlib import Path

import click

from nexus.db import add_project, get_connection, get_project_by_path
from nexus.db_concepts import add_concept, get_concept, update_concept


@click.command("ingest")
@click.argument("ledger_path", type=click.Path(exists=True))
@click.option("--quiet", "-q", is_flag=True)
def ingest_cmd(ledger_path: str, quiet: bool) -> None:
    """Ingest a knowledge ledger (JSONL) into the graph."""
    path = Path(ledger_path)
    conn = get_connection()
    added = errors = 0
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                _process_entry(conn, entry)
                added += 1
            except (json.JSONDecodeError, KeyError):
                errors += 1
    finally:
        conn.close()

    if not quiet:
        click.echo(f"Ingested: {added} entries, {errors} errors")

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
        if entry.get("category") and not existing.category:
            updates["category"] = entry["category"]
        if entry.get("notes"):
            current = existing.notes or ""
            new_note = entry["notes"]
            if new_note not in current:
                updates["notes"] = f"{current}\n{new_note}".strip()
        if updates:
            update_concept(conn, existing.id, **updates)
        return

    add_concept(
        conn, name,
        category=entry.get("category"),
        source="ledger",
        project_id=project_id,
    )
