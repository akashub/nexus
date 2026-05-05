from __future__ import annotations

import struct

from nexus.ai_config import resolve

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


def is_cloud_available(provider: str | None = None) -> bool:
    if provider:
        return bool(resolve(provider))
    return any(resolve(p) for p in _DEFAULT_MODELS)


def available_cloud_providers() -> list[dict]:
    providers = []
    for name, default_model in _DEFAULT_MODELS.items():
        creds = resolve(name)
        entry: dict = {
            "provider": name,
            "model": creds.get("model", default_model) if creds else default_model,
            "configured": bool(creds),
        }
        if name == "gemini" and creds and creds.get("project"):
            entry["via"] = "vertex"
        elif name == "gemini" and creds:
            entry["via"] = "api"
        providers.append(entry)
    return providers


def generate_cloud(
    prompt: str, *, system: str | None = None, provider: str | None = None,
    model: str | None = None,
) -> str:
    p = provider or _default_provider()
    creds = resolve(p)
    if not creds:
        raise ValueError(f"Provider {p} not configured")
    if p == "anthropic":
        return _anthropic_generate(prompt, creds, system=system, model=model)
    if p == "openai":
        return _openai_generate(prompt, creds, system=system, model=model)
    if p == "gemini":
        return _gemini_generate(prompt, creds, system=system, model=model)
    raise ValueError(f"Unknown cloud provider: {p}")


def _default_provider() -> str:
    for p in _DEFAULT_MODELS:
        if resolve(p):
            return p
    return ""


def _anthropic_generate(
    prompt: str, creds: dict, *, system: str | None = None, model: str | None = None,
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=creds["api_key"])
    kwargs: dict = {
        "model": model or creds.get("model", _DEFAULT_MODELS["anthropic"]),
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text


def _openai_generate(
    prompt: str, creds: dict, *, system: str | None = None, model: str | None = None,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=creds["api_key"])
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=model or creds.get("model", _DEFAULT_MODELS["openai"]),
        messages=messages, max_tokens=1024,
    )
    return resp.choices[0].message.content or ""


def _gemini_generate(
    prompt: str, creds: dict, *, system: str | None = None, model: str | None = None,
) -> str:
    import httpx
    mdl = model or creds.get("model", _DEFAULT_MODELS["gemini"])
    if creds.get("project"):
        return _gemini_vertex(prompt, mdl, creds, system=system)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent"
    body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = httpx.post(url, params={"key": creds["api_key"]}, json=body, timeout=30.0)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _gemini_vertex(
    prompt: str, model: str, creds: dict, *, system: str | None = None,
) -> str:
    import httpx
    loc = creds.get("location", "us-central1")
    proj = creds["project"]
    url = (
        f"https://{loc}-aiplatform.googleapis.com/v1/"
        f"projects/{proj}/locations/{loc}/"
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


def embed_cloud(text: str, provider: str | None = None) -> bytes | None:
    p = provider or "openai"
    creds = resolve(p)
    if p == "openai" and creds:
        return _openai_embed(text, creds)
    return None


def _openai_embed(text: str, creds: dict) -> bytes | None:
    from openai import OpenAI
    client = OpenAI(api_key=creds["api_key"])
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    vec = resp.data[0].embedding
    return struct.pack(f"{len(vec)}f", *vec)
