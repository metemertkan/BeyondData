"""Episode 5: the tables (results/ep05/<size>/summary.md and summary.json).

    uv run python -m scripts.ep05_summary --size full

Against the reference (fp16, greedy, wording A), per design and task:
  right      items scored right (abstain: declined correctly)
  lost       right in the reference, not right here          gained  the other way
  changed    the reply differs from the reference's (normalized)
The noise floor is f16_b: the reference with the prompt reworded.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from quant import tasks
from scripts.ep05_run import DESIGNS, OUT, add_built

TASKS = ("closed", "rag", "abstain", "records")
DATA = ("rag", "abstain", "records")
REF, NOISE = "f16", "f16_b"
LABEL = {"shipped": "as shipped (Q4_K_M, default context, sampled)", "f16": "fp16 (reference)",
         "q8_0": "Q8_0", "q6_k": "Q6_K", "q5_k_m": "Q5_K_M", "q4_k_m": "Q4_K_M (Ollama's file)", "q4_k_m_made": "Q4_K_M (made here)", "q3_k_m": "Q3_K_M", "q2_k": "Q2_K",
         "f16_b": "fp16, prompt reworded (noise floor)", "shipped_ctx": "as shipped, context set",
         "q4_k_m_kv_q8_0": "Q4_K_M, KV q8_0", "q4_k_m_kv_q4_0": "Q4_K_M, KV q4_0", "q4_k_m_kv_f16": "Q4_K_M, KV container f16", "q4_k_m_repeat": "Q4_K_M, run again",
         "q4_k_m_kv_f16_all": "Q4_K_M, KV container f16, closed first",
         "4b_q8_0": "qwen3:4b Q8_0", "q6_k_kv_q8_0": "Q6_K, KV q8_0"}


def load(size: str) -> dict:
    runs = {}
    for p in sorted((OUT / size).glob("*.jsonl")):
        rows = {}
        for line in p.read_text().splitlines():
            j = json.loads(line)
            rows[(j["task"], j["id"])] = j
        meta = OUT / size / f"{p.stem}.meta.json"
        runs[p.stem] = {"rows": rows, "meta": json.loads(meta.read_text()) if meta.exists() else {}}
    return runs


def norm(s: str) -> str:
    return tasks.normalize(s or "")


def compare(a: dict, ref: dict, task: str) -> dict:
    keys = [k for k in a if k[0] == task and k in ref]
    right = sum(a[k]["score"] == "right" for k in keys)
    lost = sum(ref[k]["score"] == "right" and a[k]["score"] != "right" for k in keys)
    gained = sum(ref[k]["score"] != "right" and a[k]["score"] == "right" for k in keys)
    changed = sum(norm(a[k]["reply"]) != norm(ref[k]["reply"]) for k in keys)
    declined = sum(a[k]["score"] == "declined" for k in keys)
    return {"n": len(keys), "right": right, "lost": lost, "gained": gained, "changed": changed, "declined": declined}


def speed(rows: dict) -> dict:
    # Ollama counts every prompt token but times only the ones not reused from its prompt cache, so reading speed
    # comes from the full reads of each export only: per window, the rows within half of its longest read time.
    full = []
    for w in {k[1].split(":")[0] for k in rows if k[0] == "records"}:
        rs = [r for k, r in rows.items() if k[0] == "records" and k[1].startswith(w + ":")]
        top = max(r["prompt_s"] for r in rs)
        full += [r for r in rs if r["prompt_s"] >= top / 2]
    p_tok = sum(r["prompt_tokens"] for r in full) or 0
    p_s = sum(r["prompt_s"] for r in full) or 1
    g_tok = sum(r["gen_tokens"] or 0 for r in rows.values() if r["task"] != "records")
    g_s = sum(r["gen_s"] for r in rows.values() if r["task"] != "records") or 1
    return {"prompt_tps": round(p_tok / p_s, 1), "gen_tps_short": round(g_tok / g_s, 2)}


def main(size: str) -> None:
    runs = load(size)
    budget_path = OUT / "budget.json"
    budget = json.loads(budget_path.read_text()) if budget_path.exists() else None
    if budget:
        add_built(budget["picks"])
    t = tasks.load(size)
    md = [f"# Episode 5 summary ({size}: {len(t['nq'])} NQ questions, {len(t['records'])} record lookups)\n"]
    js = {"size": size, "designs": {}}
    if REF not in runs:
        md.append("No reference run yet.")
        (OUT / size / "summary.md").write_text("\n".join(md))
        return
    ref = runs[REF]["rows"]
    n_items = {task: sum(1 for k in ref if k[0] == task) for task in TASKS}
    md.append("Items per task: " + ", ".join(f"{k} {v}" for k, v in n_items.items()) + ".\n")
    models = OUT / "models.json"
    if models.exists():
        md.append("## The weights, read back\n")
        md.append("| Level | Model | Source | Ollama says | Same bytes as llama-quantize here |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for q, m in json.loads(models.read_text()).items():
            md.append(f"| {q} | `{m['model']}` | {m['source']} | {m['quantization_level']} | {m.get('same_as_made_here', '')} |")
        md.append("")

    # ---- per design, per task
    md.append("## Every design against the reference (right / lost / gained / changed replies)\n")
    md.append("| Design | " + " | ".join(TASKS) + " | data tasks: lost |")
    md.append("| :--- |" + " ---: |" * (len(TASKS) + 1))
    order = [n for n in ["f16", "f16_b", "q8_0", "q6_k", "q5_k_m", "q4_k_m", "q4_k_m_made", "q3_k_m", "q2_k", "shipped",
                         "shipped_ctx", "q4_k_m_repeat", "q4_k_m_kv_f16", "q4_k_m_kv_f16_all", "q4_k_m_kv_q8_0", "q4_k_m_kv_q4_0", "q6_k_kv_q8_0", "4b_q8_0"] if n in runs]
    order += [n for n in runs if n not in order]
    for name in order:
        rows = runs[name]["rows"]
        cells, data_lost, js_d = [], 0, {}
        for task in TASKS:
            c = compare(rows, ref, task)
            js_d[task] = c
            if not c["n"]:
                cells.append("")
                continue
            if task in DATA:
                data_lost += c["lost"]
            cells.append(f"{c['right']}/{c['n']} · −{c['lost']} +{c['gained']} · {c['changed']}")
        js["designs"][name] = {"tasks": js_d, "data_lost": data_lost, "speed": speed(rows),
                               "loads": runs[name]["meta"].get("loads"), "sampled": runs[name]["meta"].get("sampled")}
        md.append(f"| {LABEL.get(name, name)} | " + " | ".join(cells) + f" | {data_lost} |")
    md.append("\nCells: right of n · answers lost and gained against fp16 · replies that differ from fp16's.\n")

    # ---- repeat checks: same settings and history should give the same replies
    md.append("## Repeat checks (same settings, same history: replies that differ)\n")
    js["repeats"] = {}
    for a, b, tasks_ in (("shipped", "shipped_ctx", ("rag", "abstain")), ("q4_k_m", "q4_k_m_repeat", TASKS),
                         ("q4_k_m", "q4_k_m_kv_f16_all", TASKS)):
        if a in runs and b in runs:
            ra, rb = runs[a]["rows"], runs[b]["rows"]
            keys = [k for k in ra if k in rb and k[0] in tasks_]
            n_diff = sum(ra[k]["reply"] != rb[k]["reply"] for k in keys)
            js["repeats"][f"{a} vs {b}"] = {"n": len(keys), "differ": n_diff}
            md.append(f"- {LABEL.get(a, a)} vs {LABEL.get(b, b)} ({', '.join(tasks_)}): {n_diff} of {len(keys)} differ")
    md.append("")

    # ---- declines, abstention and records detail
    md.append("## Declines and abstention\n")
    md.append("| Design | rag: declined (answer in passages / not) | abstain: declined correctly | abstain: answered with the right answer anyway |")
    md.append("| :--- | ---: | ---: | ---: |")
    nq = {str(q["q"]): q for q in t["nq"]}
    for name in order:
        rows = runs[name]["rows"]
        rag = [(k, r) for k, r in rows.items() if k[0] == "rag"]
        if not rag:
            continue
        dec_in = sum(r["score"] == "declined" and nq[k[1]]["answer_in_passages"] for k, r in rag)
        dec_out = sum(r["score"] == "declined" and not nq[k[1]]["answer_in_passages"] for k, r in rag)
        ab = [(k, r) for k, r in rows.items() if k[0] == "abstain"]
        ab_right = sum(r["score"] == "right" for _, r in ab)
        ab_true = sum(any(tasks.contains(r["reply"], a) for a in nq[k[1]]["answers"]) for k, r in ab)
        md.append(f"| {LABEL.get(name, name)} | {dec_in} / {dec_out} | {ab_right}/{len(ab)} | {ab_true} |")
    md.append("")

    md.append("## Records: right by context, kind and position\n")
    kinds = ("amount", "date", "email", "number")
    md.append("| Design | S | L | " + " | ".join(kinds) + " | L first third | L middle | L last third | L prompt tokens (median) |")
    md.append("| :--- |" + " ---: |" * (6 + len(kinds)))
    recs = {f"{r['window']}:{r['row']}:{r['kind']}": r for r in t["records"]}
    for name in order:
        rows = {k[1]: r for k, r in runs[name]["rows"].items() if k[0] == "records"}
        if not rows:
            continue
        def frac(f):
            ks = [k for k in rows if f(recs[k])]
            return f"{sum(rows[k]['score'] == 'right' for k in ks)}/{len(ks)}" if ks else ""
        lt = sorted(r["prompt_tokens"] for k, r in rows.items() if recs[k]["context"] == "L")
        md.append(f"| {LABEL.get(name, name)} | {frac(lambda r: r['context'] == 'S')} | {frac(lambda r: r['context'] == 'L')} | "
                  + " | ".join(frac(lambda r, kd=kd: r["kind"] == kd) for kd in kinds) + " | "
                  + " | ".join(frac(lambda r, a=a, b=b: r["context"] == "L" and a <= r["position"] < b)
                               for a, b in ((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01)))
                  + f" | {lt[len(lt) // 2] if lt else ''} |")
    md.append("")

    # ---- speed and memory
    md.append("## Speed and memory\n")
    md.append("| Design | prompt tokens/s | reply tokens/s (short prompts) | loaded size, NQ context (GiB) | loaded size, records context (GiB) | KV cache (log) |")
    md.append("| :--- | ---: | ---: | ---: | ---: | :--- |")
    for name in order:
        dd = js["designs"][name]
        loads = dd["loads"] or {}
        g = lambda key: (lambda v: f"{v / 2**30:.2f}" if v else "")(loads.get(key, {}).get("size"))
        nqk = next((k for k in loads if not k.startswith("records")), None)
        rk = next((k for k in loads if k.startswith("records")), None)
        kvl = (loads.get(rk) or {}).get("kv_log") or ""
        md.append(f"| {LABEL.get(name, name)} | {dd['speed']['prompt_tps']} | {dd['speed']['gen_tps_short']} | "
                  f"{g(nqk) if nqk else ''} | {g(rk) if rk else ''} | {kvl.replace('llama_kv_cache: ', '')[:80]} |")
    md.append("")

    kld = OUT / "kld.json"
    if kld.exists():
        md.append("## The number on the box: KL divergence and same top token against fp16 (the test questions' passages)\n")
        md.append("| Level | Mean KLD | 99th percentile KLD | Same top token | Perplexity (fp16 / this) |")
        md.append("| :--- | ---: | ---: | ---: | :--- |")
        for q, r in json.loads(kld.read_text()).items():
            md.append(f"| {q} | {r['kld_mean']} | {r['kld_p99']} | {r['same_top_p']}% | {r['ppl_base']} / {r['ppl_q']} |")
        js["kld"] = json.loads(kld.read_text())
        md.append("")

    # ---- Act 3
    if budget and NOISE in runs:
        floor = js["designs"][NOISE]["data_lost"]
        md.append(f"## Act 3: built (context {budget['context']:,}; the noise floor loses {floor} answers on the data tasks)\n")
        md.append("| Budget | Pick (most weight bits that fit; KV f16, else q8_0, else q4_0) | Loaded size GiB | Lost on data tasks | Passes (≤ noise floor) |")
        md.append("| ---: | :--- | ---: | ---: | :--- |")
        js["built"] = []
        for p in budget["picks"]:
            name = p["design"]
            lost = js["designs"].get(name, {}).get("data_lost") if name else None
            ok = lost is not None and lost <= floor
            js["built"].append({**p, "lost": lost, "passes": ok})
            md.append(f"| {p['budget_gib']} | {LABEL.get(name, name) if name else 'nothing fits'} | {p.get('gib', '')} | "
                      f"{'' if lost is None else lost} | {'yes' if ok else ('not run' if lost is None else 'no')} |")
        js["noise_floor_lost"] = floor
        md.append("")
    (OUT / size / "summary.md").write_text("\n".join(md))
    (OUT / size / "summary.json").write_text(json.dumps(js, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    main(ap.parse_args().size)
