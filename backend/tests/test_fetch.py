from __future__ import annotations

from unittest.mock import patch

from nexus.fetch import DocResult, fetch_context, fetch_quickstart, resolve_library


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


class TestFetchQuickstart:
    def test_returns_text(self):
        with patch("nexus.fetch._mcp_call", return_value="React is a library."):
            assert fetch_quickstart("/facebook/react") == "React is a library."

    def test_returns_none_on_error(self):
        with patch("nexus.fetch._mcp_call", return_value=None):
            assert fetch_quickstart("/facebook/react") is None


class TestFetchContext:
    def test_returns_doc_result_when_context7_succeeds(self):
        result = DocResult(
            text="Docs content",
            library_id="/facebook/react",
            source="context7",
        )
        with patch.dict(
            "nexus.fetch._FETCHERS",
            {"context7": lambda _name: result},
        ):
            got = fetch_context("react")
            assert isinstance(got, DocResult)
            assert got.text == "Docs content"
            assert got.library_id == "/facebook/react"
            assert got.source == "context7"

    def test_returns_none_when_no_source_matches(self):
        with patch.dict(
            "nexus.fetch._FETCHERS",
            {k: lambda _name: None for k in ("context7", "pypi", "npm", "github", "libraries")},
        ):
            assert fetch_context("unknown") is None

    def test_mode_dispatches_to_single_source(self):
        result = DocResult(text="PyPI info", source="pypi")
        with patch.dict("nexus.fetch._FETCHERS", {"pypi": lambda _name: result}):
            got = fetch_context("requests", mode="pypi")
            assert got is not None
            assert got.source == "pypi"
