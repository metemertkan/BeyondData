"""Local models through Ollama's HTTP API."""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import httpx
import numpy as np

OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "bge-m3"
THINK = {"qwen3:8b": False, "gpt-oss:20b": "low"}
_client = httpx.Client(timeout=900)


def chat(model: str, messages: list[dict], seed: int, tools: list | None = None, usage: dict | None = None) -> dict:
    body = {"model": model, "messages": messages, "stream": False, "think": THINK.get(model, False),
            "options": {"seed": seed, "num_ctx": 12288, "num_predict": 1536}}
    if tools:
        body["tools"] = tools
    t0 = time.time()
    for attempt in range(3):
        r = _client.post(f"{OLLAMA}/api/chat", json=body)
        if r.status_code == 200:
            break
        body["options"]["seed"] = seed + 1000 * (attempt + 1)   # e.g. a tool call the server couldn't parse
    r.raise_for_status()
    data = r.json()
    if usage is not None:
        usage["calls"] = usage.get("calls", 0) + 1
        usage["prompt_tokens"] = usage.get("prompt_tokens", 0) + data.get("prompt_eval_count", 0)
        usage["output_tokens"] = usage.get("output_tokens", 0) + data.get("eval_count", 0)
        usage["model_seconds"] = round(usage.get("model_seconds", 0) + time.time() - t0, 1)
    return data["message"]


def embed(texts: list[str], cache_dir: Path | None = None) -> np.ndarray:
    key = hashlib.sha256(("\n\x00".join(texts) + EMBED_MODEL).encode()).hexdigest()[:16]
    path = cache_dir / f"emb-{key}.npy" if cache_dir else None
    if path and path.exists():
        return np.load(path)
    out = []
    for i in range(0, len(texts), 32):
        r = _client.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": texts[i:i + 32]})
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    arr = np.asarray(out, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, arr)
    return arr
