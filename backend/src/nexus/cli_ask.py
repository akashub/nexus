from __future__ import annotations

import click

from nexus.db import (
    add_conversation,
    get_concept,
    get_connection,
    get_edges,
    list_concepts,
    search_fts,
)


def _find_related(conn, question: str, limit: int = 5):
    results = search_fts(conn, question)[:limit]
    if len(results) >= limit:
        return results
    from nexus.ai import cosine_similarity, embed
    qvec = embed(question)
    if not qvec:
        return results
    seen = {c.id for c in results}
    scored = [
        (c, cosine_similarity(qvec, c.embedding))
        for c in list_concepts(conn, limit=200) if c.embedding and c.id not in seen
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    results.extend(c for c, s in scored[:limit - len(results)] if s > 0.3)
    return results


def _build_context(conn, concepts) -> str:
    parts = []
    for c in concepts:
        entry = f"- {c.name}"
        if c.category:
            entry += f" [{c.category}]"
        if c.description:
            entry += f": {c.description}"
        edges = get_edges(conn, c.id)
        conns = []
        for e in edges:
            other_id = e.target_id if e.source_id == c.id else e.source_id
            other = get_concept(conn, other_id)
            if not other:
                continue
            if e.source_id == c.id:
                conns.append(f"{c.name} --[{e.relationship}]--> {other.name}")
            else:
                conns.append(f"{other.name} --[{e.relationship}]--> {c.name}")
        if conns:
            entry += f"\n  Connections: {'; '.join(conns)}"
        parts.append(entry)
    return "\n".join(parts) if parts else "No relevant concepts found."


@click.command("ask")
@click.argument("question")
def ask_cmd(question: str) -> None:
    """Ask a question using your knowledge graph as context."""
    from nexus.ai import generate_stream, is_available

    if not is_available():
        raise click.ClickException("Ollama is not running.")

    conn = get_connection()
    try:
        related = _find_related(conn, question)
        ctx = _build_context(conn, related)
        prompt = (
            f"Knowledge graph context:\n{ctx}\n\n"
            f"Question: {question}\n\n"
            f"Answer using the context above. Be specific and reference concepts."
        )

        answer_parts = []
        for chunk in generate_stream(prompt):
            click.echo(chunk, nl=False)
            answer_parts.append(chunk)
        click.echo()

        answer = "".join(answer_parts)
        concept_ids = [c.id for c in related]
        add_conversation(conn, question, answer, concept_ids)
    finally:
        conn.close()
