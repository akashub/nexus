from __future__ import annotations

import contextlib
import json
import logging
import sqlite3

import click

from nexus.ai import cosine_similarity, is_available, smart_embed, smart_generate
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
Focus on WHAT '{name}' IS and WHY a developer would use it.
If existing knowledge is provided, improve and expand on it — don't repeat it verbatim.
If workflow context is provided, incorporate HOW it's used in this developer's projects.
Do NOT summarize installation steps, onboarding docs, or setup instructions.
Respond in EXACTLY this JSON format, nothing else:
{{"description": "2-3 sentence technical description of what it is and its key capabilities",\
 "summary": "one-line summary under 15 words",\
 "category": "one of: {categories}"}}"""

_AI_FIELDS = {"description", "summary", "quickstart", "context7_id", "embedding"}
_USER_FIELDS = {"doc_url", "notes", "category"}


def _set_status(conn: sqlite3.Connection, cid: str, status: str | None) -> None:
    update_concept(conn, cid, enrich_status=status)


def enrich_concept(
    conn: sqlite3.Connection, concept_id: str, mode: str = "auto",
    provider: str | None = None, model: str | None = None,
) -> None:
    from nexus.ai_cloud import is_cloud_available
    use_cloud = provider and provider != "ollama"
    if not is_available() and not (use_cloud and is_cloud_available(provider)):
        click.echo("  No AI available (Ollama down, no cloud key) — skipping.")
        return

    c = get_concept(conn, concept_id)
    if not c:
        return

    click.echo(f"  Enriching {c.name} (source={mode})...")

    _set_status(conn, concept_id, "fetching_context")
    eagle_ctx = _fetch_eagle_mem_context(c.name)
    if eagle_ctx:
        click.echo(f"  Eagle Mem context ({len(eagle_ctx)} chars)")

    _set_status(conn, concept_id, "fetching_docs")
    docs_result = fetch_context(c.name, mode=mode)
    fields: dict = {}

    if docs_result:
        click.echo(f"  Found docs ({len(docs_result.text)} chars)")
        if docs_result.library_id:
            fields["context7_id"] = docs_result.library_id
        if docs_result.doc_url:
            fields["doc_url"] = docs_result.doc_url
    elif not eagle_ctx:
        click.echo("  No docs found, using LLM knowledge only.")

    _set_status(conn, concept_id, "generating")
    docs_text = docs_result.text[:3000] if docs_result else None
    existing_ctx = _build_existing_context(c)
    llm_fields = _generate_all(
        c.name, docs_text, c.category, eagle_ctx, existing_ctx,
        provider=provider, model=model,
    )
    fields.update(llm_fields)

    if docs_result and docs_result.library_id:
        _set_status(conn, concept_id, "fetching_quickstart")
        qs = fetch_quickstart(docs_result.library_id)
        if qs:
            fields["quickstart"] = qs[:5000]

    _set_status(conn, concept_id, "embedding")
    embed_input = f"{c.name}: {fields.get('description', c.name)}"
    new_embedding = smart_embed(embed_input, prefer_cloud=provider not in (None, "ollama"))
    if new_embedding:
        fields["embedding"] = new_embedding

    final: dict = {}
    for k, v in fields.items():
        if not v:
            continue
        existing_val = getattr(c, k, None)
        if k in _USER_FIELDS and existing_val:
            continue
        if k in _AI_FIELDS or not existing_val:
            final[k] = v

    if final:
        final["source"] = provider or "ollama"
        final["enrich_status"] = None
        update_concept(conn, concept_id, **final)
        click.echo(f"  Updated: {', '.join(k for k in final if k != 'enrich_status')}")
    else:
        _set_status(conn, concept_id, None)

    _set_status(conn, concept_id, "connecting")
    _suggest_connections(conn, concept_id)
    _set_status(conn, concept_id, None)


def _build_existing_context(c) -> str | None:
    parts: list[str] = []
    if c.description:
        parts.append(f"Current description: {c.description}")
    if c.summary:
        parts.append(f"Current summary: {c.summary}")
    if c.notes:
        parts.append(f"User notes: {c.notes[:500]}")
    return "\n".join(parts) if parts else None


def _fetch_eagle_mem_context(name: str) -> str | None:
    try:
        from nexus.scanners.eagle_mem import get_enrichment_context
        return get_enrichment_context(name)
    except Exception:
        return None


def _generate_all(
    name: str, docs: str | None, existing_cat: str | None, eagle_ctx: str | None = None,
    existing_ctx: str | None = None, provider: str | None = None, model: str | None = None,
) -> dict:
    parts: list[str] = []
    if existing_ctx:
        parts.append(f"Existing knowledge (improve on this):\n{existing_ctx}")
    if eagle_ctx:
        parts.append(f"Workflow context (how this developer uses it):\n{eagle_ctx[:1500]}")
    if docs:
        parts.append(f"Technical docs:\n{docs}")
    context = "\n\n".join(parts) if parts else "No docs available, use your knowledge."
    prompt = _ENRICH_PROMPT.format(
        name=name, context=context, categories=", ".join(CATEGORIES),
    )
    try:
        raw = smart_generate(prompt, system=_SYSTEM, provider=provider, model=model)
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

    candidates = [
        (o, cosine_similarity(c.embedding, o.embedding))
        for o in list_concepts(conn, limit=50)
        if o.id != concept_id and o.embedding
    ]
    candidates = [(o, s) for o, s in candidates if s > 0.5]
    candidates.sort(key=lambda x: x[1], reverse=True)
    for other, sim in candidates[:3]:
        click.echo(f"    {c.name} --[related_to]--> {other.name}  (sim: {sim:.2f})")


def enrich_background(concept_id: str, mode: str = "auto",
                      provider: str | None = None, model: str | None = None) -> None:
    conn = get_connection()
    try:
        enrich_concept(conn, concept_id, mode=mode, provider=provider, model=model)
    except Exception:
        log.exception("Background enrichment failed for concept %s", concept_id)
        with contextlib.suppress(Exception):
            _set_status(conn, concept_id, None)
    finally:
        conn.close()
