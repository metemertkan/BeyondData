"""Episode 6: the continuous designs in real time, as a check on the replay's clock.

poll, cdc, same_db and built run against the record for `minutes` of wall-clock time while a writer saves articles
through the application: a wording edit every 10 seconds, and at minute 7 a burst of 300 saves one after another
(a bulk publish). Embeddings are computed for real (new text, so the cache doesn't help). A prober checks every
pending article every half second and records when the index first holds its current chunks.

    uv run python -m sync.realtime --design cdc --minutes 20
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import time
from pathlib import Path

from sync import index as ix
from sync import kb, score
from sync.designs import DESIGNS
from sync.embed import Embedder
from sync.record import Record
from sync.kb import FILLER

ROOT = Path(__file__).resolve().parent.parent
EDIT_EVERY = 10
BURST_AT = 420          # minute 7: between two polls, not on one
BURST = 300
POLL_EVERY = 300
CDC_EVERY = 1.0


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()   # microseconds, as now() in Postgres


def edited(row: dict, rng: random.Random, n: int) -> dict:
    """A wording edit that the month never made: one filler sentence swapped for another, plus a marker."""
    body = row["body"]
    for kind, variants in FILLER.items():
        for v in variants:
            if v in body:
                other = rng.choice([x for x in variants if x != v])
                return row | {"body": body.replace(v, other, 1) + f"\n\nLast reviewed: revision {n}."}
    return row | {"body": body + f"\n\nLast reviewed: revision {n}."}


def run(design: str, minutes: float, out: Path, seed: int = 11, size: str = "pilot") -> dict:
    data = kb.load(size)   # the help center at the start of the month (the same for pilot and full run)
    rng = random.Random(seed)
    rec_w, rec_d, rec_p = Record(), Record(), Record()       # writer, design, prober: one connection each
    client_d, client_p = ix.connect(), ix.connect()
    import tempfile
    emb_d = Embedder(Path(tempfile.mkdtemp()) / "empty.sqlite")   # no cache: every chunk the design asks for is computed
    d = DESIGNS[design](rec_d, client_d, emb_d)
    rec_w.reset(data["articles"], slot=d.uses_slot)
    d.start(data["articles"])
    probe = DESIGNS[design](rec_p, client_p, Embedder())       # reads the same index
    if design == "same_db":
        probe.pg = ix.PgChunks(rec_p.c)
        from pgvector.psycopg import register_vector
        register_vector(rec_w.c)
    else:
        probe.coll = client_p.collections.get(d.coll.name)
    live = {a["id"]: a for a in data["articles"]}
    lock = threading.Lock()
    pending: dict[int, float] = {}
    lags: list[dict] = []
    saves: list[dict] = []
    stop = threading.Event()
    t_start = time.time()

    def writer():
        hook = d.app_hook()
        ids = sorted(live)
        n = 0
        next_edit, burst_done = t_start, False
        while not stop.is_set() and time.time() - t_start < minutes * 60:
            now = time.time()
            batch = []
            if not burst_done and now - t_start >= BURST_AT:
                batch, burst_done = rng.sample(ids, BURST), True
            elif now >= next_edit:
                batch, next_edit = [rng.choice(ids)], next_edit + EDIT_EVERY
            for aid in batch:
                n += 1
                row = edited(live[aid], rng, n)
                t0 = time.time()
                rec_w.save(row, now_iso(), hook=hook)
                t1 = time.time()
                with lock:
                    live[aid] = row
                    pending.setdefault(aid, t1)
                saves.append({"article": aid, "save_s": round(t1 - t0, 3), "burst": len(batch) > 1, "t": t1 - t_start})
            time.sleep(0.05)

    def worker():
        last_poll = now_iso()
        next_poll = t_start + POLL_EVERY
        while not stop.is_set():
            if design == "poll":
                if time.time() >= next_poll:
                    now_s = now_iso()
                    d.last = last_poll
                    job = d.tick("every", now_s)
                    last_poll, next_poll = now_s, next_poll + POLL_EVERY
                    if job:
                        _, apply, _ = job.prepare()
                        apply()
                time.sleep(0.5)
            elif design in ("cdc", "built"):
                for job in d.on_event({}):
                    _, apply, _ = job.prepare()
                    apply()
                time.sleep(CDC_EVERY)
            else:
                time.sleep(0.5)

    def prober():
        while not stop.is_set():
            with lock:
                items = list(pending.items())
            for aid, t1 in items:
                has_all, _ = score.in_sync(probe.of_article(aid), live[aid])
                if has_all:
                    with lock:
                        if pending.get(aid) == t1:
                            del pending[aid]
                            lags.append({"article": aid, "lag_s": round(time.time() - t1, 2), "t": t1 - t_start})
            time.sleep(0.5)

    threads = [threading.Thread(target=f, daemon=True) for f in (writer, worker, prober)]
    for th in threads:
        th.start()
    threads[0].join()
    end = time.time() + POLL_EVERY + 120          # let the design catch up: one more poll, or the CDC backlog
    while pending and time.time() < end:
        time.sleep(1)
    stop.set()
    for th in threads[1:]:
        th.join(timeout=30)
    res = {"design": design, "minutes": minutes, "burst_at": BURST_AT, "burst": BURST, "saves": len(saves), "synced": len(lags), "never": len(pending),
           "lags": lags, "save_times": saves, "embedded": emb_d.requested, "computed": emb_d.computed,
           "compute_s": round(emb_d.compute_s, 1)}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"realtime_{design}.json").write_text(json.dumps(res, indent=1))
    for c in (client_d, client_p):
        c.close()
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True, choices=["poll", "cdc", "same_db", "built"])
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--size", default="pilot")
    a = ap.parse_args()
    r = run(a.design, a.minutes, ROOT / "results" / "ep06" / a.size, size=a.size)
    import statistics as st
    lag = sorted(x["lag_s"] for x in r["lags"])
    q = lambda p: lag[min(len(lag) - 1, int(p * len(lag)))] if lag else None  # noqa: E731
    print(json.dumps({"design": r["design"], "saves": r["saves"], "synced": r["synced"], "never": r["never"],
                      "lag_p50": q(0.5), "lag_p95": q(0.95), "lag_max": lag[-1] if lag else None,
                      "save_p50": st.median(x["save_s"] for x in r["save_times"]) if r["save_times"] else None,
                      "computed": r["computed"], "compute_s": r["compute_s"]}))


if __name__ == "__main__":
    main()
