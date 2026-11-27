"""Episode 5: every design over its tasks, one request at a time.

    uv run python -m scripts.ep05_run --size pilot --designs all
    uv run python -m scripts.ep05_run --size full --designs all

Writes results/ep05/<size>/<design>.jsonl (one line per task and item; reruns skip what is done) and
results/ep05/<size>/<design>.meta.json (model, server, options, memory as Ollama reports it, KV buffer from the log).
Designs are in PLAN §4. The server is the Episode 5 Ollama container: `ollama` for f16 KV (as shipped), `ollama-kv`
with BD5_KV for a quantized KV cache. Switching restarts the container; switching models unloads the last one.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from quant import llm, prompts, score, tasks

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "ep05"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.ep05.yml")]
NQ_CTX, RECORDS_CTX = 4096, 16384
GREEDY = {"temperature": 0, "seed": 1}
SHIPPED = {"seed": 1}                      # nothing but a seed, so a rerun draws the same sample
# Amendment 3: one task order for every design, data tasks first. llama-server reuses cached prompts, so a reply can
# depend on what ran before it; with one order, every design's data tasks have the same history (PLAN §6).
ALL = ("rag", "abstain", "records", "closed")
DATA = ("rag", "abstain", "records")
GUARD_N, GUARD_S = 20, 60.0


def made(q: str) -> str:
    return f"bd5/qwen3-8b:{q}"


def d(model, tasks_=ALL, opts=GREEDY, ctx=True, wording="A", kv=None):
    return {"model": model, "tasks": list(tasks_), "options": opts, "set_ctx": ctx, "wording": wording, "kv": kv}


DESIGNS = {
    "shipped": d("qwen3:8b", opts=SHIPPED, ctx=False),
    "f16": d("qwen3:8b-fp16"),
    "q8_0": d("qwen3:8b-q8_0"),
    "q6_k": d(made("q6_k")),
    "q5_k_m": d(made("q5_k_m")),
    "q4_k_m": d("qwen3:8b"),
    "q4_k_m_made": d(made("q4_k_m")),      # amendment 1: same label, llama-quantize's file (attn_v quantized)
    "q3_k_m": d(made("q3_k_m")),
    "q2_k": d(made("q2_k")),
    "f16_b": d("qwen3:8b-fp16", wording="B"),
    "shipped_ctx": d("qwen3:8b", DATA, opts=SHIPPED),   # rag and abstain: same settings as shipped (a repeat check)
    "q4_k_m_kv_q8_0": d("qwen3:8b", DATA, kv="q8_0"),
    "q4_k_m_kv_q4_0": d("qwen3:8b", DATA, kv="q4_0"),
    "4b_q8_0": d("qwen3:4b-q8_0"),
}
PILOT = ["f16", "q4_k_m", "q2_k", "shipped", "shipped_ctx", "q4_k_m_kv_f16", "q4_k_m_kv_q4_0", "q4_k_m_made"]
DESIGNS["q4_k_m_kv_f16"] = d("qwen3:8b", DATA, kv="f16")   # pilot only: is the KV container the same at f16?
# Pilot only, after the pilot (PLAN §6): llama-server reuses cached prompts, so does a greedy run repeat itself,
# and does the KV container match once its history is the same (closed first, as in q4_k_m)?
DESIGNS["q4_k_m_repeat"] = d("qwen3:8b", ("closed", "rag", "abstain", "records"))
DESIGNS["q4_k_m_kv_f16_all"] = d("qwen3:8b", ("closed", "rag", "abstain", "records"), kv="f16")
PILOT_ONLY = {"q4_k_m_kv_f16", "q4_k_m_repeat", "q4_k_m_kv_f16_all"}


def add_built(picks: list[dict]) -> None:
    """Act 3's picks that aren't designs already (computed from sizes before the full run: scripts/ep05_budget.py)."""
    for p in picks:
        name = p["design"]
        if name not in DESIGNS:
            DESIGNS[name] = d(p["model"], DATA, kv=None if p["kv"] == "f16" else p["kv"])


# ---- the server

_current: tuple | None = None


def _up(service: str, kv: str | None) -> None:
    env = {**os.environ, "BD5_KV": kv or "f16"}
    other = "ollama" if service == "ollama-kv" else "ollama-kv"
    subprocess.run(COMPOSE + ["--profile", "kv", "stop", other], check=True, capture_output=True, env=env)
    subprocess.run(COMPOSE + ["--profile", "kv", "rm", "-f", other], check=True, capture_output=True, env=env)
    subprocess.run(COMPOSE + ["--profile", "kv", "up", "-d", "--force-recreate", service], check=True,
                   capture_output=True, env=env)
    for _ in range(120):
        try:
            if llm._client.get(f"{llm.OLLAMA}/api/version", timeout=5).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"{service} did not answer")


def server(kv: str | None) -> str:
    global _current
    want = ("ollama-kv", kv) if kv else ("ollama", None)
    if _current != want:
        _up(want[0], kv)
        _current = want
    return "bd5-ollama-kv" if kv else "bd5-ollama"


def unload_all() -> None:
    for m in llm.ps():
        llm._client.post(f"{llm.OLLAMA}/api/generate", json={"model": m["name"], "keep_alive": 0})


def kv_log(container: str) -> str | None:
    log = subprocess.run(["docker", "logs", container], capture_output=True, text=True).stderr
    lines = re.findall(r"llama_kv_cache: size = .*", log)
    return lines[-1] if lines else None


# ---- running

def items_for(task: str, t: dict) -> list[tuple[str, dict]]:
    if task == "records":
        return [(f"{r['window']}:{r['row']}:{r['kind']}", r) for r in t["records"]]
    qs = [q for q in t["nq"] if task != "abstain" or q["run_abstain"]]
    return [(str(q["q"]), q) for q in qs]


def run_design(size: str, name: str) -> None:
    spec = DESIGNS[name]
    t = tasks.load(size)
    out = OUT / size / f"{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(j["task"], j["id"]) for j in map(json.loads, out.read_text().splitlines())}
    meta_path = OUT / size / f"{name}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"design": name, **spec, "loads": {}}
    container = server(spec["kv"])
    unload_all()
    for task in spec["tasks"]:
        todo = [(i, it) for i, it in items_for(task, t) if (task, i) not in done]
        if not todo:
            continue
        ctx = (RECORDS_CTX if task == "records" else NQ_CTX) if spec["set_ctx"] else None
        opts = {**spec["options"], **({"num_ctx": ctx} if ctx else {})}
        times, window = [], None
        print(f"{time.strftime('%H:%M:%S')} {name} {task}: {len(todo)} items", flush=True)
        with out.open("a") as f:
            for n, (iid, item) in enumerate(todo):
                first_read = task == "records" and item["window"] != window
                window = item["window"] if task == "records" else None
                p = prompts.build(task, item, spec["wording"], t["contexts"])
                r = llm.chat(spec["model"], p, opts)
                s = score.score(task, item, r["reply"])
                f.write(json.dumps({"task": task, "id": iid, "score": s, **r}) + "\n")
                f.flush()
                key = f"{task}:{ctx}"
                if key not in meta["loads"]:
                    ps = [m for m in llm.ps() if m["name"] == spec["model"] or m["model"] == spec["model"]]
                    meta["loads"][key] = {"size": ps[0].get("size") if ps else None,
                                          "context_length": ps[0].get("context_length") if ps else None,
                                          "kv_log": kv_log(container)}
                    meta_path.write_text(json.dumps(meta, indent=1))
                if not first_read:
                    times.append(r["wall_s"])
                if len(times) == GUARD_N and sum(times) / GUARD_N > GUARD_S:
                    print(f"  {name} {task}: over {GUARD_S:g} s per item after {GUARD_N}; stopped (sampled)", flush=True)
                    meta.setdefault("sampled", []).append(task)
                    meta_path.write_text(json.dumps(meta, indent=1))
                    break
        right = sum(1 for j in map(json.loads, out.read_text().splitlines()) if j["task"] == task and j["score"] == "right")
        print(f"{time.strftime('%H:%M:%S')} {name} {task}: done ({right} right)", flush=True)
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta_path.write_text(json.dumps(meta, indent=1))
    unload_all()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    ap.add_argument("--designs", default="all", help="comma list, or all (pilot: the pilot's designs)")
    a = ap.parse_args()
    budget = OUT / "budget.json"
    if budget.exists():
        add_built(json.loads(budget.read_text())["picks"])
    if a.designs == "all":
        names = PILOT if a.size == "pilot" else [n for n in DESIGNS if n not in PILOT_ONLY]
    else:
        names = a.designs.split(",")
    # group by server so the container restarts as rarely as possible
    names.sort(key=lambda n: (DESIGNS[n]["kv"] or "", 0))
    for n in names:
        run_design(a.size, n)
    print("all designs done", flush=True)
