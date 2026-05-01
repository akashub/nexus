from __future__ import annotations

import click

from nexus.db import get_connection, get_project
from nexus.gaps import detect_gaps, format_gaps_report


@click.command("gaps")
@click.option("--project", "-p", default=None, help="Project ID or name.")
def gaps_cmd(project: str | None) -> None:
    """Detect missing companion tools for a project."""
    conn = get_connection()
    try:
        project_id = None
        project_name = None
        if project:
            p = get_project(conn, project)
            if not p:
                raise click.ClickException(f"Project not found: {project}")
            project_id = p.id
            project_name = p.name

        gaps = detect_gaps(conn, project_id=project_id)
        click.echo(format_gaps_report(project_name, gaps))
    finally:
        conn.close()
