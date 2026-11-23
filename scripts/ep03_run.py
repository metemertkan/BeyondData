"""Episode 3 run: filtered search, one database at a time, the same steps for each.

    taskset -c 6-11,18-23 uv run python -m scripts.ep03_run --size pilot --db all
    taskset -c 6-11,18-23 uv run python -m scripts.ep03_run --size full --db qdrant

For each deployment (a fresh container and load), each option measured on it, each search-knob value and each of
the seven conditions (no filter + six fields): top-10 ids and latency per question. Writes
results/ep03/<size>/<db>.json (times, sizes, settings, plans) and <db>.npz (arrays keyed
"<option>__<knob>__<cond>_ids|_lat"; knob "d" = no search parameter). Metrics come later, from
scripts/ep03_summary.py.
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

from vectors.data import K
from vectors.engines import disk_bytes
from vectors.filtered import ENGINES, compose
from vectors.filters import CONDS, Filters

ROOT = Path(__file__).resolve().parent.parent
GRID = [None, 64, 128, 256, 512, 1024]
BATCH = 1_000
WARMUP = 50                 # tuning questions per condition before each cell
GUARD_FIRST, GUARD_MS, GUARD_KEEP = 100, 250, 100  # a cell averaging > 250 ms over its first 100 stops there
SWEEP_TEST = 1_000         # non-default knob cells: all tuning questions + this many test questions (seeded)
PILOT_QUESTIONS = 600
NO_KNOB = {("elasticsearch", "exact")}  # exact search has no candidate list to sweep
PLANCACHE_COND, PLANCACHE_KNOB, PLANCACHE_N = "team", 256, 100  # amendment 4


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sweep_questions(data, qs: np.ndarray) -> np.ndarray:
    """Questions for cells at a non-default knob: every tuning question, plus a seeded sample of test questions."""
    test = np.intersect1d(data.test, qs)
    pick = np.random.default_rng(7).choice(test, min(SWEEP_TEST, len(test)), replace=False)
    return np.sort(np.concatenate([np.intersect1d(data.tune, qs), pick]))


def fmt(knob) -> str:
    return 'd' if knob is None else str(knob)


def key(option, knob, cond) -> str:
    return f"{option}__{fmt(knob)}__{cond}"


def run_cell(E, F: Filters, cond: str, qs: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    n = len(F.data.queries)
    ids = np.full((n, K), -1, np.int64)
    lat = np.full(n, np.nan)
    qv, val = F.data.queries, (None if cond == "none" else F.value(cond))
    in_run = set(qs.tolist())
    warm = [i for i in F.data.tune if i in in_run][:WARMUP]
    for i in warm:
        E.search(qv[i], K, cond, None if val is None else val[i])
    sampled = False
    for j, i in enumerate(qs):
        t = time.perf_counter()
        r = E.search(qv[i], K, cond, None if val is None else val[i])
        lat[i] = time.perf_counter() - t
        ids[i, : len(r)] = r[:K]
        if j + 1 == GUARD_FIRST and np.nanmean(lat) * 1000 > GUARD_MS:
            sampled = True
        if sampled and j + 1 >= GUARD_KEEP:
            break
    return ids, lat, sampled


def plancache_check(E, F: Filters, arrays: dict) -> dict:
    """Amendment 4 (pgvector): what an app gets when it raises ef_search on a connection that already ran its queries.

    The same 100 tuning questions filtered on team, on one connection: (a) as shipped; (b) after SET hnsw.ef_search
    on that connection; (c) after DEALLOCATE ALL on it. Each step records the plan EXPLAIN shows (planned afresh),
    the plan the prepared statement ran with (EXPLAIN EXECUTE), and its generic/custom plan counts.
    """
    cond, qs = PLANCACHE_COND, F.data.tune[:PLANCACHE_N]
    qv, val = F.data.queries, F.value(PLANCACHE_COND)
    n = len(qv)
    E.set_knob(None)  # a new connection, as shipped
    out: dict = {"cond": cond, "knob": PLANCACHE_KNOB, "questions": int(len(qs)), "steps": {}}
    steps = [("a_shipped", None), ("b_set", f"SET hnsw.ef_search = {PLANCACHE_KNOB}"), ("c_deallocate", "DEALLOCATE ALL")]
    for step, sql in steps:
        if sql:
            E.c.execute(sql, prepare=False)
        ids, lat = np.full((n, K), -1, np.int64), np.full(n, np.nan)
        for i in qs:
            t = time.perf_counter()
            r = E.search(qv[i], K, cond, val[i])
            lat[i] = time.perf_counter() - t
            ids[i, : len(r)] = r[:K]
        arrays[f"plancache__{step}_ids"], arrays[f"plancache__{step}_lat"] = ids, lat
        i0 = qs[0]
        out["steps"][step] = {"sql": sql, "explain": E.plan(qv[i0], cond, val[i0]),
                              "ran": E.prepared_plan(qv[i0], cond, val[i0]), "prepared": E.prepared_counts(cond),
                              "ef_search": E.c.execute("SHOW hnsw.ef_search", prepare=False).fetchone()[0]}
        got = (ids[qs] >= 0).sum(1)
        log("pgvector", "plancache", step, f"p50 {np.nanmedian(lat) * 1000:.1f} ms, mean returned {got.mean():.2f},",
            json.dumps({k: v for k, v in out["steps"][step].items() if k != "sql"}))
    return out


def save_container_log(db: str, size: str, tag: str) -> None:
    out = ROOT / "results" / "ep03" / size / f"{db}.{tag}.container.log"
    name = f"bd3-{ENGINES[db].service}"
    r = subprocess.run(["docker", "logs", "--tail", "3000", name], capture_output=True, text=True)
    state = subprocess.run(["docker", "inspect", name, "--format",
                            "oom_killed={{.State.OOMKilled}} exit={{.State.ExitCode}} running={{.State.Running}}"],
                           capture_output=True, text=True).stdout
    out.write_text(state + "\n" + r.stdout + r.stderr)


def run(db: str, size: str) -> None:
    out_dir = ROOT / "results" / "ep03" / size
    out_dir.mkdir(parents=True, exist_ok=True)
    F = Filters(size)
    data = F.data
    qs = np.arange(len(data.queries)) if size == "full" else np.arange(PILOT_QUESTIONS)
    sweep_qs = sweep_questions(data, qs)
    res: dict = {"db": db, "size": size, "passages": int(len(data.rows)), "questions": int(len(qs)),
                 "started": time.strftime("%F %T"), "deployments": {}}
    arrays: dict[str, np.ndarray] = {}
    E = ENGINES[db]()

    def save():
        np.savez_compressed(out_dir / f"{db}.npz", **arrays)
        (out_dir / f"{db}.json").write_text(json.dumps(res, indent=2, default=str))

    for dep, options in E.deployments.items():
        dres: dict = {"options": {}}
        res["deployments"][dep] = dres
        log(db, dep, "fresh container")
        compose("down", "-v", "--remove-orphans", cwd=ROOT)
        compose("up", "-d", E.service, cwd=ROOT)
        E = ENGINES[db]()
        t = time.time()
        E.connect()
        dres["startup_s"] = round(time.time() - t, 1)
        E.setup_deployment(dep)
        t = time.time()
        for s in range(0, len(data.rows), BATCH):
            rows = data.rows[s: s + BATCH]
            E.load_batch(rows, np.asarray(data.corpus[rows]), F.fields[rows])
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
        dres["disk_bytes_after_load"] = disk_bytes(E)
        log(db, dep, f"load {dres['load_s']} s, index {dres['index_wait_s']} s, settle {dres['settle_s']} s, "
                     f"count {dres['count']:,}")
        if db == "weaviate":
            dres["shipped_strategy"] = E.shipped_strategy()

        for option in options:
            if db == "weaviate" and option == dres.get("shipped_strategy"):
                log(db, option, "is the shipped strategy: measured as default")
                continue
            ores: dict = {}
            E.set_knob(None)
            t = time.time()
            ores["apply"] = E.apply(option)
            ores["apply_s"] = round(time.time() - t, 1)
            ores["filter_settings"] = E.filter_settings()
            grid = [None] if (db, option) in NO_KNOB else [g if g is None else min(g, E.knob_max) for g in GRID]
            ores["cells"], ores["plans"] = {}, {}
            for knob in grid:
                E.set_knob(knob)
                if db == "pgvector":  # the plan can change with ef_search, so record it at every value
                    ores["plans"][fmt(knob)] = {c: [E.plan(data.queries[i], c, None if c == "none" else F.value(c)[i])
                                                    for i in data.tune[:20]] for c in CONDS}
                for cond in CONDS:
                    t = time.time()
                    ids, lat, sampled = run_cell(E, F, cond, qs if knob is None else sweep_qs)
                    k = key(option, knob, cond)
                    arrays[f"{k}_ids"], arrays[f"{k}_lat"] = ids, lat
                    ran = ~np.isnan(lat)
                    got = (ids[ran] >= 0).sum(1)
                    ores["cells"][k] = {"sampled": sampled, "ran": int(ran.sum()), "wall_s": round(time.time() - t, 1)}
                    if db == "pgvector":  # amendment 4: the plan the cell's statement ran with, and how it got it
                        i0 = data.tune[0]
                        v0 = None if cond == "none" else F.value(cond)[i0]
                        ores["cells"][k]["ran_plan"] = E.prepared_plan(data.queries[i0], cond, v0)
                        ores["cells"][k]["prepared"] = E.prepared_counts(cond)
                    log(db, option, f"{E.knob}={knob} {cond}: p50 {np.nanmedian(lat) * 1000:.1f} ms, "
                                    f"mean returned {got.mean():.2f}, short {(got < F.expected(cond)[ran]).mean():.1%}"
                                    f"{' (sampled)' if sampled else ''}")
            E.set_knob(None)
            dres["options"][option] = ores
            save()
            if db == "pgvector" and option == "default":  # before the B-tree indexes exist
                dres["plancache_check"] = plancache_check(E, F, arrays)
                save()
        dres["disk_bytes_end"] = disk_bytes(E)
        save_container_log(db, size, dep)
        try:
            E.close()
        except Exception:
            pass
    res["finished"] = time.strftime("%F %T")
    save()
    compose("stop", E.service, cwd=ROOT)
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
            traceback.print_exc()
            log(name, "FAILED", repr(e))
            save_container_log(name, a.size, "failed")
            compose("stop", ENGINES[name].service, cwd=ROOT, check=False)
    sys.exit(0)
