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
def search_route(
    conn: ConnDep, q: str = Query(min_length=1, max_length=500),
    semantic: bool = False,
):
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


_GITHUB_RELEASE_URL = "https://api.github.com/repos/akashub/nexus/releases/latest"
_version_cache: dict | None = None
_version_ts: float = 0


@router.get("/version")
def version_route():
    import importlib.metadata
    import time

    import httpx

    global _version_cache, _version_ts
    current = importlib.metadata.version("nexus-graph")
    if _version_cache and time.time() - _version_ts < 3600:
        _version_cache["current"] = current
        return _version_cache

    result: dict = {"current": current, "latest": current, "update_available": False}
    try:
        r = httpx.get(_GITHUB_RELEASE_URL, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            latest = data["tag_name"].lstrip("v")
            result["latest"] = latest
            result["update_available"] = latest != current
            assets = data.get("assets", [])

            def find(suffix: str) -> str | None:
                return next(
                    (a["browser_download_url"] for a in assets if a["name"].endswith(suffix)), None,
                )

            result["assets"] = {
                "macos_arm": find("_aarch64.dmg"), "macos_x64": find("_x64.dmg"),
                "windows": find("_x64-setup.exe"), "linux": find(".AppImage"),
            }
            result["release_url"] = data.get("html_url", "")
    except Exception:
        pass
    _version_cache = result
    _version_ts = time.time()
    return result
