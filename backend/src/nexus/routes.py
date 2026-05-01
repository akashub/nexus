from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from nexus.db import (
    add_concept,
    add_edge,
    count_edges,
    delete_concept,
    delete_edge,
    get_all_edges,
    get_concept,
    get_edges,
    list_concepts,
    list_conversations,
    list_projects,
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


@router.get("/graph")
def graph_route(conn: ConnDep, project_id: str | None = None):
    concepts = list_concepts(conn, limit=500, project_id=project_id)
    nodes = [concept_dict(c) for c in concepts]
    node_ids = {c.id for c in concepts}
    edges = [
        edge_dict(e) for e in get_all_edges(conn)
        if e.source_id in node_ids and e.target_id in node_ids
    ]
    return {"nodes": nodes, "edges": edges}


@router.get("/stats")
def stats_route(conn: ConnDep, project_id: str | None = None):
    concepts = list_concepts(conn, limit=10000, project_id=project_id)
    cats: dict[str, int] = {}
    for c in concepts:
        key = c.category or "uncategorized"
        cats[key] = cats.get(key, 0) + 1
    return {
        "concept_count": len(concepts), "edge_count": count_edges(conn),
        "categories": cats, "project_count": len(list_projects(conn)),
    }


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
        get_claude_memories,
        get_concept_context,
        get_install_commands,
        summarize_usage,
    )
    p_name = project.name if project else ""
    p_path = project.path if project else ""
    usage = get_concept_context(p_name, p_path or "", c.name)
    installs = get_install_commands(p_name, c.name) if p_name else []
    memories = get_claude_memories(p_path or "")
    import re
    name_re = re.compile(r'\b' + re.escape(c.name.lower()) + r'\b')
    relevant = [m for m in memories if name_re.search(m["content"].lower())]
    summary = summarize_usage(c.name, usage)
    return {
        "usage_context": usage,
        "usage_summary": summary,
        "install_commands": installs,
        "claude_memories": [m["content"][:300] for m in relevant[:3]],
    }


@router.post("/concepts/{concept_id}/enrich")
def enrich_concept_route(
    concept_id: str, conn: ConnDep,
    background_tasks: BackgroundTasks, mode: str = "auto",
):
    if not get_concept(conn, concept_id):
        raise HTTPException(404, f"Concept not found: {concept_id}")
    from nexus.enrich import enrich_background
    background_tasks.add_task(enrich_background, concept_id, mode)
    return {"status": "enriching", "concept_id": concept_id, "mode": mode}
