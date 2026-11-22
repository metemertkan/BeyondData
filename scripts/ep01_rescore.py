"""Rescore results/ep01/runs.jsonl from the stored replies (no model calls), after a scorer fix.

    uv run python -m scripts.ep01_rescore
"""
from __future__ import annotations

import json
from pathlib import Path

from ledger.questions import QUESTIONS
from ledger.score import score
from ledger.world import build

PATH = Path(__file__).resolve().parent.parent / "results" / "ep01" / "runs.jsonl"
SCORE_KEYS = ("outcome", "answer", "leak", "wrote", "exposed_to_model", "untrue")


def main() -> None:
    w = build()
    rows = [json.loads(l) for l in PATH.read_text().splitlines() if l.strip()]
    changed = 0
    for r in rows:
        s = score(QUESTIONS[r["question"]], r["reply"], w, r)
        before = {k: r.get(k) for k in SCORE_KEYS}
        for k in SCORE_KEYS:
            r.pop(k, None)
        r.update(s)
        if {k: r.get(k) for k in SCORE_KEYS} != before:
            changed += 1
            print(r["design"], r["question"], r["seed"], before["outcome"], "->", r["outcome"],
                  "| untrue", before.get("untrue"), "->", r.get("untrue"))
    PATH.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    print(f"{changed} of {len(rows)} rows changed")


if __name__ == "__main__":
    main()
