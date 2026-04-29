from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from nexus.db import (
    add_concept,
    add_conversation,
    add_edge,
    count_edges,
    delete_concept,
    delete_edge,
    get_all_edges,
    get_concept,
    get_edges,
    list_concepts,
    search_fts,
    update_concept,
)
from nexus.server import (
    AskRequest,
    ConceptCreate,
    ConceptUpdate,
    ConnDep,
    EdgeCreate,
    concept_to_dict,
    edge_to_dict,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/concepts")
def list_concepts_route(
    conn: ConnDep, category: str | None = None, limit: int = Query(default=100, ge=1, le=1000),
):
    concepts = list_concepts(conn, limit=limit, category=category)
    return [concept_to_dict(c) for c in concepts]


@router.get("/concepts/{concept_id}")
def get_concept_route(concept_id: str, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    return concept_to_dict(c)


@router.post("/concepts", status_code=201)
def create_concept_route(body: ConceptCreate, conn: ConnDep, background_tasks: BackgroundTasks):
    existing = get_concept(conn, body.name)
    if existing:
        raise HTTPException(409, f"Concept already exists: {body.name}")
    c = add_concept(conn, body.name, category=body.category, tags=body.tags, notes=body.notes)
    if not body.no_enrich:
        background_tasks.add_task(_enrich_background, c.id)
    return concept_to_dict(c)


def _enrich_background(concept_id: str) -> None:
    from nexus.db import get_connection
    from nexus.enrich import enrich_concept

    conn = get_connection()
    try:
        enrich_concept(conn, concept_id)
    except Exception:
        log.exception("Background enrichment failed for concept %s", concept_id)
    finally:
        conn.close()


@router.put("/concepts/{concept_id}")
def update_concept_route(concept_id: str, body: ConceptUpdate, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    fields = body.model_dump(exclude_none=True)
    if not fields:
        return concept_to_dict(c)
    updated = update_concept(conn, concept_id, **fields)
    return concept_to_dict(updated)


@router.delete("/concepts/{concept_id}")
def delete_concept_route(concept_id: str, conn: ConnDep):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    delete_concept(conn, concept_id)
    return {"deleted": concept_id}


@router.get("/edges")
def list_edges_route(conn: ConnDep, concept_id: str | None = None):
    if not concept_id:
        raise HTTPException(400, "concept_id query parameter required")
    edges = get_edges(conn, concept_id)
    return [edge_to_dict(e) for e in edges]


@router.post("/edges", status_code=201)
def create_edge_route(body: EdgeCreate, conn: ConnDep):
    src = get_concept(conn, body.source_id)
    tgt = get_concept(conn, body.target_id)
    if not src:
        raise HTTPException(404, f"Source concept not found: {body.source_id}")
    if not tgt:
        raise HTTPException(404, f"Target concept not found: {body.target_id}")
    edge = add_edge(conn, src.id, tgt.id, body.relationship, description=body.description)
    return edge_to_dict(edge)


@router.delete("/edges/{edge_id}")
def delete_edge_route(edge_id: str, conn: ConnDep):
    if not delete_edge(conn, edge_id):
        raise HTTPException(404, f"Edge not found: {edge_id}")
    return {"deleted": edge_id}


@router.get("/search")
def search_route(conn: ConnDep, q: str = Query(max_length=500), semantic: bool = False):
    if semantic:
        from nexus.ai import cosine_similarity, embed

        qvec = embed(q)
        if qvec:
            all_c = list_concepts(conn, limit=200)
            scored = [(c, cosine_similarity(qvec, c.embedding)) for c in all_c if c.embedding]
            scored = [(c, s) for c, s in scored if s > 0.3]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [concept_to_dict(c) for c, _ in scored[:10]]
    results = search_fts(conn, q)
    return [concept_to_dict(c) for c in results]


@router.post("/ask")
def ask_route(body: AskRequest, conn: ConnDep):
    from nexus.ai import generate, is_available

    if not is_available():
        raise HTTPException(503, "Ollama is not running")
    related = search_fts(conn, body.question)[:5]
    ctx = "\n".join(
        f"- {c.name}: {c.description}" if c.description else f"- {c.name}"
        for c in related
    ) or "No relevant concepts found."
    prompt = (
        f"Knowledge graph context:\n{ctx}\n\n"
        f"Question: {body.question}\n\nAnswer using the context above."
    )
    try:
        answer = generate(prompt)
    except Exception as exc:
        log.exception("AI generation failed for question: %.100s", body.question)
        raise HTTPException(503, "AI generation failed — is Ollama running?") from exc
    concept_ids = [c.id for c in related]
    add_conversation(conn, body.question, answer, concept_ids)
    return {"question": body.question, "answer": answer, "concepts_used": concept_ids}


@router.get("/graph")
def graph_route(conn: ConnDep):
    concepts = list_concepts(conn, limit=500)
    nodes = [concept_to_dict(c) for c in concepts]
    edges = [edge_to_dict(e) for e in get_all_edges(conn)]
    return {"nodes": nodes, "edges": edges}


@router.get("/stats")
def stats_route(conn: ConnDep):
    concepts = list_concepts(conn, limit=10000)
    categories: dict[str, int] = {}
    for c in concepts:
        cat = c.category or "uncategorized"
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "concept_count": len(concepts),
        "edge_count": count_edges(conn),
        "categories": categories,
    }


@router.post("/concepts/{concept_id}/enrich")
def enrich_concept_route(concept_id: str, conn: ConnDep, background_tasks: BackgroundTasks):
    c = get_concept(conn, concept_id)
    if not c:
        raise HTTPException(404, f"Concept not found: {concept_id}")
    background_tasks.add_task(_enrich_background, concept_id)
    return {"status": "enriching", "concept_id": concept_id}


@router.get("/ai/status")
def ai_status_route():
    from nexus.ai import is_available
    return {"available": is_available()}
