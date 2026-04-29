from __future__ import annotations

import struct
from unittest.mock import MagicMock, patch

import httpx
import pytest

from nexus.ai import cosine_similarity, embed, generate, is_available


class TestIsAvailable:
    def test_available(self):
        mock_resp = MagicMock(status_code=200)
        with patch("nexus.ai.httpx.get", return_value=mock_resp):
            assert is_available() is True

    def test_unavailable(self):
        with patch("nexus.ai.httpx.get", side_effect=httpx.ConnectError("")):
            assert is_available() is False


class TestGenerate:
    def test_returns_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Hello world"}
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.ai.httpx.post", return_value=mock_resp):
            result = generate("test prompt")
            assert result == "Hello world"

    def test_passes_system_prompt(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "ok"}
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.ai.httpx.post", return_value=mock_resp) as mock_post:
            generate("test", system="Be brief")
            payload = mock_post.call_args[1]["json"]
            assert payload["system"] == "Be brief"


class TestEmbed:
    def test_returns_packed_bytes(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embeddings": [[1.0, 2.0, 3.0]]}
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.ai.httpx.post", return_value=mock_resp):
            result = embed("test text")
            assert result is not None
            values = struct.unpack("3f", result)
            assert values == pytest.approx((1.0, 2.0, 3.0))

    def test_returns_none_on_empty(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embeddings": [[]]}
        mock_resp.raise_for_status = MagicMock()
        with patch("nexus.ai.httpx.post", return_value=mock_resp):
            assert embed("test") is None

    def test_returns_none_on_error(self):
        with patch("nexus.ai.httpx.post", side_effect=httpx.HTTPError("")):
            assert embed("test") is None


class TestEmbeddingOps:
    def test_cosine_similarity_identical(self):
        vec = struct.pack("3f", 1.0, 0.0, 0.0)
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = struct.pack("3f", 1.0, 0.0, 0.0)
        b = struct.pack("3f", 0.0, 1.0, 0.0)
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        a = struct.pack("3f", 1.0, 0.0, 0.0)
        b = struct.pack("3f", 0.0, 0.0, 0.0)
        assert cosine_similarity(a, b) == 0.0
