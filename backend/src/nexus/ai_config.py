"""AI provider config — file-based credentials at ~/.nexus/ai_config.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_CONFIG_PATH = Path.home() / ".nexus" / "ai_config.json"

_PROVIDERS = {
    "anthropic": {"fields": ["api_key", "model"], "default_model": "claude-sonnet-4-6"},
    "openai": {"fields": ["api_key", "model"], "default_model": "gpt-4o-mini"},
    "gemini": {
        "fields": ["api_key", "model", "project", "location"],
        "default_model": "gemini-2.5-flash",
    },
}


def load() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except Exception:
        log.debug("Failed to read ai config", exc_info=True)
        return {}


def get(provider: str) -> dict:
    return load().get(provider, {})


def save(provider: str, settings: dict) -> None:
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = load()
    clean = {k: v for k, v in settings.items() if k in _PROVIDERS[provider]["fields"] and v}
    if not clean.get("model"):
        clean["model"] = _PROVIDERS[provider]["default_model"]
    cfg[provider] = clean
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def delete(provider: str) -> None:
    cfg = load()
    cfg.pop(provider, None)
    if cfg:
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    elif _CONFIG_PATH.exists():
        _CONFIG_PATH.unlink()


def masked() -> dict:
    cfg = load()
    result = {}
    for p, settings in cfg.items():
        masked_settings = {}
        for k, v in settings.items():
            if k == "api_key" and v:
                masked_settings[k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "****"
            else:
                masked_settings[k] = v
        result[p] = masked_settings
    return result


def resolve(provider: str) -> dict:
    """Get credentials for a provider: env vars first, then config file."""
    import os
    if provider == "gemini":
        return _resolve_gemini()
    env_provider = os.environ.get("NEXUS_CLOUD_PROVIDER", "")
    env_key = os.environ.get("NEXUS_CLOUD_API_KEY", "")
    if env_provider == provider and env_key:
        return {
            "api_key": env_key,
            "model": os.environ.get("NEXUS_CLOUD_MODEL", "")
            or _PROVIDERS[provider]["default_model"],
        }
    file_cfg = get(provider)
    if file_cfg.get("api_key"):
        return file_cfg
    return {}


def _resolve_gemini() -> dict:
    import os
    api_key = os.environ.get("NEXUS_GEMINI_API_KEY", "")
    project = os.environ.get("NEXUS_GEMINI_PROJECT", "")
    if api_key or project:
        return {
            "api_key": api_key,
            "model": os.environ.get("NEXUS_GEMINI_MODEL", "gemini-2.5-flash"),
            "project": project,
            "location": os.environ.get("NEXUS_GEMINI_LOCATION", "us-central1"),
        }
    file_cfg = get("gemini")
    if file_cfg.get("api_key") or file_cfg.get("project"):
        return file_cfg
    return {}
