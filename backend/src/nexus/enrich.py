from __future__ import annotations

import contextlib
import json
import logging
import sqlite3

import click

from nexus.ai import cosine_similarity, embed, generate, is_available
from nexus.db import get_concept, get_connection, list_concepts, update_concept
from nexus.fetch import fetch_context, fetch_quickstart

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

_AI_FIELDS = {"description", "summary", "quickstart", "context7_id", "doc_url", "embedding"}


def _set_status(conn: sqlite3.Connection, cid: str, status: str | None) -> None:
    update_concept(conn, cid, enrich_status=status)


def enrich_concept(conn: sqlite3.Connection, concept_id: str) -> None:
    if not is_available():
        click.echo("  Ollama not running — skipping enrichment.")
        return

    c = get_concept(conn, concept_id)
    if not c:
        return

    click.echo(f"  Enriching {c.name}...")
    _set_status(conn, concept_id, "fetching_docs")

    docs_result = fetch_context(c.name)
    fields: dict = {}

    if docs_result:
        click.echo(f"  Found docs ({len(docs_result.text)} chars)")
        if docs_result.library_id:
            fields["context7_id"] = docs_result.library_id
        if docs_result.doc_url:
            fields["doc_url"] = docs_result.doc_url
    else:
        click.echo("  No docs found, using LLM knowledge only.")

    _set_status(conn, concept_id, "generating")
    docs_text = docs_result.text[:3000] if docs_result else None
    llm_fields = _generate_all(c.name, docs_text, c.category)
    fields.update(llm_fields)

    if docs_result and docs_result.library_id:
        _set_status(conn, concept_id, "fetching_quickstart")
        qs = fetch_quickstart(docs_result.library_id)
        if qs:
            fields["quickstart"] = qs[:5000]

    _set_status(conn, concept_id, "embedding")
    new_embedding = embed(f"{c.name}: {fields.get('description', c.name)}")
    if new_embedding:
        fields["embedding"] = new_embedding

    final: dict = {}
    for k, v in fields.items():
        if not v:
            continue
        if k in _AI_FIELDS or not getattr(c, k, None):
            final[k] = v

    if final:
        final["source"] = "ollama"
        final["enrich_status"] = None
        update_concept(conn, concept_id, **final)
        click.echo(f"  Updated: {', '.join(k for k in final if k != 'enrich_status')}")
    else:
        _set_status(conn, concept_id, None)

    _set_status(conn, concept_id, "connecting")
    _suggest_connections(conn, concept_id)
    _set_status(conn, concept_id, None)


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
    for other, sim in candidates[:3]:
        click.echo(f"    {c.name} --[related_to]--> {other.name}  (sim: {sim:.2f})")


def enrich_background(concept_id: str) -> None:
    conn = get_connection()
    try:
        enrich_concept(conn, concept_id)
    except Exception:
        log.exception("Background enrichment failed for concept %s", concept_id)
        with contextlib.suppress(Exception):
            _set_status(conn, concept_id, None)
    finally:
        conn.close()
