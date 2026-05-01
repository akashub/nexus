from __future__ import annotations

import click

from nexus.compact import compact_project
from nexus.db import get_connection, get_project, list_projects


@click.command("compact")
@click.argument("project", required=False)
@click.option("--all", "all_projects", is_flag=True, help="Compact all projects.")
@click.option("--stale-days", default=30, help="Remove stale concepts older than N days.")
@click.option("--dry-run", is_flag=True, help="Preview without making changes.")
@click.option("--verbose", "-v", is_flag=True)
def compact_cmd(
    project: str | None, all_projects: bool, stale_days: int, dry_run: bool, verbose: bool,
) -> None:
    """Compact a project graph — merge duplicates, remove stale entries."""
    conn = get_connection()
    try:
        projects = _resolve_projects(conn, project, all_projects)
        if not projects:
            raise click.ClickException("No projects found. Provide a name or use --all.")

        for p in projects:
            if verbose:
                click.echo(f"Compacting: {p.name}")
            stats = compact_project(conn, p.id, stale_days=stale_days, dry_run=dry_run)
            prefix = "[dry run] " if dry_run else ""
            click.echo(
                f"  {prefix}{p.name}: "
                f"{stats.merged} merged, {stats.stale_removed} stale removed, "
                f"{stats.edges_deduped} edges deduped"
            )
    finally:
        conn.close()


def _resolve_projects(conn, name: str | None, all_flag: bool):
    if all_flag:
        return list_projects(conn)
    if not name:
        projects = list_projects(conn)
        if len(projects) == 1:
            return projects
        return []
    p = get_project(conn, name)
    return [p] if p else []
