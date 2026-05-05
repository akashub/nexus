from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from nexus.db import (
    add_project,
    count_concepts,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from nexus.graph_helpers import compute_project_edges
from nexus.server import ConnDep, ProjectCreate, ProjectUpdate, project_dict

log = logging.getLogger(__name__)

router = APIRouter()

_scan_status: dict[str, str | None] = {}


@router.get("/projects")
def list_projects_route(conn: ConnDep):
    return [project_dict(p) for p in list_projects(conn)]


@router.get("/projects/{project_id}")
def get_project_route(project_id: str, conn: ConnDep):
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    d = project_dict(p)
    d["concept_count"] = count_concepts(conn, project_id=p.id)
    return d


@router.post("/projects", status_code=201)
def create_project_route(body: ProjectCreate, conn: ConnDep):
    existing = get_project(conn, body.name)
    if existing:
        raise HTTPException(409, f"Project already exists: {body.name}")
    return project_dict(add_project(conn, body.name, path=body.path, description=body.description))


@router.put("/projects/{project_id}")
def update_project_route(project_id: str, body: ProjectUpdate, conn: ConnDep):
    if not get_project(conn, project_id):
        raise HTTPException(404, f"Project not found: {project_id}")
    fields = body.model_dump(exclude_none=True)
    if not fields:
        return project_dict(get_project(conn, project_id))
    return project_dict(update_project(conn, project_id, **fields))


@router.delete("/projects/{project_id}")
def delete_project_route(project_id: str, conn: ConnDep):
    if not get_project(conn, project_id):
        raise HTTPException(404, f"Project not found: {project_id}")
    delete_project(conn, project_id)
    return {"deleted": project_id}


@router.get("/projects/{project_id}/gaps")
def gaps_route(project_id: str, conn: ConnDep):
    from nexus.gaps import detect_gaps
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    return detect_gaps(conn, project_id=p.id)


@router.get("/projects/{project_id}/expertise")
def expertise_route(project_id: str, conn: ConnDep):
    from nexus.expertise import classify_expertise
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    return classify_expertise(conn, project_id).to_dict()


@router.post("/projects/{project_id}/scan")
def scan_project_route(
    project_id: str, conn: ConnDep, background_tasks: BackgroundTasks,
):
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    if not p.path:
        raise HTTPException(400, "Project has no path set")

    _scan_status[project_id] = "scanning_dependencies"

    def _run_scan():
        from pathlib import Path

        from nexus.db import get_connection
        from nexus.scanner import scan_project
        from nexus.sync import sync_scan_results
        scan_conn = get_connection()
        try:
            result = scan_project(Path(p.path))
            _scan_status[project_id] = "syncing_results"
            sync_scan_results(scan_conn, p.path, result)
            import time
            _scan_status[project_id] = "done"
            time.sleep(5)
        except Exception:
            log.exception("Scan failed for project %s", project_id)
        finally:
            scan_conn.close()
            _scan_status.pop(project_id, None)

    background_tasks.add_task(_run_scan)
    return {"status": "scanning", "project_id": project_id}


@router.get("/projects/{project_id}/scan-status")
def scan_status_route(project_id: str):
    return {"status": _scan_status.get(project_id)}


@router.post("/projects/{project_id}/replicate")
def replicate_project_route(
    project_id: str, conn: ConnDep, context: str | None = Query(default=None),
):
    from nexus.replicate import generate_setup_script, list_installable
    if not get_project(conn, project_id):
        raise HTTPException(404, f"Project not found: {project_id}")
    return {
        "script": generate_setup_script(conn, project_id, context_query=context),
        "installable": list_installable(conn, project_id),
    }


@router.post("/projects/{project_id}/compact")
def compact_project_route(
    project_id: str, conn: ConnDep, dry_run: bool = Query(default=False),
):
    from nexus.compact import compact_project
    if not get_project(conn, project_id):
        raise HTTPException(404, f"Project not found: {project_id}")
    stats = compact_project(conn, project_id, dry_run=dry_run)
    return {
        "merged": stats.merged, "stale_removed": stats.stale_removed,
        "edges_deduped": stats.edges_deduped, "dry_run": dry_run,
    }


@router.post("/projects/{project_id}/infer-relationships")
def infer_relationships_route(
    project_id: str, conn: ConnDep, background_tasks: BackgroundTasks,
):
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")

    def _run_infer():
        from nexus.db import get_connection
        from nexus.infer import infer_relationships
        infer_conn = get_connection()
        try:
            infer_relationships(infer_conn, project_id=project_id, verbose=True)
        finally:
            infer_conn.close()

    background_tasks.add_task(_run_infer)
    return {"status": "inferring", "project_id": project_id}


@router.post("/infer-relationships")
def infer_all_relationships_route(conn: ConnDep, background_tasks: BackgroundTasks):
    def _run_infer():
        from nexus.db import get_connection
        from nexus.infer import infer_relationships
        infer_conn = get_connection()
        try:
            infer_relationships(infer_conn, verbose=True)
        finally:
            infer_conn.close()

    background_tasks.add_task(_run_infer)
    return {"status": "inferring"}


@router.get("/graph/global")
def global_graph_route(conn: ConnDep):
    projects = list_projects(conn)
    nodes = []
    for p in projects:
        nodes.append({**project_dict(p), "concept_count": count_concepts(conn, project_id=p.id)})
    edges = compute_project_edges(conn, projects)
    unassigned_count = count_concepts(conn, unassigned=True)
    return {"nodes": nodes, "edges": edges, "unassigned_count": unassigned_count}


