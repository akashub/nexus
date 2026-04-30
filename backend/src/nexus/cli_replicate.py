from __future__ import annotations

from pathlib import Path

import click

from nexus.db import get_connection, get_project, get_project_by_path


@click.command("replicate")
@click.argument("project_name")
@click.option("--context", "-c", default=None, help="Filter by context query (semantic).")
@click.option("--output", "-o", default=None, help="Write script to file instead of stdout.")
@click.option("--list-only", is_flag=True, help="List installable concepts.")
def replicate_cmd(
    project_name: str, context: str | None, output: str | None, list_only: bool,
) -> None:
    """Generate a setup script to replicate a project's environment."""
    from nexus.replicate import generate_setup_script, list_installable

    conn = get_connection()
    try:
        project = get_project(conn, project_name)
        if not project:
            project = get_project_by_path(conn, str(Path(project_name).resolve()))
        if not project:
            raise click.ClickException(f"Project not found: {project_name}")

        if list_only:
            items = list_installable(conn, project.id)
            if not items:
                click.echo("No installable concepts found.")
                return
            click.echo(f"Installable concepts in {project.name}:")
            for item in items:
                cat = f" [{item['category']}]" if item.get("category") else ""
                cmds = ", ".join(item["setup_commands"])
                click.echo(f"  {item['name']}{cat}: {cmds}")
            return

        script = generate_setup_script(conn, project.id, context_query=context)
    finally:
        conn.close()

    if output:
        Path(output).write_text(script)
        Path(output).chmod(0o755)
        click.echo(f"Script written to {output}")
    else:
        click.echo(script)
