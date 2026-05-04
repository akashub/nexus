from __future__ import annotations

import os
import struct

CLOUD_PROVIDER = os.environ.get("NEXUS_CLOUD_PROVIDER", "")
CLOUD_API_KEY = os.environ.get("NEXUS_CLOUD_API_KEY", "")
CLOUD_MODEL = os.environ.get("NEXUS_CLOUD_MODEL", "")

GEMINI_API_KEY = os.environ.get("NEXUS_GEMINI_API_KEY", "")
GEMINI_PROJECT = os.environ.get("NEXUS_GEMINI_PROJECT", "")
GEMINI_LOCATION = os.environ.get("NEXUS_GEMINI_LOCATION", "us-central1")
GEMINI_MODEL = os.environ.get("NEXUS_GEMINI_MODEL", "gemini-2.5-flash")

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


def is_cloud_available(provider: str | None = None) -> bool:
    if provider == "gemini":
        return _is_gemini_available()
    if provider:
        return provider == CLOUD_PROVIDER and bool(CLOUD_API_KEY)
    return bool(CLOUD_PROVIDER and CLOUD_API_KEY) or _is_gemini_available()


def _is_gemini_available() -> bool:
    return bool(GEMINI_API_KEY or GEMINI_PROJECT)


def available_cloud_providers() -> list[dict]:
    providers = []
    if CLOUD_PROVIDER == "anthropic" and CLOUD_API_KEY:
        providers.append({
            "provider": "anthropic",
            "model": CLOUD_MODEL or _DEFAULT_MODELS["anthropic"],
        })
    if CLOUD_PROVIDER == "openai" and CLOUD_API_KEY:
        providers.append({
            "provider": "openai",
            "model": CLOUD_MODEL or _DEFAULT_MODELS["openai"],
        })
    if _is_gemini_available():
        providers.append({
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "via": "vertex" if GEMINI_PROJECT else "api",
        })
    return providers


def _get_model(provider: str | None = None) -> str:
    if provider and provider != CLOUD_PROVIDER:
        return _DEFAULT_MODELS.get(provider, "")
    return CLOUD_MODEL or _DEFAULT_MODELS.get(CLOUD_PROVIDER, "")


def generate_cloud(
    prompt: str, *, system: str | None = None, provider: str | None = None,
    model: str | None = None,
) -> str:
    p = provider or CLOUD_PROVIDER
    if p == "anthropic":
        return _anthropic_generate(prompt, system=system, model=model)
    if p == "openai":
        return _openai_generate(prompt, system=system, model=model)
    if p == "gemini":
        return _gemini_generate(prompt, system=system, model=model)
    raise ValueError(f"Unknown cloud provider: {p}")


def _anthropic_generate(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=CLOUD_API_KEY)
    kwargs: dict = {
        "model": model or _get_model("anthropic"),
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text


def _openai_generate(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=CLOUD_API_KEY)
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=model or _get_model("openai"), messages=messages, max_tokens=1024,
    )
    return resp.choices[0].message.content or ""


def _gemini_generate(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    import httpx
    model = model or GEMINI_MODEL
    if GEMINI_PROJECT:
        return _gemini_vertex(prompt, model, system=system)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = httpx.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=30.0)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _gemini_vertex(prompt: str, model: str, *, system: str | None = None) -> str:
    import httpx
    url = (
        f"https://{GEMINI_LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{GEMINI_PROJECT}/locations/{GEMINI_LOCATION}/"
        f"publishers/google/models/{model}:generateContent"
    )
    body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    token = _get_gcloud_token()
    r = httpx.post(
        url, json=body, timeout=30.0,
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _get_gcloud_token() -> str:
    import subprocess
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True,
    ).strip()


def embed_cloud(text: str) -> bytes | None:
    if CLOUD_PROVIDER == "openai":
        return _openai_embed(text)
    return None


def _openai_embed(text: str) -> bytes | None:
    from openai import OpenAI
    client = OpenAI(api_key=CLOUD_API_KEY)
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    vec = resp.data[0].embedding
    return struct.pack(f"{len(vec)}f", *vec)
