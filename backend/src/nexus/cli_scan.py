from __future__ import annotations

from pathlib import Path

import click

from nexus.db import get_connection
from nexus.scanner import scan_project
from nexus.sync import sync_scan_results


@click.command("scan")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--enrich", is_flag=True, help="Enrich new concepts after scanning.")
@click.option("--dry-run", is_flag=True, help="Preview without writing to DB.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output.")
def scan_cmd(path: str, enrich: bool, dry_run: bool, verbose: bool) -> None:
    """Scan a project directory and build its knowledge graph."""
    project_path = Path(path).resolve()
    click.echo(f"Scanning {project_path}...")

    result = scan_project(project_path, verbose=verbose)

    if not result.concepts:
        click.echo("No concepts found.")
        return

    click.echo(f"Found {len(result.concepts)} concepts, "
               f"{len(result.relationships)} relationships")

    if dry_run:
        click.echo("\nDry run — would add:")
        for c in result.concepts:
            cat = f" [{c.category_hint}]" if c.category_hint else ""
            src = f" ({c.source})" if c.source else ""
            click.echo(f"  {c.name}{cat}{src}")
        for r in result.relationships:
            click.echo(f"  {r.source_name} --[{r.relationship}]--> {r.target_name}")
        return

    conn = get_connection()
    try:
        stats = sync_scan_results(
            conn, str(project_path), result,
            verbose=verbose, enrich=enrich,
        )
    finally:
        conn.close()

    click.echo(f"\nDone: {stats['added']} added, {stats['skipped']} skipped, "
               f"{stats['edges_added']} edges")
