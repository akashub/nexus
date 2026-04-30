from __future__ import annotations

from pathlib import Path

import click

from nexus.db import (
    add_project,
    delete_project,
    get_connection,
    get_project,
    get_project_by_path,
    list_concepts,
    list_projects,
)


@click.group("project")
def project_group() -> None:
    """Manage projects in the knowledge graph."""


@project_group.command("list")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def project_list_cmd(fmt: str) -> None:
    """List all registered projects."""
    import json

    conn = get_connection()
    try:
        projects = list_projects(conn)
        if not projects:
            click.echo("No projects yet. Scan one with: nexus scan /path/to/project")
            return
        if fmt == "json":
            data = [{"name": p.name, "path": p.path, "id": p.id} for p in projects]
            click.echo(json.dumps(data, indent=2))
            return
        for p in projects:
            concepts = list_concepts(conn, project_id=p.id, limit=10000)
            path = f"  {p.path}" if p.path else ""
            click.echo(f"  {p.name} ({len(concepts)} concepts){path}")
    finally:
        conn.close()


@project_group.command("add")
@click.argument("name")
@click.option("--path", "-p", default=None, help="Path to project directory.")
@click.option("--description", "-d", default=None, help="Project description.")
def project_add_cmd(name: str, path: str | None, description: str | None) -> None:
    """Register a new project."""
    resolved = str(Path(path).resolve()) if path else None
    conn = get_connection()
    try:
        existing = get_project(conn, name)
        if existing:
            raise click.ClickException(f"Project already exists: {name}")
        if resolved:
            by_path = get_project_by_path(conn, resolved)
            if by_path:
                raise click.ClickException(f"Path already registered as: {by_path.name}")
        p = add_project(conn, name, path=resolved, description=description)
        click.echo(f"Added project: {p.name} ({p.id[:8]})")
    finally:
        conn.close()


@project_group.command("show")
@click.argument("name")
def project_show_cmd(name: str) -> None:
    """Show project details."""
    conn = get_connection()
    try:
        p = get_project(conn, name)
        if not p:
            p = get_project_by_path(conn, str(Path(name).resolve()))
        if not p:
            raise click.ClickException(f"Project not found: {name}")
        concepts = list_concepts(conn, project_id=p.id, limit=10000)
        cats: dict[str, int] = {}
        for c in concepts:
            key = c.category or "uncategorized"
            cats[key] = cats.get(key, 0) + 1
    finally:
        conn.close()

    click.echo(f"Project: {p.name}")
    if p.path:
        click.echo(f"  Path: {p.path}")
    if p.description:
        click.echo(f"  Description: {p.description}")
    click.echo(f"  Concepts: {len(concepts)}")
    if cats:
        breakdown = ", ".join(f"{v} {k}" for k, v in sorted(cats.items()))
        click.echo(f"  Categories: {breakdown}")
    if p.last_scanned_at:
        click.echo(f"  Last scanned: {p.last_scanned_at}")


@project_group.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def project_remove_cmd(name: str, yes: bool) -> None:
    """Remove a project (concepts become unassigned)."""
    conn = get_connection()
    try:
        p = get_project(conn, name)
        if not p:
            raise click.ClickException(f"Project not found: {name}")
        if not yes:
            click.confirm(f"Remove project '{p.name}'?", abort=True)
        delete_project(conn, p.id)
        click.echo(f"Removed project: {p.name}")
    finally:
        conn.close()
