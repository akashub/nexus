from __future__ import annotations

import sqlite3
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from nexus.db import (
    add_project,
    delete_project,
    get_project,
    list_concepts,
    list_projects,
    update_project,
)
from nexus.models import Project
from nexus.server import ConnDep, ProjectCreate, ProjectUpdate, project_dict

router = APIRouter()


@router.get("/projects")
def list_projects_route(conn: ConnDep):
    return [project_dict(p) for p in list_projects(conn)]


@router.get("/projects/{project_id}")
def get_project_route(project_id: str, conn: ConnDep):
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    concepts = list_concepts(conn, project_id=p.id, limit=10000)
    d = project_dict(p)
    d["concept_count"] = len(concepts)
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


@router.post("/projects/{project_id}/scan")
def scan_project_route(
    project_id: str, conn: ConnDep, background_tasks: BackgroundTasks,
):
    p = get_project(conn, project_id)
    if not p:
        raise HTTPException(404, f"Project not found: {project_id}")
    if not p.path:
        raise HTTPException(400, "Project has no path set")

    def _run_scan():
        from pathlib import Path

        from nexus.db import get_connection
        from nexus.scanner import scan_project
        from nexus.sync import sync_scan_results
        scan_conn = get_connection()
        try:
            result = scan_project(Path(p.path))
            sync_scan_results(scan_conn, p.path, result)
        finally:
            scan_conn.close()

    background_tasks.add_task(_run_scan)
    return {"status": "scanning", "project_id": project_id}


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


@router.get("/graph/global")
def global_graph_route(conn: ConnDep):
    projects = list_projects(conn)
    nodes = []
    for p in projects:
        count = len(list_concepts(conn, project_id=p.id, limit=10000))
        nodes.append({**project_dict(p), "concept_count": count})
    edges = _compute_project_edges(conn, projects)
    unassigned = list_concepts(conn, limit=10000)
    unassigned_count = sum(1 for c in unassigned if not c.project_id)
    return {"nodes": nodes, "edges": edges, "unassigned_count": unassigned_count}


def _compute_project_edges(
    conn: sqlite3.Connection, projects: list[Project],
) -> list[dict]:
    concept_projects: dict[str, set[str]] = defaultdict(set)
    for p in projects:
        for c in list_concepts(conn, project_id=p.id, limit=10000):
            concept_projects[c.name.lower()].add(p.id)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for _name, pids in concept_projects.items():
        pids_list = sorted(pids)
        for i, a in enumerate(pids_list):
            for b in pids_list[i + 1:]:
                pair_counts[(a, b)] += 1
    return [
        {"source_id": a, "target_id": b, "weight": count, "relationship": "shared_deps"}
        for (a, b), count in pair_counts.items() if count >= 2
    ]
