from __future__ import annotations

import json
from pathlib import Path

import click

from nexus.db import get_connection, get_project, get_project_by_path, list_projects
from nexus.expertise import classify_expertise


def _resolve_project(conn, project: str | None, project_dir: str | None):
    if project:
        p = get_project(conn, project)
        if p:
            return p
        raise click.ClickException(f"Project not found: {project}")
    if project_dir:
        p = get_project_by_path(conn, str(Path(project_dir).resolve()))
        if p:
            return p
        raise click.ClickException(f"No project at: {project_dir}")
    projects = list_projects(conn)
    if len(projects) == 1:
        return projects[0]
    raise click.ClickException("Multiple projects — specify --project or --project-dir")


@click.command("onboard")
@click.option("--project", "-p", default=None, help="Project name or ID.")
@click.option("--project-dir", default=None, type=click.Path(exists=True), help="Resolve from dir.")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def onboard_cmd(project: str | None, project_dir: str | None, fmt: str) -> None:
    """Show expertise profile for a project."""
    conn = get_connection()
    try:
        p = _resolve_project(conn, project, project_dir)
        profile = classify_expertise(conn, p.id)
    finally:
        conn.close()

    if fmt == "json":
        click.echo(json.dumps(profile.to_dict(), indent=2))
        return

    click.echo(f"Expertise Profile: {profile.project_name} ({profile.total} concepts)\n")
    if profile.known_well:
        click.echo(f"KNOWN WELL ({len(profile.known_well)})")
        for e in profile.known_well:
            cat = f"  {e.category}" if e.category else ""
            click.echo(f"  {e.name:<20}{cat:<14}{', '.join(e.signals)}")
        click.echo()
    if profile.seen:
        click.echo(f"SEEN ({len(profile.seen)})")
        for e in profile.seen:
            cat = f"  {e.category}" if e.category else ""
            click.echo(f"  {e.name:<20}{cat:<14}{', '.join(e.signals)}")
        click.echo()
    if profile.gaps:
        click.echo(f"GAPS ({len(profile.gaps)})")
        for e in profile.gaps:
            click.echo(f"  {e.name:<20}{'-':<14}{', '.join(e.signals)}")
