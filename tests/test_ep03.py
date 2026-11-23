"""Episode 3: exact filtered top-k, filter checks and k-means, on small synthetic data (no database needed)."""
import numpy as np
import pytest

from scripts.ep03_run import key
from vectors import filters as fl


def _unit(n, d, seed):
    x = np.random.default_rng(seed).normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_topk_over_matches_brute_force_on_a_subset():
    corpus, q = _unit(500, 8, 1), _unit(4, 8, 2)
    rows = np.arange(0, 500, 3)
    got = fl.topk_over(q, corpus, rows, k=10)
    want = rows[np.argsort(-(q @ corpus[rows].T), axis=1)[:, :10]]
    assert (got == want).all()


def test_topk_over_pads_when_the_filter_is_smaller_than_k():
    corpus, q = _unit(50, 8, 3), _unit(2, 8, 4)
    rows = np.array([5, 17, 30])
    got = fl.topk_over(q, corpus, rows, k=10)
    assert sorted(got[0, :3]) == [5, 17, 30] and (got[:, 3:] == -1).all()


def test_spherical_kmeans_finds_separated_groups():
    rng = np.random.default_rng(0)
    centers = _unit(3, 16, 5)
    x = np.concatenate([c + 0.05 * rng.normal(size=(200, 16)) for c in centers]).astype(np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    lab = fl.spherical_kmeans(x, 3, seed=1, iters=10, sample=600)
    groups = [set(lab[i * 200:(i + 1) * 200]) for i in range(3)]
    assert all(len(g) == 1 for g in groups) and len(set.union(*groups)) == 3


def test_matches_and_expected(monkeypatch):
    f = fl.Filters("pilot")
    fields = np.zeros((fl.FULL, len(fl.FIELDS)), np.int16)
    fields[:5, fl.FIELDS.index("team")] = [3, 3, 4, 3, 9]
    f.__dict__["fields"] = fields
    monkeypatch.setattr(f, "value", lambda cond: np.array([3, 4]))
    ids = np.array([[0, 1, 2, -1], [2, 4, -1, -1]])
    assert f.matches("team", ids).tolist() == [2, 1]
    assert f.matches("none", ids).tolist() == [3, 2]


def test_cell_keys():
    assert key("default", None, "team") == "default__d__team"
    assert key("acorn", 256, "none") == "acorn__256__none"


@pytest.mark.skipif(not (fl.DIR / "exact_pilot.npz").exists(), reason="data not prepared")
def test_prepared_filters_hold_the_answer_and_are_nested():
    f = fl.Filters("pilot")
    anchors = fl.anchor_rows(f.data)
    proj = f.fields[:, fl.FIELDS.index("project")].astype(int)
    assert (f.fields[:, 0] == proj // 500).all() and (f.fields[:, 2] == proj // 10).all()
    for j, c in enumerate(fl.FIELDS):
        assert (f.fields[anchors, j] == f.value(c)).all()  # the first labeled passage is inside the filter
        ids = f.exact(c)
        assert (f.matches(c, ids) == (ids >= 0).sum(1)).all()  # exact results all match the filter
        assert ((ids >= 0).sum(1) == f.expected(c)).all()


def test_pg_text_numbers_placeholders_like_psycopg():
    from vectors.filtered import PgFiltered
    sql = "WITH r AS MATERIALIZED (SELECT id, embedding <=> %s AS d FROM docs WHERE team = %s ORDER BY d LIMIT 10) SELECT id"
    assert PgFiltered._pg_text(sql) == sql.replace("<=> %s", "<=> $1").replace("team = %s", "team = $2")
    assert PgFiltered._pg_text("SELECT 1") == "SELECT 1"
