from __future__ import annotations

import os
import struct

CLOUD_PROVIDER = os.environ.get("NEXUS_CLOUD_PROVIDER", "")
CLOUD_API_KEY = os.environ.get("NEXUS_CLOUD_API_KEY", "")
CLOUD_MODEL = os.environ.get("NEXUS_CLOUD_MODEL", "")

_DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-6", "openai": "gpt-4o-mini"}


def is_cloud_available() -> bool:
    return bool(CLOUD_PROVIDER and CLOUD_API_KEY)


def _get_model() -> str:
    return CLOUD_MODEL or _DEFAULT_MODELS.get(CLOUD_PROVIDER, "")


def generate_cloud(
    prompt: str, *, system: str | None = None,
) -> str:
    if CLOUD_PROVIDER == "anthropic":
        return _anthropic_generate(prompt, system=system)
    if CLOUD_PROVIDER == "openai":
        return _openai_generate(prompt, system=system)
    raise ValueError(f"Unknown cloud provider: {CLOUD_PROVIDER}")


def _anthropic_generate(prompt: str, *, system: str | None = None) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=CLOUD_API_KEY)
    kwargs: dict = {
        "model": _get_model(),
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def _openai_generate(prompt: str, *, system: str | None = None) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=CLOUD_API_KEY)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=_get_model(), messages=messages, max_tokens=1024,
    )
    return resp.choices[0].message.content or ""


def embed_cloud(text: str) -> bytes | None:
    if CLOUD_PROVIDER == "openai":
        return _openai_embed(text)
    return None


def _openai_embed(text: str) -> bytes | None:
    from openai import OpenAI

    client = OpenAI(api_key=CLOUD_API_KEY)
    resp = client.embeddings.create(
        model="text-embedding-3-small", input=text,
    )
    vec = resp.data[0].embedding
    return struct.pack(f"{len(vec)}f", *vec)
