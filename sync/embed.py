"""Episode 6: the embedding model, BAAI/bge-small-en-v1.5 (fastembed's default) on the CPU, with a cache.

Every design asks for the vectors of the chunks it (re)indexes. The cache keeps one vector per distinct text so
the replay doesn't compute the same chunk again for every design; each design is still charged for every chunk it
asks for (`requested`), and its jobs take that long in the replay's clock (`SECONDS_PER_CHUNK`).
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path

import numpy as np
from langchain_core.embeddings import Embeddings

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "ep06" / "embeddings.sqlite"
MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
THREADS = 12
SECONDS_PER_CHUNK = 1 / 28.9   # calibration, 2026-11-27: 28.9 of the help center's own chunks per second (results/ep06/calibration.json)


def key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Embedder(Embeddings):
    """LangChain `Embeddings` over fastembed, with a persistent cache and a counter of chunks requested."""

    _model = None
    _lock = threading.Lock()

    def __init__(self, cache: Path = CACHE):
        cache.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS v (k TEXT PRIMARY KEY, v BLOB)")
        self.requested = 0          # chunks asked for (documents only), the cost a design is charged
        self.computed = 0           # chunks actually run through the model (cache misses)
        self.compute_s = 0.0

    @classmethod
    def model(cls):
        with cls._lock:
            if cls._model is None:
                from fastembed import TextEmbedding
                cls._model = TextEmbedding(MODEL, threads=THREADS)
        return cls._model

    def _vectors(self, texts: list[str], query: bool = False) -> list[np.ndarray]:
        import time
        keys = [("q:" if query else "") + key(t) for t in texts]
        have = {}
        for i in range(0, len(keys), 500):
            part = keys[i:i + 500]
            rows = self.db.execute(f"SELECT k, v FROM v WHERE k IN ({','.join('?' * len(part))})", part).fetchall()
            have.update({k: np.frombuffer(v, dtype=np.float32) for k, v in rows})
        missing = [(k, t) for k, t in zip(keys, texts) if k not in have]
        if missing:
            uniq = dict(missing)
            t0 = time.time()
            m = self.model()
            items = list(uniq.items())
            vecs = list(m.query_embed([t for _, t in items])) if query else list(m.embed([t for _, t in items], batch_size=32))
            self.compute_s += time.time() - t0
            self.computed += len(items)
            for (k, _), v in zip(items, vecs):
                v = np.asarray(v, dtype=np.float32)
                have[k] = v
            self.db.executemany("INSERT OR REPLACE INTO v VALUES (?, ?)", [(k, have[k].tobytes()) for k, _ in items])
            self.db.commit()
        return [have[k] for k in keys]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.requested += len(texts)
        return [v.tolist() for v in self._vectors(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self._vectors([text], query=True)[0].tolist()

    def vectors(self, texts: list[str]) -> np.ndarray:
        """Document vectors as an array, charged like embed_documents."""
        self.requested += len(texts)
        return np.stack(self._vectors(list(texts))) if texts else np.zeros((0, DIM), np.float32)

    def query(self, text: str) -> np.ndarray:
        return self._vectors([text], query=True)[0]
