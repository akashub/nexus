from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import patch

from nexus.db import add_concept, get_concept, get_connection, init_db
from nexus.enrich import enrich_concept
from nexus.fetch import DocResult


def _fake_embed(text, **kw):
    return struct.pack("3f", 1.0, 0.5, 0.2)


def _fake_generate(prompt, **kw):
    if "Analyze" in prompt and "JSON" in prompt:
        return (
            '{"description": "A generated description.",'
            ' "summary": "A short summary",'
            ' "category": "framework"}'
        )
    return "A generated description."


class TestEnrichConcept:
    def setup_method(self, tmp_path_factory=None):
        pass

    def _make_conn(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return get_connection(db_path)

    def test_enriches_all_fields(self, tmp_path):
        conn = self._make_conn(tmp_path)
        try:
            c = add_concept(conn, "React")
            with (
                patch("nexus.enrich.is_available", return_value=True),
                patch("nexus.enrich.fetch_context",
                       return_value=DocResult(text="React docs", library_id="lib-1")),
                patch("nexus.enrich.fetch_quickstart", return_value="npm install react"),
                patch("nexus.enrich.generate", side_effect=_fake_generate),
                patch("nexus.enrich.embed", side_effect=_fake_embed),
            ):
                enrich_concept(conn, c.id)
            updated = get_concept(conn, c.id)
            assert updated.description == "A generated description."
            assert updated.summary == "A short summary"
            assert updated.category == "framework"
            assert updated.embedding is not None
        finally:
            conn.close()

    def test_skips_when_ollama_unavailable(self, tmp_path):
        conn = self._make_conn(tmp_path)
        try:
            c = add_concept(conn, "React")
            with patch("nexus.enrich.is_available", return_value=False):
                enrich_concept(conn, c.id)
            updated = get_concept(conn, c.id)
            assert updated.description is None
        finally:
            conn.close()

    def test_preserves_existing_fields(self, tmp_path):
        conn = self._make_conn(tmp_path)
        try:
            c = add_concept(conn, "React", description="Existing", category="devtool")
            with (
                patch("nexus.enrich.is_available", return_value=True),
                patch("nexus.enrich.fetch_context", return_value=None),
                patch("nexus.enrich.generate", side_effect=_fake_generate),
                patch("nexus.enrich.embed", side_effect=_fake_embed),
            ):
                enrich_concept(conn, c.id)
            updated = get_concept(conn, c.id)
            assert updated.description == "A generated description."
            assert updated.category == "devtool"
        finally:
            conn.close()
