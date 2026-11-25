"""Episode 4 run: vector compression, one database and one deployment at a time, the same steps for each.

    taskset -c 6-11,18-23 uv run python -m scripts.ep04_run --size pilot --db all
    taskset -c 6-11,18-23 uv run python -m scripts.ep04_run --size full --db qdrant [--deployments binary,turbo1]

Per deployment (a fresh container, volume and load):
  1. load, wait until indexed, settle; read back the settings; disk and memory (docker stats) after loading;
  2. as shipped (no search parameters): every question; then each value of the knob (candidates c) on all tuning
     questions plus a seeded 1,000 test questions;
  3. the memory ladder: restart under each memory limit (no swap) after dropping the data from the page cache,
     read the data directory once inside the container, warm up on tuning questions, then the deploy-check sample
     (200 test questions, seed 7) at the settings Act 3 can pick: as shipped; "tuned" (the smallest c reaching 0.995
     on the tuning questions: target 0.99 plus half the distance to 1); "tuned_hi" (reaching 0.9975, for a target of
     0.995; amendment 1). Stops below the first limit at which no setting runs.
Writes results/ep04/<size>/<db>__<deployment>.json and .npz (arrays "<cell>_ids", "<cell>_lat"; cells "shipped",
"c<c>", "b<GiB>__shipped", "b<GiB>__tuned", "b<GiB>__tuned_hi"). Metrics come later, from scripts/ep04_summary.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from vectors.compressed import ENGINES, compose, container, restart_with_budget, state
from vectors.data import K, Data
from vectors.engines import mem_mib

ROOT = Path(__file__).resolve().parent.parent
GRID = [20, 30, 50, 100, 200, 500]       # candidates c
BATCH = 1_000
WARMUP = 200                              # tuning questions before the first cell of a deployment
WARMUP_CELL = 50                          # tuning questions before every other cell
GUARD_FIRST, GUARD_MS = 100, 250          # a cell averaging > 250 ms over its first 100 questions stops there
SWEEP_TEST = 1_000
TUNED = {"tuned": 0.995, "tuned_hi": 0.9975}  # target + half the distance to 1, for targets 0.99 and 0.995
CHECK_N, CHECK_SEED = 200, 7              # the deploy-check sample (Episodes 2-3)
LADDER = {"full": [8, 4, 2, 1, 0.5], "pilot": [2, 1, 0.5]}
LADDER_WARMUP, LADDER_GUARD_FIRST = 200, 50


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sweep_questions(data: Data) -> np.ndarray:
    pick = np.random.default_rng(7).choice(data.test, min(SWEEP_TEST, len(data.test)), replace=False)
    return np.sort(np.concatenate([data.tune, pick]))


def check_questions(data: Data) -> np.ndarray:
    return np.sort(np.random.default_rng(CHECK_SEED).choice(sweep_questions(data)[len(data.tune):], CHECK_N,
                                                            replace=False))


def recall(ids: np.ndarray, exact: np.ndarray, qs: np.ndarray) -> float:
    return float(np.mean([len(set(ids[i]) & set(exact[i, :K])) / K for i in qs]))


def run_cell(E, data: Data, qs, warm, guard_first=GUARD_FIRST):
    """Top-10 ids and latency per question; stops after guard_first questions if they average over GUARD_MS.
    A failed request (the container died, a timeout) ends the cell and is returned as the error."""
    n = len(data.queries)
    ids, lat = np.full((n, K), -1, np.int64), np.full(n, np.nan)
    qv = data.queries
    try:
        for i in warm:
            E.search(qv[i], K)
        sampled = False
        for j, i in enumerate(qs):
            t = time.perf_counter()
            r = E.search(qv[i], K)
            lat[i] = time.perf_counter() - t
            ids[i, : len(r)] = r[:K]
            if j + 1 == guard_first and np.nanmean(lat) * 1000 > GUARD_MS:
                sampled = True
                break
    except Exception as e:  # noqa: BLE001
        return ids, lat, False, f"{type(e).__name__}: {e}"[:300]
    return ids, lat, sampled, None


def disk_usage(E) -> tuple[int, int]:
    """(allocated, apparent) bytes of the volume. Allocated is what the disk holds: some databases preallocate
    sparse files whose apparent size is far larger (Qdrant at 100,000 vectors: 5-6 GiB apparent in the pilot)."""
    from vectors.compressed import volume
    out = subprocess.run(["docker", "run", "--rm", "-v", f"{volume(E)}:/v:ro", "alpine:3.20", "sh", "-c",
                          "du -sk /v; du -sb /v"], capture_output=True, text=True, check=True).stdout.split()
    return int(out[0]) * 1024, int(out[2])


def save_container_log(E, path: Path) -> None:
    name = container(E)
    r = subprocess.run(["docker", "logs", "--tail", "2000", name], capture_output=True, text=True)
    path.write_text(json.dumps(state(E)) + "\n" + r.stdout + r.stderr)


def ladder(E, data: Data, size: str, tuned: dict, arrays: dict, dres: dict, exact) -> None:
    qs, warm = check_questions(data), data.tune[:LADDER_WARMUP]
    settings, seen = [("shipped", None)], set()
    for label, t in tuned.items():  # a c already in the list is measured once (the summary reads it from there)
        if t["c"] is not None and t["c"] not in seen:
            settings.append((label, t["c"]))
            seen.add(t["c"])
    restart_each = getattr(E, "knob_needs_restart", False)
    out = dres["ladder"] = {"questions": int(len(qs)), "tuned_c": tuned["tuned"]["c"], "tuned": tuned,
                            "settings": dict(settings), "steps": {}}
    for gib in LADDER[size]:
        step: dict = {}
        out["steps"][str(gib)] = step
        ran_any = False
        for si, (label, c) in enumerate(settings):
            if si == 0 or restart_each:
                if restart_each:  # Chroma: store the setting, the restart applies it
                    if state(E)["status"] != "running":
                        break
                    E.store_knob(c)
                t = time.time()
                step[f"restart_{label}"] = r = restart_with_budget(E, gib)
                log(E.name, E.deployment, f"{gib} GiB: restart {r.get('ok')} in {time.time() - t:.0f} s",
                    {k: r.get(k) for k in ("ready_s", "preread_s", "status", "oom_killed", "error")})
                if not r["ok"]:
                    why = {"ok": False, "why": "did not start", **{k: r.get(k) for k in ("oom_killed", "error")}}
                    if restart_each:
                        step[label] = why
                        continue
                    for lab, _ in settings:  # every setting needs this start
                        step[lab] = why
                    break
            if not restart_each:
                E.set_knob(c)
            t = time.time()
            ids, lat, sampled, err = run_cell(E, data, qs, warm if si == 0 or restart_each else warm[:WARMUP_CELL],
                                              guard_first=LADDER_GUARD_FIRST)
            cell = f"b{gib}__{label}"
            arrays[f"{cell}_ids"], arrays[f"{cell}_lat"] = ids, lat
            ran = ~np.isnan(lat)
            st = state(E)
            ok = err is None and not sampled and st["status"] == "running"
            step[label] = {"ok": ok, "c": c, "ran": int(ran.sum()), "sampled": sampled, "error": err, **st,
                           "p50_ms": float(np.nanmedian(lat) * 1000) if ran.any() else None,
                           "recall": recall(ids, exact, qs[ran[qs]]) if ran.any() else None,
                           "mem_mib": mem_mib(E) if st["status"] == "running" else None,
                           "wall_s": round(time.time() - t, 1)}
            ran_any |= ok
            log(E.name, E.deployment, f"{gib} GiB {label}: ok {ok}, p50 {step[label]['p50_ms'] or 0:.1f} ms, "
                f"recall {step[label]['recall'] or 0:.3f}{' (sampled)' if sampled else ''}{' ' + err if err else ''}")
            if st["status"] != "running":
                break
        if not ran_any:
            log(E.name, E.deployment, f"stops at {gib} GiB")
            break


def run_deployment(db: str, dep: str, size: str) -> None:
    out_dir = ROOT / "results" / "ep04" / size
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"{db}__{dep}"
    data = Data(size)
    exact = data.exact
    sweep_qs = sweep_questions(data)
    E = ENGINES[db]()
    dres: dict = {"db": db, "deployment": dep, "what": E.deployments[dep], "size": size,
                  "passages": int(len(data.rows)), "started": time.strftime("%F %T"), "cells": {}}
    arrays: dict[str, np.ndarray] = {}

    def save():
        np.savez_compressed(f"{stem}.npz", **arrays)
        Path(f"{stem}.json").write_text(json.dumps(dres, indent=2, default=str))

    log(db, dep, "fresh container")
    compose("down", "-v", "--remove-orphans")
    compose("up", "-d", E.service)
    t = time.time()
    E.connect()
    dres["startup_s"] = round(time.time() - t, 1)
    E.setup_deployment(dep)
    t = time.time()
    for s in range(0, len(data.rows), BATCH):
        rows = data.rows[s: s + BATCH]
        E.load_batch(rows, np.asarray(data.corpus[rows]))
        if (s // BATCH) % 100 == 0:
            log(db, dep, f"  {s + len(rows):,} loaded, {time.time() - t:.0f} s")
    dres["load_s"] = round(time.time() - t, 1)
    t = time.time()
    dres["indexed"] = E.wait_indexed()
    dres["index_wait_s"] = round(time.time() - t, 1)
    t = time.time()
    dres["settle"] = E.settle()
    dres["settle_s"] = round(time.time() - t, 1)
    dres["count"] = int(E.count())
    dres["settings"] = E.settings()
    dres["disk_bytes"], dres["disk_bytes_apparent"] = disk_usage(E)
    dres["mem_mib_after_load"] = mem_mib(E)
    log(db, dep, f"load {dres['load_s']} s, index {dres['index_wait_s']} s, settle {dres['settle_s']} s, "
                 f"count {dres['count']:,}, disk {dres['disk_bytes'] / 2**30:.2f} GiB, "
                 f"mem {dres['mem_mib_after_load']:.0f} MiB")
    save()

    all_qs = np.arange(len(data.queries))
    for c in [None] + GRID:
        E.set_knob(c)
        cell = "shipped" if c is None else f"c{c}"
        t = time.time()
        qs = all_qs if c is None else sweep_qs
        warm = data.tune[:WARMUP] if c is None else data.tune[:WARMUP_CELL]
        ids, lat, sampled, err = run_cell(E, data, qs, warm)
        if err:
            raise RuntimeError(f"{cell}: {err}")
        arrays[f"{cell}_ids"], arrays[f"{cell}_lat"] = ids, lat
        ran = ~np.isnan(lat)
        tune_ran = data.tune[ran[data.tune]]
        dres["cells"][cell] = {"c": c, "ran": int(ran.sum()), "sampled": sampled, "wall_s": round(time.time() - t, 1),
                               "tune_recall": recall(ids, exact, tune_ran) if len(tune_ran) else None,
                               "p50_ms": float(np.nanmedian(lat) * 1000)}
        if db == "pgvector":
            dres["cells"][cell]["plan"] = E.plan(data.queries[data.tune[0]])
        log(db, dep, f"{cell}: p50 {dres['cells'][cell]['p50_ms']:.1f} ms, tuning recall "
                     f"{dres['cells'][cell]['tune_recall'] or 0:.4f}{' (sampled)' if sampled else ''}")
        save()
    dres["mem_mib_after_queries"] = mem_mib(E)

    tuned = {}
    for label, level in TUNED.items():
        ok = [c for c in GRID if not dres["cells"][f"c{c}"]["sampled"]
              and (dres["cells"][f"c{c}"]["tune_recall"] or 0) >= level]
        if ok:
            tuned[label] = {"c": min(ok), "level": level, "reached": True}
        else:  # still measured in the ladder (the best this deployment can do), but Act 3 can't pick it
            best = max((c for c in GRID if not dres["cells"][f"c{c}"]["sampled"]),
                       key=lambda c: dres["cells"][f"c{c}"]["tune_recall"], default=None)
            tuned[label] = {"c": best, "level": level, "reached": False}
    dres["tuned"] = tuned
    log(db, dep, f"tuned: {tuned}")
    E.set_knob(None)
    try:
        ladder(E, data, size, tuned, arrays, dres, exact)
    finally:
        save_container_log(E, Path(f"{stem}.container.log"))
        dres["finished"] = time.strftime("%F %T")
        save()
        try:
            E.close()
        except Exception:  # noqa: BLE001
            pass
        compose("down", "-v", "--remove-orphans", check=False)
    log(db, dep, "done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    ap.add_argument("--db", default="all", help="one name, a comma list, or all")
    ap.add_argument("--deployments", default="", help="comma list (default: all of each database's)")
    ap.add_argument("--redo", action="store_true", help="rerun deployments that already have results")
    a = ap.parse_args()
    names = list(ENGINES) if a.db == "all" else a.db.split(",")
    for name in names:
        for dep in (a.deployments.split(",") if a.deployments else list(ENGINES[name].deployments)):
            done = ROOT / "results" / "ep04" / a.size / f"{name}__{dep}.json"
            if done.exists() and not a.redo and "finished" in json.loads(done.read_text()):
                log(name, dep, "already done")
                continue
            try:
                run_deployment(name, dep, a.size)
            except Exception as e:  # keep going with the next deployment; the log has the traceback
                traceback.print_exc()
                log(name, dep, "FAILED", repr(e))
                compose("down", "-v", "--remove-orphans", check=False)
    sys.exit(0)
