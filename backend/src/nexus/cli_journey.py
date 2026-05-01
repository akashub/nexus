from __future__ import annotations

import click

from nexus.db import get_connection, get_journey, get_project
from nexus.graph_helpers import format_journey


@click.command("journey")
@click.option("--project", "-p", default=None, help="Filter by project name.")
@click.option("--days", "-d", default=90, help="How many days back (default 90).")
def journey_cmd(project: str | None, days: int) -> None:
    """Show your learning journey as a timeline."""
    conn = get_connection()
    try:
        project_id = None
        if project:
            p = get_project(conn, project)
            if not p:
                raise click.ClickException(f"Project not found: {project}")
            project_id = p.id

        weeks = get_journey(conn, project_id=project_id, days=days)
        click.echo(format_journey(weeks))
    finally:
        conn.close()
