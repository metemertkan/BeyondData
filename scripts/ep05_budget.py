"""Episode 5, Act 3's picks: what fits in 6, 8 and 12 GiB, from sizes alone (no answers involved).

    uv run python -m scripts.ep05_budget      # -> results/ep05/budget.json

Loads every weight level with each KV cache type (f16, q8_0, q4_0) at a 16,384-token context and reads the size
Ollama reports for the loaded model (/api/ps), which is what it compares with a GPU's memory. Then the rule from
PLAN §4: per budget, the most weight bits that fit, with an f16 KV cache if it fits at that level, else q8_0,
else q4_0. Picks that aren't designs yet are added to the full run (scripts/ep05_run.py reads budget.json).
"""
from __future__ import annotations

import json

from quant import llm
from scripts.ep05_run import DESIGNS, OUT, RECORDS_CTX, server, unload_all

LEVELS = ["f16", "q8_0", "q6_k", "q5_k_m", "q4_k_m", "q3_k_m", "q2_k"]
KVS = ["f16", "q8_0", "q4_0"]
BUDGETS_GIB = [6, 8, 12]


def measure() -> dict:
    sizes = {}
    for kv in KVS:
        server(None if kv == "f16" else kv)
        for level in LEVELS:
            model = DESIGNS[level]["model"]
            unload_all()
            llm.chat(model, "Hi", {"temperature": 0, "seed": 1, "num_ctx": RECORDS_CTX})
            ps = [m for m in llm.ps() if m["model"] == model or m["name"] == model]
            sizes[f"{level}/{kv}"] = {"model": model, "level": level, "kv": kv, "bytes": ps[0]["size"],
                                      "context_length": ps[0].get("context_length")}
            print(level, kv, round(ps[0]["size"] / 2**30, 2), "GiB", flush=True)
    unload_all()
    return sizes


def picks(sizes: dict) -> list[dict]:
    out = []
    for b in BUDGETS_GIB:
        pick = None
        for level in LEVELS:
            for kv in KVS:
                s = sizes[f"{level}/{kv}"]
                if s["bytes"] <= b * 2**30:
                    pick = s
                    break
            if pick:
                break
        if pick:
            name = pick["level"] if pick["kv"] == "f16" else f"{pick['level']}_kv_{pick['kv']}"
            out.append({"budget_gib": b, "design": name, "model": pick["model"], "kv": pick["kv"],
                        "gib": round(pick["bytes"] / 2**30, 2)})
        else:
            out.append({"budget_gib": b, "design": None})
    return out


if __name__ == "__main__":
    s = measure()
    p = picks(s)
    (OUT / "budget.json").write_text(json.dumps({"context": RECORDS_CTX, "sizes": s, "picks": p}, indent=1))
    print(json.dumps(p, indent=1))
