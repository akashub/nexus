from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import click

from nexus.db import (
    add_concept,
    add_edge,
    add_project,
    get_concept,
    get_concept_by_name_and_project,
    get_project_by_path,
    update_project,
)
from nexus.models import Project
from nexus.scanners import ScanResult


def sync_scan_results(
    conn: sqlite3.Connection,
    project_path: str,
    result: ScanResult,
    *,
    verbose: bool = False,
    enrich: bool = False,
) -> dict:
    project = _ensure_project(conn, project_path, result.project_description)
    stats = {"added": 0, "skipped": 0, "edges_added": 0}

    for sc in result.concepts:
        setup = [sc.setup_command] if sc.setup_command else []
        existing = get_concept_by_name_and_project(conn, sc.name, project.id)
        if existing:
            if setup and not existing.setup_commands:
                from nexus.db import update_concept
                update_concept(conn, existing.id, setup_commands=setup)
            stats["skipped"] += 1
            continue
        global_existing = get_concept(conn, sc.name)
        if global_existing and not global_existing.project_id:
            from nexus.db import update_concept
            update_concept(
                conn, global_existing.id, project_id=project.id,
                **({"setup_commands": setup} if setup else {}),
            )
            stats["skipped"] += 1
            if verbose:
                click.echo(f"  claimed: {sc.name}")
            continue

        c = add_concept(
            conn, sc.name, category=sc.category_hint,
            source=sc.source, project_id=project.id,
        )
        if setup:
            from nexus.db import update_concept
            update_concept(conn, c.id, setup_commands=setup)
        stats["added"] += 1
        if verbose:
            click.echo(f"  + {sc.name} ({sc.source})")

        if enrich:
            from nexus.enrich import enrich_concept
            enrich_concept(conn, c.id)

    _sync_relationships(conn, project.id, result, stats, verbose)

    update_project(
        conn, project.id,
        last_scanned_at=datetime.now(UTC).isoformat(),
    )
    return stats


def _ensure_project(
    conn: sqlite3.Connection, project_path: str, description: str | None,
) -> Project:
    path = str(Path(project_path).resolve())
    project = get_project_by_path(conn, path)
    if project:
        return project
    name = Path(path).name
    return add_project(conn, name, path=path, description=description)


def _sync_relationships(
    conn: sqlite3.Connection,
    project_id: str,
    result: ScanResult,
    stats: dict,
    verbose: bool,
) -> None:
    for rel in result.relationships:
        src = get_concept_by_name_and_project(
            conn, rel.source_name, project_id,
        )
        tgt = get_concept_by_name_and_project(
            conn, rel.target_name, project_id,
        )
        if not src or not tgt:
            continue
        try:
            add_edge(
                conn, src.id, tgt.id, rel.relationship,
                description=rel.reason,
            )
            stats["edges_added"] += 1
            if verbose:
                click.echo(
                    f"  ~ {rel.source_name} --[{rel.relationship}]--> "
                    f"{rel.target_name}"
                )
        except sqlite3.IntegrityError:
            pass
