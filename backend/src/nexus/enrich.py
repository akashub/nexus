from __future__ import annotations

import contextlib
import json
import logging
import sqlite3

import click

from nexus.ai import is_available, smart_embed, smart_generate
from nexus.context import (
    get_ai_tool_memories,
    get_claude_memories,
    get_eagle_overview,
)
from nexus.db import get_concept, get_connection, get_project, update_concept
from nexus.db_concepts import list_concepts
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
Do NOT include project-specific usage, installation steps, or setup instructions.
Respond in EXACTLY this JSON format, nothing else:
{{"description": "2-3 sentence technical description of what it is and its key capabilities",\
 "summary": "one-line summary under 15 words",\
 "category": "one of: {categories}"}}"""

_AI_FIELDS = {"description", "summary", "quickstart", "context7_id", "embedding", "usage_summary"}
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
    try:
        from nexus.scanners.eagle_mem import get_enrichment_context
        eagle_ctx = get_enrichment_context(c.name)
    except Exception:
        eagle_ctx = None
    if eagle_ctx:
        click.echo(f"  Eagle Mem context ({len(eagle_ctx)} chars)")

    project_ctx = _build_project_context(conn, c.project_id)

    _set_status(conn, concept_id, "fetching_docs")
    docs_result = fetch_context(c.name, mode=mode)
    fields: dict = {}

    if docs_result:
        if _check_docs_relevance(c.name, docs_result.text, project_ctx, eagle_ctx):
            click.echo(f"  Found docs ({len(docs_result.text)} chars)")
            if docs_result.library_id:
                fields["context7_id"] = docs_result.library_id
            if docs_result.doc_url:
                fields["doc_url"] = docs_result.doc_url
        else:
            click.echo(f"  Docs rejected — wrong '{c.name}' for this project context.")
            docs_result = None
    if not docs_result and not eagle_ctx:
        click.echo("  No docs found, using LLM knowledge only.")

    _set_status(conn, concept_id, "generating")
    docs_text = docs_result.text[:3000] if docs_result else None
    existing_ctx = _build_existing_context(c)
    llm_fields = _generate_all(
        c.name, docs_text, c.category, existing_ctx,
        provider=provider, model=model,
    )
    fields.update(llm_fields)

    if eagle_ctx:
        fields["usage_summary"] = _build_usage_summary(c.name, eagle_ctx)

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

    final = {
        k: v for k, v in fields.items()
        if v and not (k in _USER_FIELDS and getattr(c, k, None))
        and (k in _AI_FIELDS or not getattr(c, k, None))
    }

    if final:
        final["source"] = provider or "ollama"
        update_concept(conn, concept_id, **final)
        click.echo(f"  Updated: {', '.join(final)}")

    _set_status(conn, concept_id, None)


def _build_project_context(
    conn: sqlite3.Connection, project_id: str | None,
) -> str:
    """Build a rich project profile from all available sources."""
    if not project_id:
        return ""
    parts: list[str] = []
    project = get_project(conn, project_id)
    if not project:
        return ""

    if project.description:
        parts.append(f"Project: {project.description[:200]}")

    overview = get_eagle_overview(project.name)
    if overview:
        parts.append(f"Overview:\n{overview[:400]}")

    siblings = list_concepts(conn, project_id=project_id, limit=50)
    names = [s.name for s in siblings if s.name]
    if names:
        parts.append(f"Stack: {', '.join(names[:30])}")

    if project.path:
        for mem in get_claude_memories(project.path)[:3]:
            parts.append(f"Memory ({mem['name']}): {mem['content'][:150]}")
        for inst in get_ai_tool_memories(project.path)[:2]:
            parts.append(f"Instructions ({inst['name']}): {inst['content'][:150]}")

    return "\n".join(parts)


def _check_docs_relevance(
    name: str, docs_text: str, project_ctx: str,
    eagle_ctx: str | None = None,
) -> bool:
    """Ask LLM whether fetched docs match this project's context."""
    if not project_ctx or not is_available():
        return True
    parts = [
        f"Project context:\n{project_ctx[:800]}",
        f"Fetched docs for '{name}':\n{docs_text[:400]}",
    ]
    if eagle_ctx:
        parts.append(
            f"Developer's usage of '{name}':\n{eagle_ctx[:300]}"
        )
    parts.append(
        f"Are these docs about the correct '{name}' for this project? "
        "Reply ONLY 'YES' or 'NO'."
    )
    try:
        sys = (
            "You validate whether fetched documentation matches "
            "the intended tool. Reply YES or NO only."
        )
        raw = smart_generate("\n\n".join(parts), system=sys)
        return "no" not in raw.strip().lower()[:10]
    except Exception:
        return True


def _build_existing_context(c) -> str | None:
    parts = [getattr(c, k) for k in ("description", "summary", "notes") if getattr(c, k, None)]
    return "\n".join(parts) if parts else None


def _build_usage_summary(name: str, eagle_ctx: str) -> str:
    if not is_available() or len(eagle_ctx) < 20:
        return eagle_ctx[:500]
    try:
        raw = smart_generate(
            f"Summarize how '{name}' is used in this developer's projects. "
            f"2-3 sentences max.\n\n{eagle_ctx[:1500]}",
            system="Summarize developer tool usage concisely. No preamble.",
        )
        return raw.strip()[:500] if raw.strip() else eagle_ctx[:500]
    except Exception:
        return eagle_ctx[:500]


def _generate_all(
    name: str, docs: str | None, existing_cat: str | None,
    existing_ctx: str | None = None, provider: str | None = None, model: str | None = None,
) -> dict:
    parts: list[str] = []
    if existing_ctx:
        parts.append(f"Existing knowledge (improve on this):\n{existing_ctx}")
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


def enrich_background(
    concept_id: str, mode: str = "auto",
    provider: str | None = None, model: str | None = None,
) -> None:
    conn = get_connection()
    try:
        enrich_concept(conn, concept_id, mode=mode, provider=provider, model=model)
    except Exception:
        log.exception("Background enrichment failed for %s", concept_id)
        with contextlib.suppress(Exception):
            _set_status(conn, concept_id, None)
    finally:
        conn.close()
