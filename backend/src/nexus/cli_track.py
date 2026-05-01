from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import click

from nexus.db import (
    add_concept,
    add_project,
    get_concept,
    get_concept_by_name_and_project,
    get_connection,
    get_project,
    get_project_by_path,
    update_concept,
)

SOURCE_CATEGORIES = {
    "npm": "framework",
    "pip": "framework",
    "brew": "devtool",
    "cargo": "framework",
}

INSTALL_TEMPLATES = {
    "npm": "npm install {dev}{name}",
    "pip": "pip install {name}",
    "brew": "brew install {name}",
    "cargo": "cargo add {name}",
}

_VALID_NAME = re.compile(r"^[a-zA-Z0-9@_./-][a-zA-Z0-9@_./-]*$")


def _ensure_project(conn, project_dir: str):
    """Get or create a project for the given directory path."""
    project = get_project_by_path(conn, project_dir)
    if project:
        return project
    proj_name = Path(project_dir).name
    try:
        return add_project(conn, proj_name, path=project_dir)
    except sqlite3.IntegrityError:
        # Project name collision (e.g. /foo/app and /bar/app).
        # Fall back to lookup by name.
        return get_project(conn, proj_name)


def track_concept(
    conn,
    name: str,
    project_dir: str,
    source: str = "npm",
    dev: bool = False,
) -> dict:
    """Track a newly installed package in the knowledge graph."""
    name = name.strip()
    if not name or not _VALID_NAME.match(name):
        return {"status": "error", "message": f"Invalid package name: {name!r}"}

    project = _ensure_project(conn, project_dir)
    if not project:
        return {"status": "error", "message": f"Could not resolve project for {project_dir}"}

    existing = get_concept_by_name_and_project(conn, name, project.id)
    if existing:
        return {"status": "exists", "name": existing.name, "id": existing.id}

    category = SOURCE_CATEGORIES.get(source)
    tpl = INSTALL_TEMPLATES.get(source, "install {name}")
    dev_flag = "-D " if dev and source == "npm" else ""
    setup_cmd = tpl.format(name=name, dev=dev_flag)

    try:
        c = add_concept(
            conn, name, category=category, source="hook_capture",
            project_id=project.id,
        )
    except sqlite3.IntegrityError:
        # Global UNIQUE(name) collision — concept exists in another project.
        c = get_concept(conn, name)
        if c:
            return {"status": "exists", "name": c.name, "id": c.id}
        return {"status": "error", "message": f"Failed to add concept: {name}"}

    update_concept(conn, c.id, setup_commands=[setup_cmd])
    return {"status": "added", "name": c.name, "id": c.id}


@click.command("track")
@click.argument("name")
@click.option(
    "--project-dir", "-p", default=".",
    type=click.Path(exists=True),
    help="Project directory.",
)
@click.option(
    "--source", "-s", default="npm",
    type=click.Choice(["npm", "pip", "brew", "cargo"]),
)
@click.option("--dev", is_flag=True, help="Dev dependency.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output.")
def track_cmd(
    name: str, project_dir: str, source: str, dev: bool, quiet: bool,
) -> None:
    """Track a newly installed package in the knowledge graph."""
    project_dir = str(Path(project_dir).resolve())
    conn = get_connection()
    try:
        result = track_concept(
            conn, name, project_dir, source=source, dev=dev,
        )
        if result["status"] == "error":
            raise click.ClickException(result["message"])
        if not quiet:
            if result["status"] == "added":
                click.echo(f"Tracked: {result['name']}")
            else:
                click.echo(f"Already tracked: {result['name']}")
    finally:
        conn.close()
