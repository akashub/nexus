from __future__ import annotations

import click

from nexus.db import delete_concept, get_concept, get_connection, get_edges


def _require_concept(conn, name: str):
    c = get_concept(conn, name)
    if not c:
        raise click.ClickException(f"Concept not found: {name}")
    return c


@click.command("show")
@click.argument("name")
def show_cmd(name: str) -> None:
    """Show full details for a concept."""
    from nexus.display import print_concept_detail

    conn = get_connection()
    try:
        c = _require_concept(conn, name)
        edges = get_edges(conn, c.id)
        print_concept_detail(conn, c, edges)
    finally:
        conn.close()


@click.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def remove_cmd(name: str, yes: bool) -> None:
    """Remove a concept and its edges."""
    conn = get_connection()
    try:
        c = _require_concept(conn, name)
        edges = get_edges(conn, c.id)
        if not yes:
            msg = f"Delete '{c.name}'"
            if edges:
                msg += f" and {len(edges)} edge(s)"
            msg += "?"
            click.confirm(msg, abort=True)
        delete_concept(conn, c.id)
        click.echo(f"Removed: {c.name}")
    finally:
        conn.close()
