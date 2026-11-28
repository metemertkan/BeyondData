"""Episode 6, Act 2: Episode 2's six databases on updates and deletes.

    uv run python -m scripts.ep06_stores --prepare               # replacement vectors from outside the million
    uv run python -m scripts.ep06_stores --size pilot --db qdrant
    uv run python -m scripts.ep06_stores --size full             # all six, one at a time

For each database, in a fresh container (docker-compose.ep06-stores.yml, its own project), with Episode 2's setup:
load, index and settle as Episode 2 did; then

1. fresh:        recall@10 of 1,000 test questions against exact search, p50 latency, count, memory, disk;
2. add again:    1,000 ids sent again with new vectors through Episode 2's insert call. What does it hold then
                 (searched by the new vector and by the old one, and the count)? Then the documented upsert;
3. update:       200 ids, one at a time, with the documented upsert; searched by the new vector and the old one
                 every 50 ms until the new one is found and the old one gone (up to 5 s);
4. delete:       200 ids, one at a time; searched by their vector every 50 ms until gone (up to 5 s);
5. churn:        three rounds, each replacing 10% of the vectors with the documented upsert; after each, the same
                 measurements as fresh, against exact search on the vectors as they are now, with recall split by
                 whether a question's true top 10 holds a replaced vector;
6. clean-up:     the database's documented clean-up (or a wait), then measured again.

An update gives an id the vector of a passage outside Episode 2's million (the source has 2.68 million).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from vectors.churn import COMPOSE, STORES
from vectors.data import DIR as EP2, RAW, Data, _corpus_files, _emb
from vectors.engines import disk_bytes, mem_mib

ROOT = Path(__file__).resolve().parent.parent
REPL = ROOT / "data" / "ep06" / "replacements.npy"
K = 10
N_QUESTIONS = 1000
N_AGAIN, N_VIS = 1000, 200
ROUNDS, SHARE = 3, 0.10
BATCH = 1000
SEED = 7


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def prepare(n: int = 310_000) -> None:
    """Vectors of passages that are neither in Episode 2's million nor held back, picked at random."""
    import pyarrow.parquet as pq
    meta = json.loads((EP2 / "meta.json").read_text())
    used = set(meta["doc_ids"]) | set(meta["holdout_doc_ids"])
    rng = np.random.default_rng(SEED)
    out, got = np.zeros((n, 1024), np.float32), 0
    for f in _corpus_files():
        t = pq.read_table(f, columns=["_id", "emb"])
        ids = t.column("_id").to_pylist()
        free = [i for i, d in enumerate(ids) if d not in used]
        pick = [i for i in free if rng.random() < 0.2][: n - got]
        if pick:
            out[got: got + len(pick)] = _emb(t.take(pick))
            got += len(pick)
        log(f"{f.name}: {got:,} of {n:,}")
        if got >= n:
            break
    assert got == n, got
    REPL.parent.mkdir(parents=True, exist_ok=True)
    np.save(REPL, out)


def compose(*args, check=True):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True, check=check)


class State:
    """The vectors each id holds now, for exact search."""

    def __init__(self, data: Data):
        self.rows = np.asarray(data.rows)
        self.pos = {int(r): j for j, r in enumerate(self.rows)}
        log(f"reading {len(self.rows):,} vectors")
        self.vec = np.ascontiguousarray(np.asarray(data.corpus[self.rows]), dtype=np.float32)
        self.alive = np.ones(len(self.rows), bool)
        self.replaced = np.zeros(len(self.rows), bool)

    def set(self, ids, vecs):
        j = [self.pos[int(i)] for i in ids]
        self.vec[j] = vecs
        self.replaced[j] = True

    def kill(self, ids):
        self.alive[[self.pos[int(i)] for i in ids]] = False

    def exact(self, qv: np.ndarray) -> np.ndarray:
        top = np.full((len(qv), K), -1, np.int64)
        best = np.full((len(qv), K), -np.inf, np.float32)
        for s in range(0, len(self.rows), 100_000):
            sc = qv @ self.vec[s: s + 100_000].T
            sc[:, ~self.alive[s: s + 100_000]] = -np.inf
            cand = np.argpartition(-sc, K, axis=1)[:, :K]
            cs = np.take_along_axis(sc, cand, 1)
            allr = np.concatenate([top, self.rows[s: s + 100_000][cand]], 1)
            alls = np.concatenate([best, cs], 1)
            keep = np.argsort(-alls, axis=1, kind="stable")[:, :K]
            top, best = np.take_along_axis(allr, keep, 1), np.take_along_axis(alls, keep, 1)
        return top


