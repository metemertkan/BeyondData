"""Episode 5: one chat call to the Episode 5 Ollama container (docker-compose.ep05.yml, port 11435).

Thinking is off everywhere (`think: false`, as in Episode 1): with thinking, one answer takes minutes on this CPU.
`num_predict` caps every reply at 64 tokens, which no short answer needs; it is a cost cap, not a setting
under test. Everything else comes from the design: sampling or greedy, context length, or nothing at all.
"""
from __future__ import annotations

import os
import time

import httpx

OLLAMA = os.environ.get("BD5_OLLAMA", "http://127.0.0.1:11435")
NUM_PREDICT = 64
_client = httpx.Client(timeout=3600)


def chat(model: str, prompt: str, options: dict) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
            "keep_alive": -1, "options": {**options, "num_predict": NUM_PREDICT}}
    t0 = time.time()
    for attempt in range(3):
        r = _client.post(f"{OLLAMA}/api/chat", json=body)
        if r.status_code == 200:
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    j = r.json()
    return {"reply": j["message"]["content"], "prompt_tokens": j.get("prompt_eval_count"),
            "gen_tokens": j.get("eval_count"), "prompt_s": round(j.get("prompt_eval_duration", 0) / 1e9, 3),
            "gen_s": round(j.get("eval_duration", 0) / 1e9, 3), "load_s": round(j.get("load_duration", 0) / 1e9, 3),
            "wall_s": round(time.time() - t0, 3), "done_reason": j.get("done_reason")}


def ps() -> list[dict]:
    return _client.get(f"{OLLAMA}/api/ps").json().get("models", [])


def show(model: str) -> dict:
    return _client.post(f"{OLLAMA}/api/show", json={"model": model}).json()
