from __future__ import annotations

import click

from nexus.db import add_conversation, get_concept, get_connection, get_edges, search_fts


@click.command("ask")
@click.argument("question")
def ask_cmd(question: str) -> None:
    """Ask a question using your knowledge graph as context."""
    from nexus.ai import generate_stream, is_available

    if not is_available():
        raise click.ClickException("Ollama is not running.")

    conn = get_connection()
    try:
        related = search_fts(conn, question)[:5]
        context_parts = []
        for c in related:
            edges = get_edges(conn, c.id)
            conns = []
            for e in edges:
                t = get_concept(conn, e.target_id)
                if t and e.source_id == c.id:
                    conns.append(f"{c.name} --[{e.relationship}]--> {t.name}")
            entry = f"- {c.name}"
            if c.category:
                entry += f" [{c.category}]"
            if c.description:
                entry += f": {c.description}"
            if conns:
                entry += f"\n  Connections: {'; '.join(conns)}"
            context_parts.append(entry)

        ctx = "\n".join(context_parts) if context_parts else "No relevant concepts found."
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
