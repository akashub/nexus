from __future__ import annotations

from datetime import datetime

import click

from nexus.db import get_connection, get_journey, get_project


def _format_week_label(week_start: str) -> str:
    dt = datetime.fromisoformat(week_start)
    return dt.strftime("Week of %b %-d")


def _print_tree(weeks: list[dict]) -> None:
    total_concepts = 0
    for week in weeks:
        click.echo(f"\n{_format_week_label(week['week_start'])}")
        concepts = week["concepts"]
        total_concepts += len(concepts)
        for i, c in enumerate(concepts):
            is_last = i == len(concepts) - 1
            prefix = "  └── " if is_last else "  ├── "
            cat = f" [{c.category}]" if c.category else ""
            desc = ""
            if c.summary:
                desc = f" — {c.summary[:60]}"
            elif c.description:
                desc = f" — {c.description[:60]}"
            click.echo(f"{prefix}{c.name}{cat}{desc}")

    click.echo(f"\n{len(weeks)} week(s) · {total_concepts} concept(s)")


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
        if not weeks:
            click.echo("No concepts found in this time range.")
            return
        _print_tree(weeks)
    finally:
        conn.close()
