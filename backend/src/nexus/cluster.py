from __future__ import annotations

import json
import sqlite3

import click

from nexus.ai import generate, is_available
from nexus.db_concepts import list_concepts, update_concept

_SYSTEM = (
    "You cluster software concepts by their semantic role in a project. "
    'Reply with ONLY JSON: {"groups": {"Group Name": ["concept1", ...], ...}}. '
    "Create 5-8 groups. Names describe the ROLE in the project "
    "(e.g. 'Agent Core', 'API Layer', 'Geospatial'), not tool type."
)


def cluster_concepts(
    conn: sqlite3.Connection, *,
    project_id: str | None = None,
    project_name: str | None = None,
    verbose: bool = False,
) -> dict:
    if not is_available():
        click.echo("ollama not available — skipping clustering")
        return {"clustered": 0, "groups": 0}
    concepts = list_concepts(conn, limit=500, project_id=project_id)
    if len(concepts) < 3:
        return {"clustered": 0, "groups": 0}

    overview = ""
    if project_name:
        try:
            from nexus.context import get_eagle_overview
            overview = get_eagle_overview(project_name) or ""
        except Exception:
            pass

    items = "\n".join(
        f"- {c.name}" + (f": {c.description[:100]}" if c.description else "")
        for c in concepts
    )
    prompt = f"Project: {project_name or 'unknown'}\n"
    if overview:
        prompt += f"Context: {overview[:400]}\n"
    prompt += f"\nConcepts:\n{items}\n\nCluster these by semantic role."

    try:
        raw = generate(prompt, system=_SYSTEM)
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start < 0 or end <= start:
            return {"clustered": 0, "groups": 0}
        groups = json.loads(raw[start:end]).get("groups", {})
    except (json.JSONDecodeError, Exception):
        return {"clustered": 0, "groups": 0}

    name_map = {c.name.lower(): c.id for c in concepts}
    clustered = 0
    for group, members in groups.items():
        for name in members:
            cid = name_map.get(name.lower())
            if cid:
                update_concept(conn, cid, semantic_group=group)
                clustered += 1
                if verbose:
                    click.echo(f"  {name} -> {group}")
    return {"clustered": clustered, "groups": len(groups)}
