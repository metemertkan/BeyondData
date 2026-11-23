"""Episode 2 data: one million Natural Questions passages with Cohere embed-english-v3 vectors (1024-d).

    uv run python -m vectors.data --prepare     # raw parquet -> data/ep02/{corpus.npy, ...} + exact ground truth

Source: huggingface.co/datasets/CohereLabs/beir-embed-english-v3 (nq/), downloaded without an account by
vectors/download.sh. Every passage labeled relevant for a test question is in the million; the rest is a
seeded random sample. 1,000 more passages, outside the million, are held back for the write test.
Ids in every database are row numbers: 0..N-1 for the corpus, 1_000_000.. for the held-back passages.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "ep02" / "raw" / "nq"
DIR = ROOT / "data" / "ep02"
SEED = 7
FULL = 1_000_000
PILOT = 100_000
HOLDOUT = 1_000
HOLDOUT_BASE = 1_000_000
TUNE = 1_000  # tuning questions; the remaining 2,452 are test questions
K = 10
GT_K = 100


def _corpus_files() -> list[Path]:
    return sorted((RAW / "corpus").glob("*.parquet"))


def _emb(table) -> np.ndarray:
    col = table.column("emb").combine_chunks()
    return col.flatten().to_numpy(zero_copy_only=False).astype(np.float32).reshape(len(col), -1)


def prepare() -> None:
    import pyarrow.parquet as pq

    rng = np.random.default_rng(SEED)
    files = _corpus_files()
    ids = [pq.read_table(f, columns=["_id"]).column("_id").to_pylist() for f in files]
    all_ids = [i for chunk in ids for i in chunk]
    n_all = len(all_ids)
    pos = {d: i for i, d in enumerate(all_ids)}

    queries = pq.read_table(RAW / "queries" / "test.parquet")
    qrels = pq.read_table(RAW / "qrels" / "test.parquet").to_pylist()
    relevant = sorted({pos[r["corpus_id"]] for r in qrels if r["score"] > 0})
    rel_set = set(relevant)
    others = rng.permutation(np.array([i for i in range(n_all) if i not in rel_set]))
    full_rows = np.array(relevant + others[: FULL - len(relevant)].tolist())
    holdout_rows = others[FULL - len(relevant): FULL - len(relevant) + HOLDOUT]
    pilot_rows = set(relevant + others[: PILOT - len(relevant)].tolist())
    order = rng.permutation(len(full_rows))  # insert order: relevant passages are not all at the start
    full_rows = full_rows[order]

    # read vectors and text for the selected rows, file by file
    want = {int(r): j for j, r in enumerate(full_rows)}
    hold = {int(r): j for j, r in enumerate(holdout_rows)}
    corpus = np.lib.format.open_memmap(DIR / "corpus.npy", mode="w+", dtype=np.float32, shape=(FULL, 1024))
    held = np.zeros((HOLDOUT, 1024), np.float32)
    doc_ids, titles, texts = [None] * FULL, [None] * FULL, [None] * FULL
    held_ids = [None] * HOLDOUT
    base = 0
    for f in files:
        t = pq.read_table(f)
        emb = _emb(t)
        _id, title, text = (t.column(c).to_pylist() for c in ("_id", "title", "text"))
        for local in range(len(emb)):
            g = base + local
            if g in want:
                j = want[g]
                corpus[j] = emb[local]
                doc_ids[j], titles[j], texts[j] = _id[local], title[local], text[local]
            elif g in hold:
                held[hold[g]] = emb[local]
                held_ids[hold[g]] = _id[local]
        base += len(emb)
        print(f"read {f.name}: {len(emb):,} rows")
    corpus.flush()
    np.save(DIR / "holdout.npy", held)

    qv = _emb(queries)
    q_ids = queries.column("_id").to_pylist()
    split = rng.permutation(len(q_ids))
    tune_idx, test_idx = np.sort(split[:TUNE]), np.sort(split[TUNE:])
    row_of = {d: j for j, d in enumerate(doc_ids)}
    labels: dict[str, list[int]] = {}
    for r in qrels:
        if r["score"] > 0:
            labels.setdefault(r["query_id"], []).append(row_of[r["corpus_id"]])
    np.save(DIR / "queries.npy", qv)
    pilot_mask = np.array([int(r) in pilot_rows for r in full_rows])
    np.save(DIR / "pilot_mask.npy", pilot_mask)
    (DIR / "meta.json").write_text(json.dumps({
        "source": "CohereLabs/beir-embed-english-v3 nq (embed-english-v3, 1024-d)",
        "seed": SEED, "corpus_rows_in_source": n_all, "full": FULL, "pilot": int(pilot_mask.sum()),
        "relevant_passages": len(relevant), "holdout": HOLDOUT,
        "query_ids": q_ids, "tune": tune_idx.tolist(), "test": test_idx.tolist(),
        "labels": {q: sorted(v) for q, v in labels.items()},
        "doc_ids": doc_ids, "holdout_doc_ids": held_ids,
    }))
    import pyarrow as pa
    pq.write_table(pa.table({"row": np.arange(FULL), "doc_id": doc_ids, "title": titles, "text": texts}),
                   DIR / "passages.parquet")
    for name, mask in (("full", None), ("pilot", pilot_mask)):
        exact(name, mask)


def exact(name: str, mask: np.ndarray | None) -> None:
    """Exact top-100 by brute force (inner product = cosine: every vector here has unit length)."""
    corpus = np.load(DIR / "corpus.npy", mmap_mode="r")
    qv = np.load(DIR / "queries.npy")
    rows = np.arange(len(corpus)) if mask is None else np.flatnonzero(mask)
    top = np.zeros((len(qv), GT_K), np.int64)
    best = np.full((len(qv), GT_K), -np.inf, np.float32)
    for s in range(0, len(rows), 100_000):
        r = rows[s: s + 100_000]
        scores = qv @ np.asarray(corpus[r]).T
        cand = np.argpartition(-scores, GT_K, axis=1)[:, :GT_K]
        cs = np.take_along_axis(scores, cand, 1)
        allr = np.concatenate([top, r[cand]], 1)
        alls = np.concatenate([best, cs], 1)
        keep = np.argsort(-alls, axis=1, kind="stable")[:, :GT_K]
        top, best = np.take_along_axis(allr, keep, 1), np.take_along_axis(alls, keep, 1)
    np.savez(DIR / f"exact_{name}.npz", ids=top, scores=best)
    print(f"exact {name}: {len(rows):,} passages, {len(qv):,} questions")


@dataclass
class Data:
    size: str  # "full" or "pilot"

    @cached_property
    def meta(self) -> dict:
        return json.loads((DIR / "meta.json").read_text())

    @cached_property
    def rows(self) -> np.ndarray:
        """Corpus row numbers in this size, in insert order (they are also the ids in every database)."""
        if self.size == "full":
            return np.arange(FULL)
        return np.flatnonzero(np.load(DIR / "pilot_mask.npy"))

    @cached_property
    def corpus(self) -> np.ndarray:
        return np.load(DIR / "corpus.npy", mmap_mode="r")

    @cached_property
    def queries(self) -> np.ndarray:
        return np.load(DIR / "queries.npy")

    @cached_property
    def holdout(self) -> np.ndarray:
        return np.load(DIR / "holdout.npy")

    @cached_property
    def exact(self) -> np.ndarray:
        return np.load(DIR / f"exact_{self.size}.npz")["ids"]

    @cached_property
    def tune(self) -> np.ndarray:
        return np.array(self.meta["tune"])

    @cached_property
    def test(self) -> np.ndarray:
        return np.array(self.meta["test"])

    @cached_property
    def labels(self) -> list[set[int]]:
        """Relevant corpus rows per question (all of them are in both sizes)."""
        lab = self.meta["labels"]
        return [set(lab.get(q, [])) for q in self.meta["query_ids"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        DIR.mkdir(parents=True, exist_ok=True)
        prepare()
