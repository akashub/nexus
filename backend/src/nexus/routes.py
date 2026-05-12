from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from nexus.db import (
    add_concept,
    add_edge,
    delete_concept,
    delete_edge,
    get_concept,
    get_edges,
    list_concepts,
    list_conversations,
    update_concept,
)
from nexus.server import (
    ConceptCreate,
    ConceptUpdate,
    ConnDep,
    EdgeCreate,
    concept_dict,
    edge_dict,
)

router = APIRouter()


@router.get("/concepts")
def list_concepts_route(
    conn: ConnDep, category: str | None = None, limit: int = Query(default=100, ge=1, le=1000),
    project_id: str | None = None,
):
    concepts = list_concepts(conn, limit=limit, category=category, project_id=project_id)
    return [concept_dict(c) for c in concepts]


@router.get("/concepts/{concept_id}")
def get_concept_route(concept_id: str, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    return concept_dict(c)


@router.post("/concepts", status_code=201)
def create_concept_route(body: ConceptCreate, conn: ConnDep, background_tasks: BackgroundTasks):
    existing = get_concept(conn, body.name)
    if existing:
        raise HTTPException(409, f"Concept already exists: {body.name}")
    c = add_concept(
        conn, body.name, category=body.category, tags=body.tags,
        notes=body.notes, project_id=body.project_id,
    )
    if not body.no_enrich:
        from nexus.enrich import enrich_background
        background_tasks.add_task(enrich_background, c.id, body.source_mode)
    return concept_dict(c)


@router.put("/concepts/{concept_id}")
def update_concept_route(concept_id: str, body: ConceptUpdate, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    fields = body.model_dump(exclude_none=True)
    if not fields:
        return concept_dict(c)
    return concept_dict(update_concept(conn, concept_id, **fields))


@router.delete("/concepts/{concept_id}")
def delete_concept_route(concept_id: str, conn: ConnDep):
    if not get_concept(conn, concept_id):
        raise HTTPException(404, f"Concept not found: {concept_id}")
    delete_concept(conn, concept_id)
    return {"deleted": concept_id}


@router.get("/edges")
def list_edges_route(conn: ConnDep, concept_id: str = Query()):
    return [edge_dict(e) for e in get_edges(conn, concept_id)]


@router.post("/edges", status_code=201)
def create_edge_route(body: EdgeCreate, conn: ConnDep):
    src, tgt = get_concept(conn, body.source_id), get_concept(conn, body.target_id)
    if not src:
        raise HTTPException(404, f"Source concept not found: {body.source_id}")
    if not tgt:
        raise HTTPException(404, f"Target concept not found: {body.target_id}")
    edge = add_edge(conn, src.id, tgt.id, body.relationship, description=body.description)
    return edge_dict(edge)


@router.delete("/edges/{edge_id}")
def delete_edge_route(edge_id: str, conn: ConnDep):
    if not delete_edge(conn, edge_id):
        raise HTTPException(404, f"Edge not found: {edge_id}")
    return {"deleted": edge_id}


@router.get("/conversations")
def list_conversations_route(conn: ConnDep, limit: int = Query(default=20, ge=1, le=100)):
    return [{"id": c.id, "question": c.question, "answer": c.answer,
             "created_at": c.created_at} for c in list_conversations(conn, limit=limit)]


@router.get("/concepts/{concept_id}/context")
def concept_context_route(concept_id: str, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    project = None
    if c.project_id:
        from nexus.db import get_project
        project = get_project(conn, c.project_id)
    from nexus.context import (
        get_ai_tool_memories,
        get_claude_memories,
        get_install_commands,
        search_session_context,
        summarize_usage,
    )
    p_name = project.name if project else ""
    p_path = project.path if project else ""
    raw_snippets = search_session_context(p_name, c.name) if p_name else []
    raw_snippets = [s for s in raw_snippets if len(s.strip()) >= 40]
    seen = set()
    raw_snippets = [s for s in raw_snippets if not (s in seen or seen.add(s))]
    installs = get_install_commands(p_name, c.name) if p_name else []
    memories = get_claude_memories(p_path or "")
    memories.extend(get_ai_tool_memories(p_path or ""))
    name_re = re.compile(r'\b' + re.escape(c.name.lower()) + r'\b')
    relevant = [m for m in memories if name_re.search(m["content"].lower())]
    summary = c.usage_summary
    if not summary and raw_snippets:
        summary = summarize_usage(c.name, "\n".join(raw_snippets))
        if summary:
            # Conditional update: only write if still NULL (idempotent under concurrent GETs)
            conn.execute(
                "UPDATE concepts SET usage_summary = ?, updated_at = datetime('now')"
                " WHERE id = ? AND usage_summary IS NULL",
                (summary, c.id),
            )
            conn.commit()
    return {
        "usage_summary": summary or "",
        "raw_context": raw_snippets[:5],
        "install_commands": installs,
        "claude_memories": [m["content"][:300] for m in relevant[:3]],
    }


_SKIP_DIRS = frozenset({
    "Library", "Applications", "Music", "Movies", "Pictures",
    "Documents", "Downloads", "Public", "node_modules", "venv", ".venv",
})


@router.get("/detect-projects")
def detect_projects_route():
    from pathlib import Path
    home = Path.home()
    found: list[dict] = []

    def _scan(d: Path, depth: int) -> None:
        if depth > 3 or len(found) >= 30:
            return
        try:
            for p in d.iterdir():
                if not p.is_dir() or p.name.startswith(".") or p.name in _SKIP_DIRS:
                    continue
                if (p / ".git").is_dir():
                    found.append({"name": p.name, "path": str(p)})
                elif depth < 3:
                    _scan(p, depth + 1)
        except PermissionError:
            pass

    _scan(home, 1)
    found.sort(key=lambda x: x["name"])
    return found


@router.post("/concepts/{concept_id}/enrich")
def enrich_concept_route(
    concept_id: str, conn: ConnDep, background_tasks: BackgroundTasks,
    mode: str = "auto", provider: str | None = None, model: str | None = None,
):
    if not get_concept(conn, concept_id):
        raise HTTPException(404, f"Concept not found: {concept_id}")
    from nexus.enrich import enrich_background
    background_tasks.add_task(enrich_background, concept_id, mode, provider, model)
    return {"status": "enriching", "concept_id": concept_id, "mode": mode}
