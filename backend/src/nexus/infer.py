from __future__ import annotations

import sqlite3

import click


def infer_relationships(
    conn: sqlite3.Connection, *, project_id: str | None = None,
    project_name: str | None = None, project_path: str | None = None,
    verbose: bool = False,
) -> dict:
    from nexus.pipeline import rebuild_project_edges
    stats = rebuild_project_edges(
        conn, project_id,
        project_path=project_path, project_name=project_name,
    )
    if verbose:
        click.echo(f"  structural: {stats['structural']}, orphans: {stats['orphans']}")
    return {
        "similarity": 0, "inferred": stats["structural"],
        "skipped": 0, "errors": 0,
    }
