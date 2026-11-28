"""Episode 6: the Episode 2 adapters with updates, deletes and each database's own clean-up.

`load_batch` is Episode 2's insert, the call each quickstart uses (pgvector COPY, Qdrant upsert, Milvus insert,
Weaviate insert_many, Elasticsearch bulk index, Chroma add). `upsert` is the call each database documents for
replacing a vector by id; `delete` removes ids; `maintain` is the documented clean-up after many updates (or, where
there is nothing to call, a wait for the background clean-up).
"""
from __future__ import annotations

import time

import numpy as np

from vectors.engines import NAME, Chroma, Elastic, Engine, Milvus, PgVector, Qdrant, Weaviate, _uuid

COMPOSE = ["docker", "compose", "-f", "docker-compose.ep06-stores.yml"]
WAIT_FOR_BACKGROUND_S = 600   # Weaviate and Chroma: two of Weaviate's default 5-minute clean-up cycles


class Churn(Engine):
    prefix, project = "bd6s", "beyonddata-ep06s"
    upsert_call = ""
    maintain_call = ""

    def upsert(self, ids: np.ndarray, vecs: np.ndarray) -> None: ...
    def delete(self, ids: np.ndarray) -> None: ...
    def maintain(self) -> dict: return {}


class PgChurn(PgVector, Churn):
    upsert_call = "INSERT … ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding"
    maintain_call = "VACUUM"

    def upsert(self, ids, vecs):
        with self.c.cursor() as cur:
            cur.executemany(f"INSERT INTO {NAME} (id, embedding) VALUES (%s, %s) "
                            f"ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding",
                            [(int(i), v) for i, v in zip(ids, vecs)])

    def delete(self, ids):
        self.c.execute(f"DELETE FROM {NAME} WHERE id = ANY(%s)", ([int(i) for i in ids],))

    def maintain(self):
        before = self._dead()
        t = time.time()
        self.c.execute(f"VACUUM {NAME}")
        return {"s": round(time.time() - t, 1), "dead_tuples_before": before, "dead_tuples_after": self._dead()}

    def _dead(self):
        return self.c.execute("SELECT n_dead_tup FROM pg_stat_user_tables WHERE relname = %s", (NAME,)).fetchone()[0]

    def stats(self):
        return {"dead_tuples": self._dead(),
                "index_bytes": self.c.execute(f"SELECT pg_indexes_size('{NAME}')").fetchone()[0]}


class QdrantChurn(Qdrant, Churn):
    upsert_call = "upsert (wait=True, the client's default)"
    maintain_call = "none to call: wait until the collection is green (the optimizer vacuums deleted points)"

    def upsert(self, ids, vecs):
        self.load_batch(ids, vecs)

    def delete(self, ids):
        from qdrant_client import models as m
        self.c.delete(NAME, points_selector=m.PointIdsList(points=[int(i) for i in ids]))

    def maintain(self):
        t = time.time()
        out = self.wait_indexed()
        return {"s": round(time.time() - t, 1), **out}

    def stats(self):
        info = self.c.get_collection(NAME)
        return {"segments": info.segments_count, "status": str(info.status), "indexed": info.indexed_vectors_count}


class MilvusChurn(Milvus, Churn):
    upsert_call = "upsert"
    maintain_call = "compact, then wait for the loaded segments to settle"

    def upsert(self, ids, vecs):
        self.c.upsert(NAME, [{"id": int(i), "vector": v} for i, v in zip(ids, vecs.tolist())])

    def delete(self, ids):
        self.c.delete(NAME, ids=[int(i) for i in ids])

    def maintain(self):
        t = time.time()
        job = self.c.compact(NAME)
        while str(self.c.get_compaction_state(job)).lower() not in ("completed", "compactionstate.completed"):
            time.sleep(5)
            if time.time() - t > 3600:
                break
        state = str(self.c.get_compaction_state(job))
        out = self.settle()
        return {"s": round(time.time() - t, 1), "compaction": state, "segments_after": len(self._segments()),
                "settle": out}

    def stats(self):
        return {"loaded_segments": len(self._segments())}


class WeaviateChurn(Weaviate, Churn):
    upsert_call = "insert_many with the same ids (batch import replaces an existing object)"
    maintain_call = f"none to call: wait {WAIT_FOR_BACKGROUND_S // 60} minutes for the tombstone clean-up"

    def upsert(self, ids, vecs):
        self.load_batch(ids, vecs)

    def delete(self, ids):
        from weaviate.classes.query import Filter
        self._c().data.delete_many(where=Filter.by_id().contains_any([_uuid(i) for i in ids]))

    def maintain(self):
        t = time.time()
        self.wait_indexed()
        time.sleep(WAIT_FOR_BACKGROUND_S)
        return {"s": round(time.time() - t, 1)}

    def stats(self):
        return {"vector_queue": self._queue()}


class ElasticChurn(Elastic, Churn):
    upsert_call = "bulk index with the same _id (replaces the document)"
    maintain_call = "force merge with only_expunge_deletes, then refresh"

    def upsert(self, ids, vecs):
        self.load_batch(ids, vecs)

    def delete(self, ids):
        from elasticsearch import helpers
        helpers.bulk(self.c, ({"_op_type": "delete", "_index": NAME, "_id": str(int(i))} for i in ids),
                     raise_on_error=False)

    def maintain(self):
        t = time.time()
        before = self.stats()
        self.c.indices.forcemerge(index=NAME, only_expunge_deletes=True, wait_for_completion=True,
                                  request_timeout=7200)
        self.c.indices.refresh(index=NAME)
        return {"s": round(time.time() - t, 1), "before": before, "after": self.stats()}

    def stats(self):
        s = self.c.indices.stats(index=NAME, metric="docs,segments")["indices"][NAME]["primaries"]
        return {"docs": s["docs"]["count"], "deleted_docs": s["docs"]["deleted"], "segments": s["segments"]["count"]}


class ChromaChurn(Chroma, Churn):
    upsert_call = "upsert"
    maintain_call = f"none to call: wait {WAIT_FOR_BACKGROUND_S // 60} minutes"

    def upsert(self, ids, vecs):
        self._c().upsert(ids=[str(int(i)) for i in ids], embeddings=vecs)

    def delete(self, ids):
        self._c().delete(ids=[str(int(i)) for i in ids])

    def maintain(self):
        time.sleep(WAIT_FOR_BACKGROUND_S)
        return {"s": WAIT_FOR_BACKGROUND_S}

    def stats(self):
        return {}


STORES = {e.name: e for e in (PgChurn, QdrantChurn, MilvusChurn, WeaviateChurn, ElasticChurn, ChromaChurn)}
