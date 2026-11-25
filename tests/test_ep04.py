"""Episode 4: the compression helpers and knob mappings, on small synthetic data (no database needed)."""
import numpy as np

from scripts import ep04_vectors as ev
from scripts.ep04_run import GRID, check_questions, sweep_questions
from vectors.compressed import ENGINES, MilvusCompressed, PgCompressed
from vectors.nomic import shorten


def _unit(n, d, seed):
    x = np.random.default_rng(seed).normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_scalar_quantization_error_shrinks_with_levels():
    x = _unit(1000, 32, 1)
    lo, hi = ev.minmax(x)
    e8 = np.abs(ev.scalar(x, lo, hi, 256) - x).max()
    e4 = np.abs(ev.scalar(x, lo, hi, 16) - x).max()
    assert e8 <= (hi - lo).max() / 255 / 2 + 1e-6 and e8 < e4


def test_sign_dot_is_hamming():
    x, y = _unit(1, 64, 2), _unit(1, 64, 3)
    hamming = int(((x > 0) != (y > 0)).sum())
    assert ev.sign(x) @ ev.sign(y).T == 64 - 2 * hamming


def test_top_merge_keeps_best_with_ties_by_id():
    ev.TOP = 3
    try:
        i, s = ev.top_merge(np.array([[5, 9]]), np.array([[0.5, 0.1]], np.float32),
                            np.array([[2, 7]]), np.array([[0.5, 0.9]], np.float32))
    finally:
        ev.TOP = 100
    assert i.tolist() == [[7, 2, 5]]


def test_rescoring_recovers_the_exact_top_10():
    corpus, q = _unit(400, 16, 4), _unit(5, 16, 5)
    exact = np.argsort(-(q @ corpus.T), axis=1)[:, :10]
    noisy = np.argsort(-(q @ (corpus + 0.3 * _unit(400, 16, 6)).T), axis=1)
    got = ev.rescored(noisy, q, corpus, 400)
    assert (got == exact).all()


def test_matryoshka_shorten_is_unit_length_prefix():
    v = np.random.default_rng(7).normal(size=(3, 768)).astype(np.float32)
    s = shorten(v, 256)
    assert s.shape == (3, 256) and np.allclose(np.linalg.norm(s, axis=1), 1)
    assert np.allclose(s / s[:, :1], v[:, :256] / v[:, :1], rtol=1e-4)


def test_every_database_has_a_float32_reference_and_23_deployments_in_all():
    assert sum(len(e.deployments) for e in ENGINES.values()) == 23
    for e in ENGINES.values():
        assert any(d.startswith("float32") for d in e.deployments.values())


def test_knob_mappings():
    pg = PgCompressed()
    pg.deployment, pg._knob = "bit", None
    assert "LIMIT 40) t" in pg._sql(10)  # the README's 4x when nothing is set
    pg._knob = 200
    assert "LIMIT 200) t" in pg._sql(10)
    m = MilvusCompressed()
    m.deployment = "ivf_rabitq"
    assert min(m.NLIST, 8 * max(1, 500 // 10)) == 128 and GRID[-1] == 500


def test_question_samples_are_seeded_and_disjoint_from_tuning():
    class D:
        tune, test = np.arange(0, 1000), np.arange(1000, 3452)
    a, b = sweep_questions(D), sweep_questions(D)
    assert (a == b).all() and len(a) == 2000
    chk = check_questions(D)
    assert len(chk) == 200 and not set(chk) & set(D.tune) and set(chk) <= set(a)
