from __future__ import annotations

import click

from nexus.cli_ask import ask_cmd
from nexus.cli_concept import remove_cmd, show_cmd
from nexus.cli_scan import scan_cmd
from nexus.db import (
    DB_PATH,
    add_concept,
    add_edge,
    get_concept,
    get_connection,
    init_db,
    list_concepts,
    search_fts,
)

VALID_RELATIONSHIPS = ["uses", "depends_on", "similar_to", "part_of", "related_to"]


def _require_concept(conn, name: str):
    c = get_concept(conn, name)
    if not c:
        raise click.ClickException(f"Concept not found: {name}")
    return c


@click.group()
def main() -> None:
    """Nexus — personal learning knowledge graph."""


@main.group()
def db() -> None:
    """Database management."""


@db.command("init")
def db_init() -> None:
    """Initialize the Nexus database."""
    init_db()
    click.echo(f"Database initialized at {DB_PATH}")


@main.command("add")
@click.argument("name")
@click.option("--category", "-c", default=None, help="devtool, framework, concept, pattern")
@click.option("--tags", "-t", default=None, help="Comma-separated tags.")
@click.option("--notes", "-n", default=None, help="Personal notes.")
@click.option("--no-enrich", is_flag=True, help="Skip AI enrichment.")
def add_cmd(
    name: str, category: str | None, tags: str | None, notes: str | None, no_enrich: bool,
) -> None:
    """Add a concept to your knowledge graph."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    conn = get_connection()
    try:
        existing = get_concept(conn, name)
        if existing:
            raise click.ClickException(f"Concept already exists: {existing.name}")
        c = add_concept(conn, name, category=category, tags=tag_list, notes=notes)
        click.echo(f"Added: {c.name} ({c.id[:8]})")
        if not no_enrich:
            from nexus.enrich import enrich_concept

            enrich_concept(conn, c.id)
    finally:
        conn.close()


@main.command("connect")
@click.argument("source")
@click.argument("target")
@click.option(
    "--type", "-t", "rel_type", default="related_to",
    type=click.Choice(VALID_RELATIONSHIPS),
    help="Relationship type.",
)
@click.option("--description", "-d", default=None, help="Why they're connected.")
def connect_cmd(source: str, target: str, rel_type: str, description: str | None) -> None:
    """Create a directed edge: SOURCE -> TARGET."""
    conn = get_connection()
    try:
        src = _require_concept(conn, source)
        tgt = _require_concept(conn, target)
        add_edge(conn, src.id, tgt.id, rel_type, description=description)
        click.echo(f"Connected: {src.name} --[{rel_type}]--> {tgt.name}")
    finally:
        conn.close()


@main.command("list")
@click.option("--category", "-c", default=None, help="Filter by category.")
@click.option("--limit", "-n", default=20, help="Max results.")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def list_cmd(category: str | None, limit: int, fmt: str) -> None:
    """List all concepts."""
    import json

    conn = get_connection()
    try:
        concepts = list_concepts(conn, limit=limit, category=category)
    finally:
        conn.close()
    if not concepts:
        click.echo("No concepts yet. Add one with: nexus add <name>")
        return
    if fmt == "json":
        data = [{"name": c.name, "category": c.category, "id": c.id} for c in concepts]
        click.echo(json.dumps(data, indent=2))
        return
    for c in concepts:
        cat = f" [{c.category}]" if c.category else ""
        click.echo(f"  {c.name}{cat}")


@main.command("search")
@click.argument("query")
@click.option("--semantic", "-s", is_flag=True, help="Use embedding similarity.")
def search_cmd(query: str, semantic: bool) -> None:
    """Search concepts by keyword or semantic similarity."""
    conn = get_connection()
    try:
        if semantic:
            from nexus.ai import cosine_similarity, embed

            qvec = embed(query)
            if not qvec:
                click.echo("Embedding model unavailable. Falling back to FTS.")
                results = search_fts(conn, query)
            else:
                all_c = list_concepts(conn, limit=200)
                scored = sorted(
                    ((c, cosine_similarity(qvec, c.embedding))
                     for c in all_c if c.embedding),
                    key=lambda x: x[1], reverse=True,
                )
                results = [c for c, s in scored[:10] if s > 0.3]
        else:
            results = search_fts(conn, query)
    finally:
        conn.close()
    if not results:
        click.echo(f"No results for: {query}")
        return
    click.echo(f"Found {len(results)} result(s):")
    for c in results:
        cat = f" [{c.category}]" if c.category else ""
        desc = f" — {c.description[:80]}" if c.description else ""
        click.echo(f"  {c.name}{cat}{desc}")


main.add_command(ask_cmd)
main.add_command(scan_cmd)
main.add_command(show_cmd)
main.add_command(remove_cmd)


@main.command("serve")
@click.option("--port", "-p", default=7777, help="Port number.")
@click.option("--host", default="127.0.0.1", help="Host address.")
def serve_cmd(port: int, host: str) -> None:
    """Start the Nexus API server."""
    import uvicorn

    click.echo(f"Starting Nexus server on {host}:{port}")
    uvicorn.run("nexus.server:app", host=host, port=port, reload=False)
