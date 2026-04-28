from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from nexus.fetch import fetch_context, fetch_web, query_docs, resolve_library


class TestResolveLibrary:
    def test_returns_id(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "lib-123"}]
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.fetch.httpx.get", return_value=mock_resp):
            assert resolve_library("react") == "lib-123"

    def test_returns_none_on_empty(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.fetch.httpx.get", return_value=mock_resp):
            assert resolve_library("unknown") is None

    def test_returns_none_on_error(self):
        with patch("nexus.fetch.httpx.get", side_effect=httpx.HTTPError("")):
            assert resolve_library("anything") is None


class TestQueryDocs:
    def test_returns_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"text": "React is a library."}
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.fetch.httpx.get", return_value=mock_resp):
            assert query_docs("lib-123") == "React is a library."

    def test_returns_none_on_error(self):
        with patch("nexus.fetch.httpx.get", side_effect=httpx.HTTPError("")):
            assert query_docs("lib-123") is None


class TestFetchWeb:
    def test_returns_plain_text(self):
        mock_resp = MagicMock()
        mock_resp.text = "Plain content"
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.fetch.httpx.get", return_value=mock_resp):
            assert fetch_web("http://example.com") == "Plain content"

    def test_strips_html(self):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Hello</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.fetch.httpx.get", return_value=mock_resp):
            result = fetch_web("http://example.com")
            assert result is not None
            assert "<html" not in result
            assert "Hello" in result

    def test_returns_none_on_error(self):
        with patch("nexus.fetch.httpx.get", side_effect=httpx.HTTPError("")):
            assert fetch_web("http://fail.com") is None


class TestFetchContext:
    def test_returns_docs_when_library_found(self):
        with (
            patch("nexus.fetch.resolve_library", return_value="lib-123"),
            patch("nexus.fetch.query_docs", return_value="Docs content"),
        ):
            assert fetch_context("react") == "Docs content"

    def test_returns_none_when_library_not_found(self):
        with patch("nexus.fetch.resolve_library", return_value=None):
            assert fetch_context("unknown") is None
