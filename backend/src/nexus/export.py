from __future__ import annotations

from nexus.models import Concept, Edge


def export_graph(
    concepts: list[Concept], edges: list[Edge], *, fmt: str = "json",
) -> dict | str:
    if fmt == "markdown":
        return _to_markdown(concepts, edges)
    return _to_json(concepts, edges)


def _to_json(concepts: list[Concept], edges: list[Edge]) -> dict:
    name_map = {c.id: c.name for c in concepts}
    return {
        "concepts": [
            {
                "name": c.name, "category": c.category,
                "description": c.description, "summary": c.summary,
                "tags": c.tags, "source": c.source,
            }
            for c in concepts
        ],
        "relationships": [
            {
                "source": name_map.get(e.source_id, e.source_id[:8]),
                "target": name_map.get(e.target_id, e.target_id[:8]),
                "relationship": e.relationship,
                "description": e.description,
            }
            for e in edges
        ],
    }


def _to_markdown(concepts: list[Concept], edges: list[Edge]) -> str:
    name_map = {c.id: c.name for c in concepts}
    outgoing: dict[str, list[Edge]] = {}
    for e in edges:
        outgoing.setdefault(e.source_id, []).append(e)

    lines = ["# Knowledge Graph Export", ""]
    for c in sorted(concepts, key=lambda x: x.name.lower()):
        cat = f" ({c.category})" if c.category else ""
        lines.append(f"## {c.name}{cat}")
        if c.summary:
            lines.append(f"*{c.summary}*")
        if c.description:
            lines.append("")
            lines.append(c.description)
        conns = outgoing.get(c.id, [])
        if conns:
            lines.append("")
            for e in conns:
                target = name_map.get(e.target_id, "?")
                lines.append(f"- **{e.relationship}** → {target}")
        lines.append("")
    return "\n".join(lines)


