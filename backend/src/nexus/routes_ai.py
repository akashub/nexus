from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from nexus.cli_ask import _build_context, _find_related
from nexus.db import add_conversation, list_concepts, search_fts
from nexus.server import AskRequest, ConnDep, concept_dict

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
def search_route(conn: ConnDep, q: str = Query(max_length=500), semantic: bool = False):
    if semantic:
        from nexus.ai import cosine_similarity, embed
        qvec = embed(q)
        if qvec:
            scored = [
                (c, cosine_similarity(qvec, c.embedding))
                for c in list_concepts(conn, limit=200) if c.embedding
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [concept_dict(c) for c, _score in scored[:10] if _score > 0.3]
    return [concept_dict(c) for c in search_fts(conn, q)]


@router.post("/ask")
def ask_route(body: AskRequest, conn: ConnDep):
    from nexus.ai import generate_stream, is_available
    if not is_available():
        raise HTTPException(503, "Ollama is not running")
    related = _find_related(conn, body.question)
    ctx = _build_context(conn, related)
    prompt = (
        f"Knowledge graph context:\n{ctx}\n\n"
        f"Question: {body.question}\n\nAnswer using the context above."
    )
    concept_ids = [c.id for c in related]

    def stream():
        chunks: list[str] = []
        try:
            for token in generate_stream(prompt):
                chunks.append(token)
                yield token
        except Exception:
            log.exception("AI generation failed for question: %.100s", body.question)
            return
        try:
            from nexus.db import get_connection
            save_conn = get_connection()
            try:
                add_conversation(save_conn, body.question, "".join(chunks), concept_ids)
            finally:
                save_conn.close()
        except Exception:
            log.exception("Failed to save conversation for question: %.100s", body.question)

    return StreamingResponse(stream(), media_type="text/plain")


@router.get("/ai/status")
def ai_status_route():
    from nexus.ai import is_available
    return {"available": is_available()}