def measure(E, st: State, qv: np.ndarray, label: str) -> dict:
    ex = st.exact(qv)
    ids, lat = [], []
    for v in qv:
        t = time.perf_counter()
        ids.append(E.search(v, K))
        lat.append(time.perf_counter() - t)
    rec = np.array([len(set(a) & set(b.tolist())) / K for a, b in zip(ids, ex)])
    touched = np.array([st.replaced[[st.pos[int(x)] for x in b]].any() for b in ex])
    out = {"label": label, "recall": round(float(rec.mean()), 4), "p50_ms": round(float(np.median(lat)) * 1000, 2),
           "p95_ms": round(float(np.percentile(lat, 95)) * 1000, 2),
           "recall_with_replaced": round(float(rec[touched].mean()), 4) if touched.any() else None,
           "recall_without_replaced": round(float(rec[~touched].mean()), 4) if (~touched).any() else None,
           "questions_with_replaced": int(touched.sum()), "count": int(E.count()), "expected_count": int(st.alive.sum()),
           "mem_mib": round(mem_mib(E), 1), "disk_bytes": disk_bytes(E), "stats": E.stats()}
    log(E.name, label, {k: out[k] for k in ("recall", "recall_with_replaced", "recall_without_replaced", "p50_ms",
                                            "count", "expected_count")})
    return out


def found(E, i: int, v: np.ndarray) -> bool:
    return int(i) in [int(x) for x in E.search(v, K)]


