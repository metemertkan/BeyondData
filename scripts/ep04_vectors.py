"""Episode 4, the vectors alone: exact search over compressed representations, no database, no index.

    taskset -c 0-5,12-17 uv run python -m scripts.ep04_vectors --part million
    taskset -c 0-5,12-17 uv run python -m scripts.ep04_vectors --part subset     # needs vectors.nomic --prepare

million: Cohere embed-english-v3 on the million, every question. Each representation ranks the whole corpus; its top
10 is scored as is, and its top c re-scored with the float32 vectors (c = 20, 50, 100).
subset: the 100,000-passage subset, Cohere v3 and nomic-embed-text-v1.5, dimensions full/512/256/128/64 (Matryoshka:
first d, L2-normalized), each as float32, int8 or 1-bit sign codes; re-scored with the full-length float32 vectors
at c = 50 and 100. Ground truth is each model's own exact full-length search.

Writes results/ep04/vectors/<part>.json: per representation, test-question recall@10, nDCG@10, hit@10, answers lost,
and bytes per vector.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from scripts.ep02_summary import lost_counts, ndcg_hit, recall
from vectors.data import K, Data
from vectors.nomic import DIR as NOMIC_DIR, shorten

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "ep04" / "vectors"
CHUNK = 100_000
TOP = 100


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def minmax(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return x.min(0), x.max(0)


def scalar(x: np.ndarray, lo: np.ndarray, hi: np.ndarray, levels: int) -> np.ndarray:
    """Per-dimension min-max scalar quantization, returned decoded (what a float query is scored against)."""
    step = (hi - lo) / (levels - 1)
    code = np.clip(np.rint((x - lo) / step), 0, levels - 1)
    return (lo + code * step).astype(np.float32)


def sign(x: np.ndarray) -> np.ndarray:
    return np.where(x > 0, 1.0, -1.0).astype(np.float32)  # 1 bit per dimension; +-1 dot = d - 2 x Hamming


def unit(x: np.ndarray) -> np.ndarray:
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


def top_merge(top_i, top_s, cand_i, cand_s):
    """Keep the best TOP of (current, candidates) per row, ties by lower id (deterministic)."""
    alli = np.concatenate([top_i, cand_i], 1)
    alls = np.concatenate([top_s, cand_s], 1)
    order = np.lexsort((alli, -alls), axis=1)[:, :TOP]
    return np.take_along_axis(alli, order, 1), np.take_along_axis(alls, order, 1)


def metrics(ids, exact, labels, qs) -> dict:
    nd, hit = ndcg_hit(ids, labels, qs)
    near, lost = lost_counts(ids, exact, labels, qs)
    return {"recall": round(recall(ids, exact, qs), 4), "ndcg": round(nd, 4), "hit": round(hit, 4), "lost": int(lost),
            "nearest_missed": int(near)}


def rescored(cands: np.ndarray, qv: np.ndarray, vecs, c: int) -> np.ndarray:
    """Top 10 after re-scoring each row's first c candidates with the float32 vectors (vecs indexed by id)."""
    out = np.zeros((len(cands), K), np.int64)
    for i in range(len(cands)):
        cc = cands[i, :c]
        s = np.asarray(vecs[np.sort(cc)]) @ qv[i]
        srt = np.sort(cc)
        out[i] = srt[np.lexsort((srt, -s))[:K]]
    return out


