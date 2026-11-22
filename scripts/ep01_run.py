"""Episode 1 batch: every design on every question, several seeds.

    uv run python -m scripts.ep01_run --questions S1,C3 --seeds 1      # a quick look
    uv run python -m scripts.ep01_run                                  # the full batch

Results are appended to results/ep01/runs.jsonl; runs already there are skipped, so an
interrupted batch resumes where it stopped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ledger import designs
from ledger.questions import QUESTIONS
from ledger.score import score
from ledger.world import build

OUT = Path(__file__).resolve().parent.parent / "results" / "ep01" / "runs.jsonl"


def key(r: dict) -> tuple:
    return (r["model"], r["design"], r["question"], r["seed"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen3:8b")
    ap.add_argument("--designs", default=",".join(designs.DESIGNS))
    ap.add_argument("--questions", default=",".join(QUESTIONS))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {key(json.loads(l)) for l in out.read_text().splitlines() if l.strip()}
    w = build()
    rows, _ = designs.row_index()
    plan = [(m, d, q, s) for s in range(1, args.seeds + 1) for m in args.models.split(",")
            for q in args.questions.split(",") for d in args.designs.split(",")]
    todo = [p for p in plan if p not in done]
    print(f"{len(plan)} runs planned, {len(todo)} to do", flush=True)
    for n, (model, design, qid, seed) in enumerate(todo, 1):
        q = QUESTIONS[qid]
        mode = "portal" if q.kind == "portal" else "internal"
        try:
            run = designs.run(design, q.text, mode, model, seed, w)
        except Exception as e:  # recorded, not hidden: a crashed run counts as no answer
            run = {"reply": "", "error": f"{type(e).__name__}: {e}", "messages": [], "queries": [], "tool_calls": [],
                   "writes": [], "retrieved": [], "usage": {}, "seconds": 0}
        run["context_rows"] = [rows[k] for k in run.get("retrieved", [])]
        s = score(q, run["reply"], w, run)
        row = {"model": model, "design": design, "question": qid, "kind": q.kind, "mode": mode, "seed": seed,
               **s, "expected": q.expected if not hasattr(q.expected, "isoformat") else q.expected.isoformat(), **run}
        with out.open("a") as f:
            f.write(json.dumps(row, default=str) + "\n")
        flag = (" LEAK" if s.get("leak") else "") + (" WROTE" if s.get("wrote") else "")
        print(f"[{n}/{len(todo)}] {model} {design:9} {qid} s{seed}: {s['outcome']:8}{flag} "
              f"({run['seconds']}s) {s['answer'][:90]!r}", flush=True)


if __name__ == "__main__":
    main()
