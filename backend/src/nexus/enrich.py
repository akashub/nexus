from __future__ import annotations

import json
import logging
import sqlite3
import time

import click

from nexus.ai import cosine_similarity, embed, generate, is_available
from nexus.db import get_concept, get_connection, list_concepts, update_concept
from nexus.fetch import fetch_context

log = logging.getLogger(__name__)

CATEGORIES = ["devtool", "framework", "concept", "pattern", "language"]

_SYSTEM = (
    "You are a concise technical assistant helping a developer build a personal "
    "knowledge graph. Respond with only what is asked, no preamble."
)

_ENRICH_PROMPT = """Analyze '{name}' for a developer's knowledge graph.
{context}
Respond in EXACTLY this JSON format, nothing else:
{{"description": "2-3 sentence technical description",\
 "summary": "one-line summary under 15 words",\
 "category": "one of: {categories}"}}"""


def enrich_concept(conn: sqlite3.Connection, concept_id: str) -> None:
    if not is_available():
        click.echo("  Ollama not running — skipping enrichment.")
        return

    c = get_concept(conn, concept_id)
    if not c:
        return

    click.echo(f"  Enriching {c.name}...")

    docs = _fetch_docs(c.name)
    fields = _generate_all(c.name, docs, c.category)

    time.sleep(1)
    embedding = _generate_embedding(c.name, fields.get("description"))

    if embedding and not c.embedding:
        fields["embedding"] = embedding
    filtered: dict = {}
    for k, v in fields.items():
        if v and not getattr(c, k, None):
            filtered[k] = v
    if filtered:
        filtered["source"] = "ollama"
        update_concept(conn, concept_id, **filtered)
        click.echo(f"  Updated: {', '.join(filtered.keys())}")

    _suggest_connections(conn, concept_id)


def _fetch_docs(name: str) -> str | None:
    click.echo("  Fetching docs via Context7...")
    docs = fetch_context(name)
    if docs:
        click.echo(f"  Found docs ({len(docs)} chars)")
        return docs[:3000]
    click.echo("  No docs found, using LLM knowledge only.")
    return None


def _generate_all(name: str, docs: str | None, existing_cat: str | None) -> dict:
    context = f"Reference docs:\n{docs}" if docs else "No docs available, use your knowledge."
    prompt = _ENRICH_PROMPT.format(
        name=name, context=context, categories=", ".join(CATEGORIES),
    )
    try:
        raw = generate(prompt, system=_SYSTEM)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
        else:
            return {}
        result: dict = {}
        if data.get("description"):
            result["description"] = data["description"]
        if data.get("summary"):
            result["summary"] = data["summary"]
        cat = (data.get("category") or "").strip().lower()
        if not existing_cat and cat in CATEGORIES:
            result["category"] = cat
        return result
    except Exception:
        return {}


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
        click.echo(f"    {c.name} --[related_to]--> {other.name}  (similarity: {sim:.2f})")


def enrich_background(concept_id: str) -> None:
    conn = get_connection()
    try:
        enrich_concept(conn, concept_id)
    except Exception:
        log.exception("Background enrichment failed for concept %s", concept_id)
    finally:
        conn.close()
