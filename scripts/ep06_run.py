"""Episode 6: replay the month into each design, then ask the model.

    uv run python -m scripts.ep06_run --size pilot                    # every design, retrieval only
    uv run python -m scripts.ep06_run --size pilot --designs cdc poll
    uv run python -m scripts.ep06_run --size pilot --answers          # the model's replies to every logged context

Writes results/ep06/<size>/<design>.json (jobs, audits, sync times) and <design>.questions.jsonl (the 4 chunks each
question got, classified), and with --answers results/ep06/<size>/answers.jsonl (one reply per distinct prompt).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sync import index as ix
from sync import kb
from sync.designs import ORDER
from sync.embed import Embedder
from sync.record import Record
from sync.replay import Replay

ROOT = Path(__file__).resolve().parent.parent


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def replay(size: str, designs: list[str]) -> None:
    data = kb.load(size)
    out = ROOT / "results" / "ep06" / size
    emb = Embedder()
    record = Record()
    client = ix.connect()
    try:
        for name in designs:
            log(f"{name}: start")
            res = Replay(name, data, record, client, emb, out, log=log).run()
            log(f"{name}: done", json.dumps({k: res[k] for k in ("initial", "month", "final", "wall_s")}))
    finally:
        client.close()


def calibrate() -> None:
    """Embedding speed on the help center's own chunks, with an empty cache (every chunk computed)."""
    import tempfile
    from sync.record import chunks
    texts = [d.page_content for a in kb.load("full")["articles"] for d in chunks(a)]
    emb = Embedder(Path(tempfile.mkdtemp()) / "empty.sqlite")
    emb.model()
    emb.vectors(texts[:64])                       # warm-up
    t = time.time()
    emb.vectors(texts[64:])
    s = time.time() - t
    n = len(texts) - 64
    res = {"chunks": n, "seconds": round(s, 1), "chunks_per_s": round(n / s, 1),
           "mean_chars": round(sum(map(len, texts)) / len(texts))}
    (ROOT / "results" / "ep06" / "calibration.json").write_text(json.dumps(res, indent=1))
    log("calibration", res)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"])
    ap.add_argument("--designs", nargs="*", default=ORDER)
    ap.add_argument("--answers", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args()
    if a.calibrate:
        calibrate()
    elif a.answers:
        from sync.answer import answer_all
        answer_all(a.size, a.designs, log=log)
    else:
        replay(a.size, a.designs)


if __name__ == "__main__":
    main()