def run(db: str, size: str) -> dict:
    out_dir = ROOT / "results" / "ep06" / size / "stores"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = Data(size)
    E = STORES[db]()
    res: dict = {"db": db, "size": size, "started": time.strftime("%F %T"), "upsert_call": E.upsert_call,
                 "maintain_call": E.maintain_call}
    R = np.load(REPL, mmap_mode="r")
    st = State(data)
    qv = data.queries[data.test[:N_QUESTIONS]]
    rng = np.random.default_rng(SEED)
    perm = st.rows[rng.permutation(len(st.rows))]
    r_next = 0

    def take(n):
        nonlocal r_next
        v = np.asarray(R[r_next: r_next + n], dtype=np.float32)
        r_next += n
        return v

    log(db, size, "fresh container")
    compose("down", "-v", "--remove-orphans")
    compose("up", "-d", E.service)
    E.connect()
    E.setup()
    t = time.time()
    for s in range(0, len(st.rows), BATCH):
        E.load_batch(st.rows[s: s + BATCH], st.vec[s: s + BATCH])
    res["load_s"] = round(time.time() - t, 1)
    t = time.time()
    res["indexed"] = E.wait_indexed()
    res["settle"] = E.settle()
    res["index_settle_s"] = round(time.time() - t, 1)
    log(db, f"loaded {len(st.rows):,} in {res['load_s']} s, indexed and settled in {res['index_settle_s']} s")
    res["fresh"] = measure(E, st, qv, "fresh")

    # 2. add again, through the insert call each quickstart uses
    ids = perm[:N_AGAIN]
    old = st.vec[[st.pos[int(i)] for i in ids]].copy()
    new = take(N_AGAIN)
    before = E.count()
    try:
        E.load_batch(ids, new)
        err = None
    except Exception as e:  # a refusal is a result
        err = f"{type(e).__name__}: {str(e)[:300]}"
    time.sleep(5)          # past every database's visibility window (Episode 2: all found within a second)
    sample = range(0, N_AGAIN, 5)
    res["add_again"] = {"error": err, "count_before": int(before), "count_after": int(E.count()),
                        "found_by_new": sum(found(E, ids[j], new[j]) for j in sample),
                        "found_by_old": sum(found(E, ids[j], old[j]) for j in sample), "searched": len(sample)}
    E.upsert(ids, new)
    time.sleep(5)
    st.set(ids, new)
    res["add_again"] |= {"after_upsert_count": int(E.count()),
                         "after_upsert_found_by_new": sum(found(E, ids[j], new[j]) for j in sample),
                         "after_upsert_found_by_old": sum(found(E, ids[j], old[j]) for j in sample)}
    log(db, "add again", res["add_again"])

    # 3. update visibility, one id at a time
    vis = []
    ids = perm[N_AGAIN: N_AGAIN + N_VIS]
    new = take(N_VIS)
    for i, v in zip(ids, new):
        o = st.vec[st.pos[int(i)]].copy()
        t0 = time.perf_counter()
        E.upsert(np.array([i]), v[None, :])
        w = time.perf_counter() - t0
        t_new = t_old = None
        while time.perf_counter() - t0 < 5 + w and (t_new is None or t_old is None):
            el = time.perf_counter() - t0 - w
            if t_new is None and found(E, i, v):
                t_new = el
            if t_old is None and not found(E, i, o):
                t_old = el
            if t_new is None or t_old is None:
                time.sleep(0.05)
        vis.append({"write_ms": round(w * 1000, 2), "new_s": t_new, "old_gone_s": t_old})
        st.set([i], v[None, :])
    res["update_visibility"] = vis

    # 4. delete visibility, one id at a time
    gone = []
    ids = perm[N_AGAIN + N_VIS: N_AGAIN + 2 * N_VIS]
    for i in ids:
        o = st.vec[st.pos[int(i)]].copy()
        t0 = time.perf_counter()
        E.delete(np.array([i]))
        w = time.perf_counter() - t0
        t_gone = None
        while time.perf_counter() - t0 < 5 + w:
            el = time.perf_counter() - t0 - w
            if not found(E, i, o):
                t_gone = el
                break
            time.sleep(0.05)
        gone.append({"write_ms": round(w * 1000, 2), "gone_s": t_gone})
        st.kill([i])
    res["delete_visibility"] = gone
    summ = lambda xs: {"n": len(xs), "at_once": sum(1 for x in xs if x == 0 or (x is not None and x < 0.001)),  # noqa: E731
                       "within_1s": sum(1 for x in xs if x is not None and x <= 1),
                       "never_5s": sum(1 for x in xs if x is None)}
    log(db, "update: new found", summ([v["new_s"] for v in vis]), "old gone", summ([v["old_gone_s"] for v in vis]),
        "| delete gone", summ([g["gone_s"] for g in gone]))

    # 5. churn
    res["churn"] = []
    alive_ids = lambda: st.rows[st.alive]  # noqa: E731
    for r in range(1, ROUNDS + 1):
        pool = alive_ids()
        ids = rng.choice(pool, int(SHARE * len(st.rows)), replace=False)
        new = take(len(ids))
        t = time.time()
        for s in range(0, len(ids), BATCH):
            E.upsert(ids[s: s + BATCH], new[s: s + BATCH])
        w = time.time() - t
        st.set(ids, new)
        m = measure(E, st, qv, f"round {r}")
        res["churn"].append({"round": r, "replaced": len(ids), "write_s": round(w, 1),
                             "per_s": round(len(ids) / w, 1), **m})
    t = time.time()
    res["maintain"] = E.maintain()
    res["after_cleanup"] = measure(E, st, qv, "after clean-up")
    res["finished"] = time.strftime("%F %T")
    (out_dir / f"{db}.json").write_text(json.dumps(res, indent=1, default=str))
    r2 = subprocess.run(["docker", "logs", "--tail", "2000", f"{E.prefix}-{E.service}"], capture_output=True, text=True)
    (out_dir / f"{db}.container.log").write_text(r2.stdout + r2.stderr)
    E.close()
    compose("stop", E.service)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--size", choices=["pilot", "full"])
    ap.add_argument("--db", nargs="*", default=list(STORES))
    a = ap.parse_args()
    if a.prepare:
        prepare()
        return
    for db in a.db:
        run(db, a.size)
    compose("down", "-v", "--remove-orphans")


if __name__ == "__main__":
    main()
