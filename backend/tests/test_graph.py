from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from nexus.db import get_connection, init_db
from nexus.server import app


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    def override_conn():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    from nexus.server import _get_conn
    app.dependency_overrides[_get_conn] = override_conn
    return TestClient(app)


def _add(client: TestClient, name: str, **kw) -> dict:
    r = client.post("/api/concepts", json={"name": name, "no_enrich": True, **kw})
    assert r.status_code == 201
    return r.json()


class TestGraphRoute:
    def test_graph_returns_nodes_and_edges(self, tmp_path):
        c = _client(tmp_path)
        _add(c, "React")
        r = c.get("/api/graph")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data and "edges" in data

    def test_expertise_level_on_nodes(self, tmp_path):
        c = _client(tmp_path)
        _add(c, "React")
        r = c.get("/api/graph")
        node = r.json()["nodes"][0]
        assert node["expertise_level"] == "seen"

    def test_export_markdown(self, tmp_path):
        c = _client(tmp_path)
        _add(c, "React", category="framework")
        r = c.get("/api/graph/export?format=markdown")
        assert r.status_code == 200
        assert "## React (framework)" in r.text

    def test_export_json(self, tmp_path):
        c = _client(tmp_path)
        _add(c, "React")
        r = c.get("/api/graph/export?format=json")
        assert r.status_code == 200
        data = r.json()
        assert data["concepts"][0]["name"] == "React"

    def test_enrich_status_empty(self, tmp_path):
        c = _client(tmp_path)
        r = c.get("/api/enrich-status")
        assert r.status_code == 200
        assert r.json()["status"] is None

    def test_bulk_enrich_no_unenriched(self, tmp_path):
        c = _client(tmp_path)
        concept = _add(c, "React")
        c.put(f"/api/concepts/{concept['id']}", json={"description": "A library"})
        r = c.post("/api/concepts/enrich-bulk")
        assert r.status_code == 200
        assert r.json()["status"] == "done"
        assert r.json()["count"] == 0

    def teardown_method(self):
        app.dependency_overrides.clear()
