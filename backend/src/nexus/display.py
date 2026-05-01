from __future__ import annotations

import click

from nexus.db import get_concept


def print_concept_detail(conn, c, edges) -> None:
    click.echo(f"\n  {c.name}")
    if c.category:
        click.echo(f"  [{c.category}]")
    click.echo()

    if c.description:
        click.echo(f"  {c.description}")
        click.echo()
    if c.summary:
        click.echo(f"  Summary: {c.summary}")
    if c.tags:
        click.echo(f"  Tags: {', '.join(c.tags)}")
    if c.notes:
        click.echo(f"  Notes: {c.notes}")
    if c.quickstart:
        lines = c.quickstart.strip().splitlines()
        preview = "\n    ".join(lines[:8])
        click.echo(f"\n  Install / Quickstart:\n    {preview}")
        if len(lines) > 8:
            click.echo(f"    ... ({len(lines) - 8} more lines)")
    if c.source != "manual":
        click.echo(f"  Source: {c.source}")

    _print_edges(conn, c, edges)
    click.echo(f"\n  Created: {c.created_at}")
    click.echo(f"  ID: {c.id}")


def _print_edges(conn, c, edges) -> None:
    if not edges:
        return
    click.echo()
    outgoing = [e for e in edges if e.source_id == c.id]
    incoming = [e for e in edges if e.target_id == c.id]
    if outgoing:
        click.echo("  Outgoing:")
        for e in outgoing:
            target = get_concept(conn, e.target_id)
            tname = target.name if target else e.target_id[:8]
            click.echo(f"    -> {tname}  ({e.relationship})")
    if incoming:
        click.echo("  Incoming:")
        for e in incoming:
            source = get_concept(conn, e.source_id)
            sname = source.name if source else e.source_id[:8]
            click.echo(f"    <- {sname}  ({e.relationship})")
