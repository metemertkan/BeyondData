"""Episode 6: the index for the split designs (Weaviate 1.40.7), and the same-database one (pgvector in the record).

Every Weaviate collection uses the flat (exact) index with cosine distance, and every design retrieves the same way:
the k nearest chunks by vector. So designs differ only in what their index holds.
"""
from __future__ import annotations

import time
import uuid

import numpy as np
import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter

PROPS = ["text", "source", "article_id", "start_index", "chunk_hash", "article_hash"]


def connect() -> weaviate.WeaviateClient:
    end = time.time() + 120
    while True:
        try:
            return weaviate.connect_to_local(port=8086, grpc_port=50056)
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


def create(client: weaviate.WeaviateClient, name: str):
    if client.collections.exists(name):
        client.collections.delete(name)
    return client.collections.create(
        name,
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.flat(distance_metric=VectorDistances.COSINE)),
        properties=[Property(name="text", data_type=DataType.TEXT), Property(name="source", data_type=DataType.TEXT),
                    Property(name="article_id", data_type=DataType.INT), Property(name="start_index", data_type=DataType.INT),
                    Property(name="chunk_hash", data_type=DataType.TEXT), Property(name="article_hash", data_type=DataType.TEXT)])


def drop_all(client: weaviate.WeaviateClient) -> None:
    for name in list(client.collections.list_all()):
        client.collections.delete(name)


def insert(coll, objs: list[dict], vecs: np.ndarray) -> None:
    """objs: properties (and an optional 'uuid'); random ids unless given."""
    for i in range(0, len(objs), 500):
        part = [DataObject(properties={k: v for k, v in o.items() if k != "uuid"}, vector=vecs[i + j].tolist(),
                           uuid=o.get("uuid") or uuid.uuid4())
                for j, o in enumerate(objs[i:i + 500])]
        r = coll.data.insert_many(part)
        if r.has_errors:
            raise RuntimeError(str(list(r.errors.values())[:3]))


def delete_article(coll, article_id: int) -> int:
    r = coll.data.delete_many(where=Filter.by_property("article_id").equal(int(article_id)))
    return r.successful


def of_article(coll, article_id: int) -> list[dict]:
    r = coll.query.fetch_objects(filters=Filter.by_property("article_id").equal(int(article_id)), limit=10_000,
                                 return_properties=PROPS)
    return [o.properties | {"uuid": str(o.uuid)} for o in r.objects]


def near(coll, vec: np.ndarray, k: int) -> list[dict]:
    r = coll.query.near_vector(vec.tolist(), limit=k, return_properties=PROPS)
    return [o.properties | {"uuid": str(o.uuid)} for o in r.objects]


def entries(coll) -> list[dict]:
    return [o.properties | {"uuid": str(o.uuid)} for o in coll.iterator(return_properties=PROPS)]


def count(coll) -> int:
    return coll.aggregate.over_all(total_count=True).total_count


# --------------------------------------------------------------------------------------------- same database
class PgChunks:
    """The `chunks` table next to `articles` in the record (exact search: no vector index at this size)."""

    def __init__(self, conn):
        from pgvector.psycopg import register_vector
        self.c = conn
        register_vector(self.c)

    def write(self, cur, article_id: int, docs, vecs: np.ndarray) -> None:
        cur.execute("DELETE FROM chunks WHERE article_id = %s", (article_id,))
        for n, (d, v) in enumerate(zip(docs, vecs)):
            cur.execute("INSERT INTO chunks (article_id, n, source, text, embedding) VALUES (%s, %s, %s, %s, %s)",
                        (article_id, n, d.metadata["source"], d.page_content, v))

    def near(self, vec: np.ndarray, k: int) -> list[dict]:
        rows = self.c.execute("SELECT text, source, article_id FROM chunks ORDER BY embedding <=> %s LIMIT %s",
                              (vec, k)).fetchall()
        return [{"text": t, "source": s, "article_id": a} for t, s, a in rows]

    def of_article(self, article_id: int) -> list[dict]:
        rows = self.c.execute("SELECT text, source, article_id FROM chunks WHERE article_id = %s", (article_id,)).fetchall()
        return [{"text": t, "source": s, "article_id": a} for t, s, a in rows]

    def entries(self) -> list[dict]:
        return [{"text": t, "source": s, "article_id": a}
                for t, s, a in self.c.execute("SELECT text, source, article_id FROM chunks").fetchall()]

    def count(self) -> int:
        return self.c.execute("SELECT count(*) FROM chunks").fetchone()[0]
