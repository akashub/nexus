from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexus.db import get_connection, init_db
from nexus.server import app


@pytest.fixture()
def client(tmp_path: Path):
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
    yield TestClient(app)
    app.dependency_overrides.clear()


def _add(client, name: str, **kw) -> dict:
    body = {"name": name, "no_enrich": True, **kw}
    r = client.post("/api/concepts", json=body)
    assert r.status_code == 201
    return r.json()


class TestConceptsCRUD:
    def test_create_and_get(self, client):
        data = _add(client, "React", category="framework")
        assert data["name"] == "React" and data["category"] == "framework"
        r = client.get(f"/api/concepts/{data['id']}")
        assert r.status_code == 200 and r.json()["name"] == "React"

    def test_create_duplicate(self, client):
        _add(client, "React")
        r = client.post("/api/concepts", json={"name": "React", "no_enrich": True})
        assert r.status_code == 409

    def test_list(self, client):
        _add(client, "React")
        _add(client, "Vue")
        r = client.get("/api/concepts")
        assert r.status_code == 200 and len(r.json()) == 2

    def test_list_category_filter(self, client):
        _add(client, "React", category="framework")
        _add(client, "SQLite", category="concept")
        r = client.get("/api/concepts?category=framework")
        assert len(r.json()) == 1

    def test_update(self, client):
        data = _add(client, "React")
        r = client.put(f"/api/concepts/{data['id']}", json={"category": "framework"})
        assert r.status_code == 200 and r.json()["category"] == "framework"

    def test_delete(self, client):
        data = _add(client, "React")
        r = client.delete(f"/api/concepts/{data['id']}")
        assert r.status_code == 200
        r2 = client.get(f"/api/concepts/{data['id']}")
        assert r2.status_code == 404

    def test_get_not_found(self, client):
        assert client.get("/api/concepts/fake-id").status_code == 404


class TestEdgesCRUD:
    def test_create_and_list(self, client):
        a = _add(client, "A")
        b = _add(client, "B")
        r = client.post("/api/edges", json={
            "source_id": a["id"], "target_id": b["id"], "relationship": "uses",
        })
        assert r.status_code == 201
        edges = client.get(f"/api/edges?concept_id={a['id']}").json()
        assert len(edges) == 1

    def test_delete_edge(self, client):
        a, b = _add(client, "A"), _add(client, "B")
        edge = client.post("/api/edges", json={
            "source_id": a["id"], "target_id": b["id"], "relationship": "uses",
        }).json()
        r = client.delete(f"/api/edges/{edge['id']}")
        assert r.status_code == 200

    def test_edges_missing_param(self, client):
        assert client.get("/api/edges").status_code == 400


class TestSearch:
    def test_fts_search(self, client):
        _add(client, "React")
        r = client.get("/api/search?q=React")
        assert r.status_code == 200 and len(r.json()) >= 1

    def test_search_no_results(self, client):
        r = client.get("/api/search?q=nonexistent")
        assert r.status_code == 200 and r.json() == []


class TestAsk:
    def test_ask_ollama_unavailable(self, client):
        with patch("nexus.ai.is_available", return_value=False):
            r = client.post("/api/ask", json={"question": "What is React?"})
            assert r.status_code == 503

    def test_ask_returns_answer(self, client):
        _add(client, "React")
        with (
            patch("nexus.ai.is_available", return_value=True),
            patch("nexus.ai.generate", return_value="React is a UI library."),
        ):
            r = client.post("/api/ask", json={"question": "What is React?"})
            assert r.status_code == 200
            assert "React is a UI library" in r.json()["answer"]


class TestGraphAndStats:
    def test_graph(self, client):
        a, b = _add(client, "A"), _add(client, "B")
        client.post("/api/edges", json={
            "source_id": a["id"], "target_id": b["id"], "relationship": "uses",
        })
        r = client.get("/api/graph")
        assert r.status_code == 200
        data = r.json()
        assert len(data["nodes"]) == 2 and len(data["edges"]) == 1

    def test_stats(self, client):
        _add(client, "React", category="framework")
        _add(client, "SQLite", category="concept")
        r = client.get("/api/stats")
        data = r.json()
        assert data["concept_count"] == 2
        assert data["categories"]["framework"] == 1
