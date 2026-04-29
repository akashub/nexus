from __future__ import annotations

from unittest.mock import patch

from nexus.fetch import DocResult, fetch_context, query_docs, resolve_library


class TestResolveLibrary:
    def test_returns_id(self):
        mcp_text = (
            "- Title: React\n"
            "- Context7-compatible library ID: /facebook/react\n"
            "- Description: A library\n"
        )
        with patch("nexus.fetch._mcp_call", return_value=mcp_text):
            lib_id, doc_url = resolve_library("react")
            assert lib_id == "/facebook/react"

    def test_returns_none_on_empty(self):
        with patch("nexus.fetch._mcp_call", return_value=None):
            lib_id, doc_url = resolve_library("unknown")
            assert lib_id is None

    def test_returns_none_on_no_match(self):
        with patch("nexus.fetch._mcp_call", return_value="No results found"):
            lib_id, doc_url = resolve_library("anything")
            assert lib_id is None


class TestQueryDocs:
    def test_returns_text(self):
        with patch("nexus.fetch._mcp_call", return_value="React is a library."):
            assert query_docs("/facebook/react") == "React is a library."

    def test_returns_none_on_error(self):
        with patch("nexus.fetch._mcp_call", return_value=None):
            assert query_docs("/facebook/react") is None


class TestFetchContext:
    def test_returns_doc_result_when_library_found(self):
        with (
            patch("nexus.fetch.resolve_library",
                  return_value=("/facebook/react", None)),
            patch("nexus.fetch.query_docs", return_value="Docs content"),
        ):
            result = fetch_context("react")
            assert isinstance(result, DocResult)
            assert result.text == "Docs content"
            assert result.library_id == "/facebook/react"

    def test_returns_none_when_library_not_found(self):
        with patch("nexus.fetch.resolve_library", return_value=(None, None)):
            assert fetch_context("unknown") is None
