"""Episode 2 run: one database at a time, the same steps for each.

    taskset -c 6-11,18-23 uv run python -m scripts.ep02_run --size pilot --db all
    taskset -c 6-11,18-23 uv run python -m scripts.ep02_run --size full --db qdrant

Writes results/ep02/<size>/<db>.json (times, sizes, settings, throughput, write test) and <db>.npz (top-10 ids
and latency for every question at the default and at every sweep value). Metrics come later, from
scripts/ep02_summary.py, so nothing here decides what counts as good.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from vectors.data import HOLDOUT_BASE, K, Data
from vectors.engines import COMPOSE, ENGINES, disk_bytes, mem_mib

ROOT = Path(__file__).resolve().parent.parent
GRID = [10, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024]
BATCH = 1_000
WARMUP = 500
QPS_PROCS = 16
QPS_SECONDS = 30


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def run_queries(E, qv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ids = np.full((len(qv), K), -1, np.int64)
    lat = np.zeros(len(qv), np.float64)
    for i, v in enumerate(qv):
        t = time.perf_counter()
        r = E.search(v, K)
        lat[i] = time.perf_counter() - t
        ids[i, : len(r)] = r[:K]
    return ids, lat


def _qps_worker(db: str, knob, qv: np.ndarray, seconds: float, start: float, out) -> None:
    E = ENGINES[db]()
    E.connect()
    if E.knob_is_global:
        E._knob = knob
    else:
        E.set_knob(knob)
    while time.time() < start:
        time.sleep(0.01)
    n, i, errors, first, end = 0, 0, 0, "", start + seconds
    while time.time() < end:
        try:
            E.search(qv[i % len(qv)], K)
            n += 1
        except Exception as e:  # counted, not fatal: the error rate is a result too
            errors += 1
            first = first or repr(e)[:300]
            time.sleep(0.1)
        i += 1
    out.put((n, errors, first))
    try:
        E.close()
    except Exception:
        pass


def throughput(db: str, knob, qv: np.ndarray) -> dict:
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    start = time.time() + 15  # time for every process to connect
    ps = [ctx.Process(target=_qps_worker, args=(db, knob, np.roll(qv, 97 * j, 0), QPS_SECONDS, start, out))
          for j in range(QPS_PROCS)]
    for p in ps:
        p.start()
    got = [out.get(timeout=QPS_SECONDS + 300) for _ in ps]
    for p in ps:
        p.join()
    errors = sum(g[1] for g in got)
    return {"qps": round(sum(g[0] for g in got) / QPS_SECONDS, 1), "errors": errors,
            "first_error": next((g[2] for g in got if g[2]), "")}


def compose(*args, check=True):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True, check=check)


def save_container_log(db: str, size: str) -> None:
    out = ROOT / "results" / "ep02" / size / f"{db}.container.log"
    r = subprocess.run(["docker", "logs", "--tail", "3000", f"bd2-{ENGINES[db].service}"], capture_output=True,
                       text=True)
    state = subprocess.run(["docker", "inspect", f"bd2-{ENGINES[db].service}", "--format",
                            "oom_killed={{.State.OOMKilled}} exit={{.State.ExitCode}} running={{.State.Running}}"],
                           capture_output=True, text=True).stdout
    out.write_text(state + "\n" + r.stdout + r.stderr)


def run(db: str, size: str) -> None:
    out_dir = ROOT / "results" / "ep02" / size
    out_dir.mkdir(parents=True, exist_ok=True)
    data = Data(size)
    E = ENGINES[db]()
    res: dict = {"db": db, "size": size, "passages": int(len(data.rows)), "started": time.strftime("%F %T")}
    arrays: dict[str, np.ndarray] = {}

    log(db, size, "fresh container")
    compose("down", "-v", "--remove-orphans")
    compose("up", "-d", E.service)
    t = time.time()
    E.connect()
    res["startup_s"] = round(time.time() - t, 1)
    E.setup()

    log(db, "loading", len(data.rows))
    t = time.time()
    for s in range(0, len(data.rows), BATCH):
        rows = data.rows[s: s + BATCH]
        E.load_batch(rows, np.asarray(data.corpus[rows]))
        if (s // BATCH) % 100 == 0:
            log(db, f"  {s + len(rows):,} loaded, {time.time() - t:.0f} s")
    res["load_s"] = round(time.time() - t, 1)
    log(db, "waiting until indexed")
    t = time.time()
    res["indexed"] = E.wait_indexed()
    res["index_wait_s"] = round(time.time() - t, 1)
    # recall right after indexing (200 tuning questions, no search parameters), then let background work finish
    E.set_knob(None)
    ex = data.exact[:, :K]
    res["recall_just_indexed"] = round(float(np.mean(
        [len(set(E.search(data.queries[i], K)) & set(ex[i])) / K for i in data.tune[:200]])), 4)
    t = time.time()
    res["settle"] = E.settle()
    res["settle_s"] = round(time.time() - t, 1)
    res["count"] = int(E.count())
    res["settings"] = E.settings()
    log(db, f"load {res['load_s']} s, index {res['index_wait_s']} s, settle {res['settle_s']} s, "
             f"recall just indexed {res['recall_just_indexed']}, count {res['count']:,}")
    time.sleep(10)
    res["mem_after_load_mib"] = round(mem_mib(E), 1)
    res["disk_bytes"] = disk_bytes(E)

    qv = data.queries
    E.set_knob(None)
    run_queries(E, qv[data.tune[:WARMUP]])
    ids, lat = run_queries(E, qv)
    arrays["default_ids"], arrays["default_lat"] = ids, lat
    log(db, f"default: p50 {np.median(lat[data.test]) * 1000:.1f} ms")

    exact = data.exact[:, :K]
    tune_recall = {}
    for v in [g for g in GRID if g <= E.knob_max]:
        E.set_knob(v)
        run_queries(E, qv[data.tune[:100]])  # settle after the change
        ids, lat = run_queries(E, qv)
        arrays[f"k{v}_ids"], arrays[f"k{v}_lat"] = ids, lat
        rec = np.mean([len(set(ids[i]) & set(exact[i])) / K for i in data.tune])
        tune_recall[v] = round(float(rec), 4)
        log(db, f"{E.knob}={v}: tune recall {rec:.4f}, p50 {np.median(lat[data.test]) * 1000:.1f} ms")
    res["tune_recall"] = tune_recall

    # throughput at the default and at the cheapest sweep values reaching 0.95 and 0.99 on tuning questions
    pick = lambda target: next((v for v, r in tune_recall.items() if r >= target), None)  # noqa: E731
    res["qps"] = {}
    for label, knob in (("default", None), ("r95", pick(0.95)), ("r99", pick(0.99))):
        if label != "default" and knob is None:
            continue
        E.set_knob(knob)
        time.sleep(1)
        res["qps"][label] = {"knob": knob, **throughput(db, knob, qv[data.test])}
        log(db, f"throughput {label} ({knob}): {res['qps'][label]}")
    E.set_knob(None)
    res["mem_after_queries_mib"] = round(mem_mib(E), 1)

    # read your own write: insert one held-back passage, search for it straight away: is it in the top 10?
    hv = data.holdout
    best = np.full(len(hv), -1.0, np.float32)
    for s in range(0, len(data.rows), 100_000):
        best = np.maximum(best, (hv @ np.asarray(data.corpus[data.rows[s: s + 100_000]]).T).max(axis=1))
    dup = best > 0.9999  # an identical passage is already in (kept out of the count, to compare with the pilot)
    now, later, ins, srch = [], [], [], []
    t_write = time.time()
    for j, v in enumerate(hv):
        t = time.perf_counter()
        E.insert_one(HOLDOUT_BASE + j, v)
        ins.append(time.perf_counter() - t)
        t = time.perf_counter()
        now.append(HOLDOUT_BASE + j in E.search(v, K))
        srch.append(time.perf_counter() - t)
    time.sleep(1)
    for j, v in enumerate(hv):
        later.append(HOLDOUT_BASE + j in E.search(v, K))
    keep = ~dup
    res["write_test"] = {"passages": int(keep.sum()), "duplicates_skipped": int(dup.sum()),
                         "found_immediately": int(np.array(now)[keep].sum()),
                         "found_after_1s": int(np.array(later)[keep].sum()),
                         "insert_p50_ms": round(float(np.median(ins)) * 1000, 2),
                         "insert_p99_ms": round(float(np.percentile(ins, 99)) * 1000, 2),
                         "insert_max_ms": round(float(np.max(ins)) * 1000, 2),
                         "search_after_insert_p50_ms": round(float(np.median(srch)) * 1000, 2),
                         "search_after_insert_max_ms": round(float(np.max(srch)) * 1000, 2),
                         "wall_s": round(time.time() - t_write, 1)}
    log(db, "write test", res["write_test"])
    res["disk_bytes_end"] = disk_bytes(E)
    res["finished"] = time.strftime("%F %T")
    E.close()
    np.savez_compressed(out_dir / f"{db}.npz", **arrays)
    (out_dir / f"{db}.json").write_text(json.dumps(res, indent=2, default=str))
    save_container_log(db, size)
    compose("stop", E.service)
    log(db, "done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    ap.add_argument("--db", default="all", help="one name, a comma list, or all")
    a = ap.parse_args()
    names = list(ENGINES) if a.db == "all" else a.db.split(",")
    for name in names:
        try:
            run(name, a.size)
        except Exception as e:  # keep going with the next database; the log has the traceback
            import traceback
            traceback.print_exc()
            log(name, "FAILED", repr(e))
            save_container_log(name, a.size)
            compose("stop", ENGINES[name].service, check=False)
    sys.exit(0)
