from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse

from nexus.db import count_edges, get_all_edges, list_concepts, list_projects
from nexus.server import ConnDep, concept_dict, edge_dict

log = logging.getLogger(__name__)

router = APIRouter()

_enrich_status: dict[str, str | None] = {}


@router.get("/graph")
def graph_route(conn: ConnDep, project_id: str | None = None):
    concepts = list_concepts(conn, limit=500, project_id=project_id)
    all_edges = get_all_edges(conn)
    node_ids = {c.id for c in concepts}
    edges = [e for e in all_edges if e.source_id in node_ids and e.target_id in node_ids]
    connected = {eid for e in edges for eid in (e.source_id, e.target_id)}
    nodes = []
    for c in concepts:
        d = concept_dict(c)
        known = c.description and c.embedding and c.id in connected
        d["expertise_level"] = "known_well" if known else "seen"
        nodes.append(d)
    return {"nodes": nodes, "edges": [edge_dict(e) for e in edges]}


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


@router.get("/graph/export")
def export_graph_route(
    conn: ConnDep, project_id: str | None = None,
    fmt: str = Query(default="markdown", alias="format"),
):
    from nexus.export import export_graph
    concepts = list_concepts(conn, limit=500, project_id=project_id)
    node_ids = {c.id for c in concepts}
    edges = [e for e in get_all_edges(conn) if e.source_id in node_ids and e.target_id in node_ids]
    if fmt == "markdown":
        md = export_graph(concepts, edges, fmt="markdown")
        return PlainTextResponse(md, media_type="text/markdown")
    return export_graph(concepts, edges, fmt="json")


@router.post("/concepts/enrich-bulk")
def bulk_enrich_route(
    conn: ConnDep, background_tasks: BackgroundTasks,
    project_id: str | None = None,
):
    unenriched = [
        c for c in list_concepts(conn, limit=500, project_id=project_id)
        if not c.description
    ]
    if not unenriched:
        return {"status": "done", "count": 0}
    _enrich_status["bulk"] = f"enriching (0/{len(unenriched)})"

    def _run():
        from nexus.db import get_connection, get_project
        from nexus.enrich import enrich_concept
        from nexus.pipeline import rebuild_project_edges
        ec = get_connection()
        try:
            for i, c in enumerate(unenriched):
                _enrich_status["bulk"] = f"enriching ({i + 1}/{len(unenriched)})"
                try:
                    enrich_concept(ec, c.id)
                except Exception:
                    log.debug("Bulk enrich failed for %s", c.name, exc_info=True)
            if project_id:
                _enrich_status["bulk"] = "rebuilding edges"
                p = get_project(ec, project_id)
                rebuild_project_edges(
                    ec, project_id,
                    project_path=p.path if p else None,
                    project_name=p.name if p else None,
                )
            _enrich_status["bulk"] = "done"
        except Exception:
            log.exception("Bulk enrich failed")
        finally:
            ec.close()
            _enrich_status.pop("bulk", None)

    background_tasks.add_task(_run)
    return {"status": "enriching", "count": len(unenriched)}


@router.get("/enrich-status")
def enrich_status_route():
    return {"status": _enrich_status.get("bulk")}
