"""Episode 2: the data split, the ground truth and the metrics (no database needed)."""
from __future__ import annotations

import numpy as np
import pytest

from scripts.ep02_summary import ndcg_hit, recall
from vectors.data import DIR, FULL, HOLDOUT, Data

needs_data = pytest.mark.skipif(not (DIR / "meta.json").exists(), reason="run `python -m vectors.data --prepare` first")


@needs_data
def test_split_and_sizes():
    full, pilot = Data("full"), Data("pilot")
    assert len(full.rows) == FULL and len(pilot.rows) == 100_000
    assert set(pilot.rows) <= set(full.rows)
    assert not set(full.tune) & set(full.test) and len(full.tune) + len(full.test) == 3452
    # every labeled passage is in both sizes, so nDCG is comparable between them
    labeled = set().union(*full.labels)
    assert labeled <= set(pilot.rows.tolist())
    m = full.meta
    assert len(m["holdout_doc_ids"]) == HOLDOUT and not set(m["holdout_doc_ids"]) & set(m["doc_ids"])
    assert len(set(m["doc_ids"])) == FULL


@needs_data
def test_exact_ground_truth_is_exact():
    for d in (Data("full"), Data("pilot")):
        rng = np.random.default_rng(1)
        for q in rng.choice(len(d.queries), 3, replace=False):
            scores = np.asarray(d.corpus[d.rows]) @ d.queries[q] if d.size == "pilot" else d.corpus @ d.queries[q]
            top = d.rows[np.argsort(-scores)[:10]] if d.size == "pilot" else np.argsort(-scores)[:10]
            assert set(top) == set(d.exact[q, :10])


@needs_data
def test_vectors_have_unit_length():
    d = Data("full")
    norms = np.linalg.norm(np.asarray(d.corpus[:5000]), axis=1)
    assert np.allclose(norms, 1, atol=1e-3)  # so cosine, inner product and L2 rank the same way
    assert np.allclose(np.linalg.norm(d.queries, axis=1), 1, atol=1e-3)


def test_recall_counts_overlap_with_exact_top10():
    exact = np.array([list(range(10)), list(range(10, 20))])
    ids = np.array([list(range(10)), [10, 11, 12, 13, 14, 99, 98, 97, 96, 95]])
    assert recall(ids, exact, [0]) == 1.0
    assert recall(ids, exact, [1]) == 0.5
    assert recall(ids, exact, [0, 1]) == 0.75


def test_ndcg_and_hit():
    labels = [{3}, {50}, {0, 1}]
    ids = np.array([list(range(10))] * 3)
    nd, hit = ndcg_hit(ids, labels, [0])
    assert nd == pytest.approx(1 / np.log2(5)) and hit == 1.0  # relevant at rank 4
    nd, hit = ndcg_hit(ids, labels, [1])
    assert nd == 0.0 and hit == 0.0
    nd, _ = ndcg_hit(ids, labels, [2])
    assert nd == pytest.approx(1.0)  # both relevant passages at ranks 1 and 2


def test_lost_counts():
    from scripts.ep02_summary import lost_counts
    exact = np.array([list(range(10)), list(range(10, 20))])
    ids = np.array([list(range(1, 11)), list(range(10, 20))])
    labels = [{0}, {15}]
    assert lost_counts(ids, exact, labels, [0, 1]) == (1, 1)  # q0 misses the nearest, which is also its answer
