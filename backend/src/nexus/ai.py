from __future__ import annotations

import json
import os
import struct

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("NEXUS_LLM_MODEL", "gemma3:4b")
EMBED_MODEL = os.environ.get("NEXUS_EMBED_MODEL", "nomic-embed-text")

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def is_available() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def generate(prompt: str, *, model: str | None = None, system: str | None = None) -> str:
    model = model or LLM_MODEL
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 2048},
    }
    if system:
        payload["system"] = system
    r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()["response"]


def generate_stream(prompt: str, *, model: str | None = None, system: str | None = None):
    model = model or LLM_MODEL
    payload: dict = {"model": model, "prompt": prompt, "stream": True}
    if system:
        payload["system"] = system
    with httpx.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload, timeout=_TIMEOUT) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk.get("response"):
                    yield chunk["response"]
                if chunk.get("done"):
                    break


def embed(text: str, *, model: str | None = None) -> bytes | None:
    model = model or EMBED_MODEL
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": model, "input": text},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        vec = r.json().get("embeddings", [[]])[0]
        if not vec:
            return None
        return struct.pack(f"{len(vec)}f", *vec)
    except (httpx.HTTPError, KeyError, IndexError):
        return None


def cosine_similarity(a: bytes, b: bytes) -> float:
    va = list(struct.unpack(f"{len(a) // 4}f", a))
    vb = list(struct.unpack(f"{len(b) // 4}f", b))
    dot = sum(x * y for x, y in zip(va, vb, strict=False))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(x * x for x in vb) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
