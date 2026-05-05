"""Tests for AI provider config file management."""

from __future__ import annotations

from unittest.mock import patch

from nexus.ai_config import delete, get, load, masked, resolve, save


def test_load_missing_file(tmp_path):
    with patch("nexus.ai_config._CONFIG_PATH", tmp_path / "nope.json"):
        assert load() == {}


def test_save_and_load(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "sk-test-123", "model": "claude-sonnet-4-6"})
        cfg = load()
        assert cfg["anthropic"]["api_key"] == "sk-test-123"
        assert cfg["anthropic"]["model"] == "claude-sonnet-4-6"


def test_save_sets_default_model(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("openai", {"api_key": "sk-xyz"})
        assert load()["openai"]["model"] == "gpt-4o-mini"


def test_save_strips_unknown_fields(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "sk-1", "bogus": "val"})
        assert "bogus" not in load()["anthropic"]


def test_delete_removes_provider(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "sk-1"})
        save("openai", {"api_key": "sk-2"})
        delete("anthropic")
        cfg = load()
        assert "anthropic" not in cfg
        assert "openai" in cfg


def test_delete_last_removes_file(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "sk-1"})
        delete("anthropic")
        assert not path.exists()


def test_get_specific_provider(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("openai", {"api_key": "sk-abc"})
        assert get("openai")["api_key"] == "sk-abc"
        assert get("anthropic") == {}


def test_masked_hides_keys(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "sk-ant-1234567890"})
        m = masked()
        assert m["anthropic"]["api_key"].startswith("sk-a")
        assert m["anthropic"]["api_key"].endswith("7890")
        assert "1234" not in m["anthropic"]["api_key"]


def test_resolve_prefers_env(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "file-key"})
        env = {"NEXUS_CLOUD_PROVIDER": "anthropic", "NEXUS_CLOUD_API_KEY": "env-key"}
        with patch.dict("os.environ", env):
            creds = resolve("anthropic")
            assert creds["api_key"] == "env-key"


def test_resolve_falls_back_to_file(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("anthropic", {"api_key": "file-key"})
        with patch.dict("os.environ", {}, clear=False):
            creds = resolve("anthropic")
            assert creds["api_key"] == "file-key"


def test_resolve_gemini_env(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        env = {"NEXUS_GEMINI_API_KEY": "gem-key"}
        with patch.dict("os.environ", env):
            creds = resolve("gemini")
            assert creds["api_key"] == "gem-key"


def test_resolve_gemini_file(tmp_path):
    path = tmp_path / "cfg.json"
    with patch("nexus.ai_config._CONFIG_PATH", path):
        save("gemini", {"api_key": "gem-file"})
        with patch.dict("os.environ", {}, clear=False):
            creds = resolve("gemini")
            assert creds["api_key"] == "gem-file"
