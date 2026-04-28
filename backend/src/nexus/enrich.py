from __future__ import annotations

import sqlite3

import click

from nexus.ai import cosine_similarity, embed, generate, is_available
from nexus.db import get_concept, list_concepts, update_concept
from nexus.fetch import fetch_context

CATEGORIES = ["devtool", "framework", "concept", "pattern", "language"]

_SYSTEM = (
    "You are a concise technical assistant helping a developer build a personal "
    "knowledge graph. Respond with only what is asked, no preamble."
)


def enrich_concept(conn: sqlite3.Connection, concept_id: str) -> None:
    if not is_available():
        click.echo("  Ollama not running — skipping enrichment.")
        return

    c = get_concept(conn, concept_id)
    if not c:
        return

    click.echo(f"  Enriching {c.name}...")

    docs = _fetch_docs(c.name)
    description = _generate_description(c.name, docs)
    summary = _generate_summary(c.name, description)
    category = _suggest_category(c.name, description, c.category)
    embedding = _generate_embedding(c.name, description)

    fields: dict = {}
    if description and not c.description:
        fields["description"] = description
    if summary and not c.summary:
        fields["summary"] = summary
    if category and not c.category:
        fields["category"] = category
    if embedding and not c.embedding:
        fields["embedding"] = embedding
    if fields:
        fields["source"] = "ollama"
        update_concept(conn, concept_id, **fields)
        click.echo(f"  Updated: {', '.join(fields.keys())}")

    _suggest_connections(conn, concept_id)


def _fetch_docs(name: str) -> str | None:
    click.echo("  Fetching docs via Context7...")
    docs = fetch_context(name)
    if docs:
        click.echo(f"  Found docs ({len(docs)} chars)")
        return docs[:4000]
    click.echo("  No docs found, using LLM knowledge only.")
    return None


def _generate_description(name: str, docs: str | None) -> str | None:
    context = f"\n\nReference docs:\n{docs}" if docs else ""
    prompt = (
        f"Describe '{name}' for a developer learning about it. "
        f"2-3 sentences, technically accurate.{context}"
    )
    try:
        return generate(prompt, system=_SYSTEM)
    except Exception:
        return None


def _generate_summary(name: str, description: str | None) -> str | None:
    if not description:
        return None
    prompt = f"Write a one-line summary (under 15 words) for '{name}': {description}"
    try:
        return generate(prompt, system=_SYSTEM)
    except Exception:
        return None


def _suggest_category(name: str, desc: str | None, existing: str | None) -> str | None:
    if existing:
        return existing
    prompt = (
        f"Categorize '{name}' as exactly one of: {', '.join(CATEGORIES)}.\n"
        f"Context: {desc or name}\nRespond with only the category word."
    )
    try:
        result = generate(prompt, system=_SYSTEM).strip().lower()
        return result if result in CATEGORIES else None
    except Exception:
        return None


def _generate_embedding(name: str, description: str | None) -> bytes | None:
    text = f"{name}: {description}" if description else name
    return embed(text)


def _suggest_connections(conn: sqlite3.Connection, concept_id: str) -> None:
    c = get_concept(conn, concept_id)
    if not c or not c.embedding:
        return

    candidates = []
    for other in list_concepts(conn, limit=50):
        if other.id == concept_id or not other.embedding:
            continue
        sim = cosine_similarity(c.embedding, other.embedding)
        if sim > 0.5:
            candidates.append((other, sim))

    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:3]

    if not top:
        return

    click.echo("  Suggested connections:")
    for other, sim in top:
        rel = _guess_relationship(c.name, c.description, other.name, other.description)
        click.echo(f"    {c.name} --[{rel}]--> {other.name}  (similarity: {sim:.2f})")


def _guess_relationship(
    name_a: str, desc_a: str | None, name_b: str, desc_b: str | None,
) -> str:
    prompt = (
        f"What is the relationship between '{name_a}' and '{name_b}'?\n"
        f"A: {desc_a or name_a}\nB: {desc_b or name_b}\n"
        f"Choose exactly one: uses, depends_on, similar_to, part_of, related_to\n"
        f"Respond with only the relationship."
    )
    try:
        result = generate(prompt, system=_SYSTEM).strip().lower()
        valid = ["uses", "depends_on", "similar_to", "part_of", "related_to"]
        return result if result in valid else "related_to"
    except Exception:
        return "related_to"
