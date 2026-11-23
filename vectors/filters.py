"""Episode 3 data: filter fields on Episode 2's million passages, the filter each question uses, and exact
filtered ground truth.

    uv run python -m vectors.filters --prepare     # data/ep03/fields.npy + exact_{pilot,full}.npz

Six fields per passage (seed 7). Random, nested like an org chart: project (1,000 values, ~0.1% each),
team = project // 10 (~1%), dept = project // 100 (~10%), region = project // 500 (~50%). Topical: spherical
k-means of the passage vectors, topic (100 clusters) and subtopic (1,000 clusters). Each question filters on the
value of its first labeled passage, so the answer is always inside the filter.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import cached_property

import numpy as np

from vectors.data import DIR as EP2_DIR, FULL, K, ROOT, SEED, Data

DIR = ROOT / "data" / "ep03"
FIELDS = ["region", "dept", "team", "project", "topic", "subtopic"]
RANDOM = ["region", "dept", "team", "project"]
TOPICAL = ["topic", "subtopic"]
CONDS = ["none"] + FIELDS
SELECTIVITY = {"region": "50%", "dept": "10%", "team": "1%", "project": "0.1%", "topic": "~1%", "subtopic": "~0.1%"}


def spherical_kmeans(x: np.ndarray, k: int, seed: int, iters: int = 20, sample: int = 200_000) -> np.ndarray:
    """Cluster unit vectors by cosine; returns the label of every row of x. Trained on a seeded sample."""
    rng = np.random.default_rng(seed)
    train = np.asarray(x[np.sort(rng.choice(len(x), min(sample, len(x)), replace=False))])
    cent = train[rng.choice(len(train), k, replace=False)].copy()

    def assign(rows: np.ndarray) -> np.ndarray:
        out = np.empty(len(rows), np.int64)
        for s in range(0, len(rows), 50_000):
            out[s: s + 50_000] = np.argmax(np.asarray(rows[s: s + 50_000]) @ cent.T, axis=1)
        return out

    for it in range(iters):
        lab = assign(train)
        sums = np.zeros_like(cent)
        np.add.at(sums, lab, train)
        counts = np.bincount(lab, minlength=k)
        empty = np.flatnonzero(counts == 0)
        sums[empty] = train[rng.choice(len(train), len(empty), replace=False)]  # reseed empty clusters
        cent = sums / np.linalg.norm(sums, axis=1, keepdims=True)
        print(f"  k-means {k}: iteration {it + 1}/{iters}, empty {len(empty)}", flush=True)
    return assign(x)


def prepare_fields() -> np.ndarray:
    rng = np.random.default_rng(SEED)
    project = rng.integers(0, 1000, FULL)
    corpus = np.load(EP2_DIR / "corpus.npy")
    fields = np.zeros((FULL, len(FIELDS)), np.int16)
    fields[:, 0], fields[:, 1], fields[:, 2], fields[:, 3] = project // 500, project // 100, project // 10, project
    fields[:, 4] = spherical_kmeans(corpus, 100, SEED + 1)
    fields[:, 5] = spherical_kmeans(corpus, 1000, SEED + 2)
    np.save(DIR / "fields.npy", fields)
    return fields


def topk_over(qv: np.ndarray, corpus: np.ndarray, rows: np.ndarray, k: int = K) -> np.ndarray:
    """Exact top-k corpus rows (from `rows`) for each query vector; -1 pads when rows has fewer than k."""
    top = np.full((len(qv), k), -1, np.int64)
    best = np.full((len(qv), k), -np.inf, np.float32)
    for s in range(0, len(rows), 100_000):
        r = rows[s: s + 100_000]
        scores = qv @ np.asarray(corpus[r]).T
        kk = min(k, len(r))
        cand = np.argpartition(-scores, kk - 1, axis=1)[:, :kk] if kk < len(r) else np.tile(np.arange(len(r)), (len(qv), 1))
        allr = np.concatenate([top, r[cand]], 1)
        alls = np.concatenate([best, np.take_along_axis(scores, cand, 1)], 1)
        keep = np.argsort(-alls, axis=1, kind="stable")[:, :k]
        top, best = np.take_along_axis(allr, keep, 1), np.take_along_axis(alls, keep, 1)
    top[~np.isfinite(best)] = -1
    return top


def prepare_exact(size: str) -> None:
    d = Data(size)
    fields = np.load(DIR / "fields.npy")
    corpus = np.load(EP2_DIR / "corpus.npy")
    anchors = anchor_rows(d)
    in_size = np.zeros(FULL, bool)
    in_size[d.rows] = True
    out = {}
    for j, f in enumerate(FIELDS):
        values = fields[anchors, j].astype(np.int64)
        ids = np.full((len(values), K), -1, np.int64)
        sizes = np.zeros(len(values), np.int64)
        for v in np.unique(values):
            qs = np.flatnonzero(values == v)
            rows = np.flatnonzero(in_size & (fields[:, j] == v))
            sizes[qs] = len(rows)
            ids[qs] = topk_over(d.queries[qs], corpus, rows)
        out[f"{f}_value"], out[f"{f}_size"], out[f"{f}_ids"] = values, sizes, ids
        print(f"exact {size} {f}: median filter size {int(np.median(sizes)):,}, min {sizes.min():,}", flush=True)
    np.savez(DIR / f"exact_{size}.npz", **out)


def anchor_rows(d: Data) -> np.ndarray:
    """Each question's first labeled passage (lowest row number); its field values are the question's filters."""
    lab = d.meta["labels"]
    return np.array([min(lab[q]) for q in d.meta["query_ids"]])


@dataclass
class Filters:
    size: str

    @cached_property
    def data(self) -> Data:
        return Data(self.size)

    @cached_property
    def fields(self) -> np.ndarray:
        """(1M, 6) int16: every passage's value for each field, in FIELDS order; row number = passage id."""
        return np.load(DIR / "fields.npy")

    @cached_property
    def _exact(self):
        return np.load(DIR / f"exact_{self.size}.npz")

    def value(self, cond: str) -> np.ndarray:
        return self._exact[f"{cond}_value"]

    def size_of(self, cond: str) -> np.ndarray:
        if cond == "none":
            return np.full(len(self.data.queries), len(self.data.rows))
        return self._exact[f"{cond}_size"]

    def exact(self, cond: str) -> np.ndarray:
        return self.data.exact[:, :K] if cond == "none" else self._exact[f"{cond}_ids"]

    def expected(self, cond: str) -> np.ndarray:
        """How many results a full answer has: min(10, passages matching the filter)."""
        return np.minimum(K, self.size_of(cond))

    def matches(self, cond: str, ids: np.ndarray) -> np.ndarray:
        """Per question, how many returned ids (not -1) actually match the filter."""
        if cond == "none":
            return (ids >= 0).sum(1)
        j = FIELDS.index(cond)
        vals = np.where(ids >= 0, self.fields[np.clip(ids, 0, FULL - 1), j], -1)
        return ((vals == self.value(cond)[:, None]) & (ids >= 0)).sum(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--exact-only", action="store_true")
    a = ap.parse_args()
    DIR.mkdir(parents=True, exist_ok=True)
    if a.prepare and not a.exact_only:
        prepare_fields()
    if a.prepare or a.exact_only:
        for s in ("pilot", "full"):
            prepare_exact(s)
