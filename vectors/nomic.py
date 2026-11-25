"""Episode 4: the same passages and questions embedded with a Matryoshka-trained open model (nomic-embed-text-v1.5).

    uv run --with onnxruntime --with tokenizers --with huggingface_hub python -m vectors.nomic --prepare

Episode 2's vectors come from Cohere embed-english-v3, which was trained for int8 and binary output but not for
shorter vectors. nomic-embed-text-v1.5 (137M parameters, 768-d, Apache 2.0) was trained with Matryoshka
representation learning for 768/512/256/128/64 dimensions. It runs on CPU here (ONNX, fp32 weights) at about
9 passages a second (3 hours), so it embeds the 100,000-passage pilot subset (every labeled passage plus a seeded
sample), not the million. Recipe from the model card: prefixes "search_document: " / "search_query: ", mean pooling, then
layer norm; to shorten, keep the first d dimensions and L2-normalize. Stored: the layer-normed 768-d vectors
(float32), so every shorter size is a slice. Also stored: Cohere's vectors and exact ground truth for the same subset.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from vectors.data import DIR as EP2, Data

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "ep04"
REPO = "nomic-ai/nomic-embed-text-v1.5"
REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"  # pinned: the snapshot the episode used
DIM = 768
DIMS = (768, 512, 256, 128, 64)
MAX_TOKENS = 512


def _model():
    import onnxruntime as ort
    from huggingface_hub import snapshot_download
    from tokenizers import Tokenizer
    snap = Path(snapshot_download(REPO, revision=REVISION, allow_patterns=["onnx/model.onnx", "tokenizer.json"]))
    tok = Tokenizer.from_file(str(snap / "tokenizer.json"))
    tok.enable_truncation(MAX_TOKENS)
    tok.enable_padding()
    so = ort.SessionOptions()
    so.intra_op_num_threads, so.inter_op_num_threads = 12, 1
    return tok, ort.InferenceSession(str(snap / "onnx" / "model.onnx"), so, providers=["CPUExecutionProvider"])


def embed(texts: list[str], tok, sess, batch: int = 32, log_every: int = 2000) -> np.ndarray:
    """Mean-pooled, layer-normed 768-d vectors (not yet L2-normalized), in the order given. Batches are formed
    from length-sorted texts so padding stays small."""
    out = np.zeros((len(texts), DIM), np.float32)
    order = np.argsort([len(t) for t in texts], kind="stable")
    t0, done = time.time(), 0
    for s in range(0, len(texts), batch):
        idx = order[s: s + batch]
        enc = tok.encode_batch([texts[i] for i in idx])
        ids = np.array([e.ids for e in enc], np.int64)
        mask = np.array([e.attention_mask for e in enc], np.int64)
        h = sess.run(None, {"input_ids": ids, "token_type_ids": np.zeros_like(ids), "attention_mask": mask})[0]
        m = mask[..., None].astype(np.float32)
        pooled = (h * m).sum(1) / np.maximum(m.sum(1), 1e-9)
        mu, sd = pooled.mean(1, keepdims=True), pooled.std(1, keepdims=True)
        out[idx] = (pooled - mu) / np.sqrt(sd ** 2 + 1e-5)  # F.layer_norm without weights
        done += len(idx)
        if done // log_every != (done - len(idx)) // log_every:
            r = done / (time.time() - t0)
            print(f"  {done:,}/{len(texts):,}  {r:.1f}/s  eta {(len(texts) - done) / r / 60:.0f} min", flush=True)
    return out


def shorten(v: np.ndarray, d: int) -> np.ndarray:
    """Matryoshka: the first d dimensions, L2-normalized (works on the stored layer-normed vectors)."""
    x = np.ascontiguousarray(v[:, :d], np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def exact_top(corpus: np.ndarray, queries: np.ndarray, k: int = 100) -> np.ndarray:
    scores = queries @ corpus.T
    cand = np.argpartition(-scores, k, axis=1)[:, :k]
    cs = np.take_along_axis(scores, cand, 1)
    return np.take_along_axis(cand, np.argsort(-cs, axis=1, kind="stable"), 1)


def prepare() -> None:
    import pyarrow.parquet as pq
    DIR.mkdir(parents=True, exist_ok=True)
    data = Data("pilot")
    rows = data.rows  # corpus row numbers of the 100k subset, in insert order
    p = pq.read_table(EP2 / "passages.parquet", columns=["title", "text"]).to_pylist()
    docs = [f"search_document: {p[r]['title']} {p[r]['text']}" for r in rows]
    qtext = pq.read_table(EP2 / "raw" / "nq" / "queries" / "test.parquet", columns=["_id", "text"]).to_pylist()
    assert [q["_id"] for q in qtext] == data.meta["query_ids"]
    tok, sess = _model()
    t = time.time()
    qv = embed([f"search_query: {q['text']}" for q in qtext], tok, sess)
    np.save(DIR / "nomic_queries.npy", qv)
    print(f"questions: {len(qv):,} in {time.time() - t:.0f} s", flush=True)
    t = time.time()
    cv = embed(docs, tok, sess)
    np.save(DIR / "nomic_corpus.npy", cv)
    np.save(DIR / "rows.npy", rows)
    print(f"passages: {len(cv):,} in {time.time() - t:.0f} s", flush=True)
    # exact top 100 at each length for both models, on the same subset (local ids 0..n-1 index into rows)
    out = {}
    for d in DIMS:
        out[f"nomic_{d}"] = exact_top(shorten(cv, d), shorten(qv, d))
    coh = np.asarray(data.corpus[rows])
    for d in (1024, 512, 256, 128, 64):
        out[f"cohere_{d}"] = exact_top(shorten(coh, d), shorten(data.queries, d))
    np.savez(DIR / "exact_subset.npz", **out)
    print("exact ground truth written", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--check", action="store_true", help="compare 8 passages against Ollama's nomic-embed-text")
    a = ap.parse_args()
    if a.check:
        import httpx
        import pyarrow.parquet as pq
        p = pq.read_table(EP2 / "passages.parquet", columns=["title", "text"]).slice(0, 8).to_pylist()
        docs = [f"search_document: {r['title']} {r['text']}" for r in p]
        tok, sess = _model()
        mine = shorten(embed(docs, tok, sess), DIM)
        # Ollama returns mean-pooled, L2-normalized vectors (no layer norm): compare before layer norm by undoing
        # nothing; layer norm changes direction only by the mean shift, so report both cosines
        oll = np.array(httpx.post("http://localhost:11434/api/embed", json={
            "model": "nomic-embed-text", "input": docs, "options": {"num_ctx": 2048}}, timeout=600).json()["embeddings"])
        ln = (oll - oll.mean(1, keepdims=True)) / oll.std(1, keepdims=True)
        ln /= np.linalg.norm(ln, axis=1, keepdims=True)
        print("cosine vs Ollama after the same layer norm:", np.round((mine * ln).sum(1), 4))
    if a.prepare:
        prepare()