def million() -> dict:
    data = Data("full")
    qv, corpus, exact, labels, test = data.queries, data.corpus, data.exact, data.labels, data.test
    n, d = corpus.shape
    log("ranges for scalar quantization")
    lo, hi = np.full(d, np.inf, np.float32), np.full(d, -np.inf, np.float32)
    for s in range(0, n, CHUNK):
        x = np.asarray(corpus[s: s + CHUNK])
        lo, hi = np.minimum(lo, x.min(0)), np.maximum(hi, x.max(0))
    reps = {  # name -> (bytes per vector, query transform, passage transform)
        "float16": (2 * d, lambda q: q, lambda x: x.astype(np.float16).astype(np.float32)),
        "int8": (d, lambda q: q, lambda x: scalar(x, lo, hi, 256)),
        "int4": (d // 2, lambda q: q, lambda x: scalar(x, lo, hi, 16)),
        "1bit_hamming": (d // 8, sign, sign),
        "1bit_float_query": (d // 8, lambda q: q, sign),
        "dims512": (4 * 512, lambda q: unit(q[:, :512]), lambda x: unit(x[:, :512])),
        "dims256": (4 * 256, lambda q: unit(q[:, :256]), lambda x: unit(x[:, :256])),
        "dims128": (4 * 128, lambda q: unit(q[:, :128]), lambda x: unit(x[:, :128])),
    }
    tops = {r: (np.zeros((len(qv), 0), np.int64), np.zeros((len(qv), 0), np.float32)) for r in reps}
    qx = {r: f(qv) for r, (_, f, _) in reps.items()}
    for s in range(0, n, CHUNK):
        x = np.asarray(corpus[s: s + CHUNK])
        for r, (_, _, g) in reps.items():
            sc = qx[r] @ g(x).T
            cand = np.argpartition(-sc, TOP, axis=1)[:, :TOP]
            tops[r] = top_merge(*tops[r], cand + s, np.take_along_axis(sc, cand, 1))
        log(f"  {s + len(x):,} passages")
    out = {"float32": {"bytes": 4 * d, "c10": metrics(exact[:, :K], exact, labels, test)}}
    for r, (nbytes, _, _) in reps.items():
        cands = tops[r][0]
        out[r] = {"bytes": nbytes, "c10": metrics(cands[:, :K], exact, labels, test)}
        for c in (20, 50, 100):
            out[r][f"c{c}"] = metrics(rescored(cands, qv, corpus, c), exact, labels, test)
        log(r, json.dumps(out[r]))
    return out


def subset() -> dict:
    data = Data("pilot")
    rows = np.load(NOMIC_DIR / "rows.npy")
    assert (rows == data.rows).all()
    local = {int(r): j for j, r in enumerate(rows)}
    labels = [{local[x] for x in lab if x in local} for lab in data.labels]
    test = data.test
    ex = np.load(NOMIC_DIR / "exact_subset.npz")
    models = {"cohere": (np.asarray(data.corpus[rows]), data.queries, 1024),
              "nomic": (np.load(NOMIC_DIR / "nomic_corpus.npy"), np.load(NOMIC_DIR / "nomic_queries.npy"), 768)}
    out: dict = {}
    for m, (cv, qv, full) in models.items():
        exact = ex[f"{m}_{full}"]
        cfull, qfull = shorten(cv, full), shorten(qv, full)
        out[m] = {}
        for d in (full, 512, 256, 128, 64):
            c_d, q_d = shorten(cv, d), shorten(qv, d)
            lo, hi = minmax(c_d)
            for prec, nbytes, qf, cf in (("float32", 4 * d, q_d, c_d),
                                         ("int8", d, q_d, scalar(c_d, lo, hi, 256)),
                                         ("1bit", d // 8, sign(q_d), sign(c_d))):
                sc = qf @ cf.T
                cand = np.argpartition(-sc, TOP, axis=1)[:, :TOP]
                cs = np.take_along_axis(sc, cand, 1)
                cands = np.take_along_axis(cand, np.lexsort((cand, -cs), axis=1), 1)
                key = f"{d}_{prec}"
                out[m][key] = {"dims": d, "precision": prec, "bytes": nbytes,
                               "c10": metrics(cands[:, :K], exact, labels, test)}
                for c in (50, 100):
                    out[m][key][f"c{c}"] = metrics(rescored(cands, qfull, cfull, c), exact, labels, test)
                log(m, key, json.dumps(out[m][key]))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["million", "subset"], required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    res = million() if a.part == "million" else subset()
    (OUT / f"{a.part}.json").write_text(json.dumps(res, indent=2))
    log("written", OUT / f"{a.part}.json")
