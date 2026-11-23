"""Episode 2: one adapter per database, each set up the way its quickstart does it.

Every adapter: setup() creates the collection or table giving only the dimension and cosine distance (plus the
index the quickstart creates, with no parameters); load() inserts batches from one writer; wait_indexed() blocks
until the database has finished indexing; settings() reads the effective configuration back from the running
database; search(vec, knob) returns the top-10 ids, with knob=None meaning "no search parameters at all".
"""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from typing import Any

import numpy as np

DIM = 1024
NAME = "docs"


def _retry(fn, seconds=180):
    end = time.time() + seconds
    while True:
        try:
            return fn()
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


class Engine:
    name = ""
    service = ""          # docker compose service
    knob = ""             # name of the search-time setting the sweep changes
    knob_max = 10_000
    knob_is_global = False  # True: set_knob changes the collection for every client, not just this one

    def connect(self) -> None: ...
    def setup(self) -> None: ...
    def load_batch(self, ids: np.ndarray, vecs: np.ndarray) -> None: ...
    def wait_indexed(self) -> dict: return {}
    def settle(self) -> dict: return {}  # wait out background work that changes results after indexing
    def settings(self) -> dict: return {}
    def set_knob(self, value: int | None) -> None: self._knob = value
    def search(self, vec: np.ndarray, k: int = 10) -> list[int]: ...
    def insert_one(self, i: int, vec: np.ndarray) -> None: self.load_batch(np.array([i]), vec[None, :])
    def count(self) -> int: return -1
    def close(self) -> None: ...
    _knob: int | None = None


# --------------------------------------------------------------------------------------------- pgvector
class PgVector(Engine):
    name, service, knob, knob_max = "pgvector", "pgvector", "hnsw.ef_search", 1000
    dsn = "postgresql://bench:bench@localhost:5437/bench"

    def connect(self):
        import psycopg
        from pgvector.psycopg import register_vector
        def go():
            c = psycopg.connect(self.dsn, autocommit=True)
            c.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(c)
            return c
        self.c = _retry(go)
        self.notices: list[str] = []
        self.c.add_notice_handler(lambda d: self.notices.append(d.message_primary))

    def setup(self):
        self.c.execute(f"CREATE TABLE {NAME} (id bigint PRIMARY KEY, embedding vector({DIM}))")

    def load_batch(self, ids, vecs):
        with self.c.cursor().copy(f"COPY {NAME} (id, embedding) FROM STDIN WITH (FORMAT BINARY)") as cp:
            cp.set_types(["int8", "vector"])
            for i, v in zip(ids, vecs):
                cp.write_row((int(i), v))

    def wait_indexed(self):
        # the README's index, no parameters; created after loading, as the README recommends
        t = time.time()
        self.c.execute(f"CREATE INDEX ON {NAME} USING hnsw (embedding vector_cosine_ops)")
        return {"index_build_s": round(time.time() - t, 1), "notices": list(dict.fromkeys(self.notices))}

    def settings(self):
        q = lambda s: self.c.execute(s).fetchone()[0]  # noqa: E731
        return {"index": q(f"SELECT indexdef FROM pg_indexes WHERE tablename='{NAME}' AND indexdef LIKE '%hnsw%'"),
                "reloptions (empty = m 16, ef_construction 64)": q(
                    f"SELECT reloptions FROM pg_class WHERE relname IN (SELECT indexname FROM pg_indexes "
                    f"WHERE tablename='{NAME}' AND indexdef LIKE '%hnsw%')"),
                "hnsw.ef_search": q("SHOW hnsw.ef_search"), "hnsw.iterative_scan": q("SHOW hnsw.iterative_scan"),
                "maintenance_work_mem": q("SHOW maintenance_work_mem"),
                "max_parallel_maintenance_workers": q("SHOW max_parallel_maintenance_workers"),
                "shared_buffers": q("SHOW shared_buffers"), "version": q("SELECT extversion FROM pg_extension "
                                                                        "WHERE extname='vector'"),
                **self._plans()}

    def _plans(self) -> dict:
        """Which plan the planner picks for top 1 vs top 10, and what a top-1 query costs. Vectors this size are
        stored out of line (TOAST), so a sequential scan looks cheap to the planner."""
        v = np.ones(DIM, np.float32) / DIM ** 0.5
        out = {}
        for k in (1, 10):
            plan = [r[0] for r in self.c.execute(f"EXPLAIN SELECT id FROM {NAME} ORDER BY embedding <=> %s LIMIT {k}",
                                                 (v,)).fetchall()]
            out[f"plan_limit_{k}"] = "index scan" if any("Index Scan" in p for p in plan) else "sequential scan"
            t = time.perf_counter()
            self.c.execute(f"SELECT id FROM {NAME} ORDER BY embedding <=> %s LIMIT {k}", (v,)).fetchall()
            out[f"limit_{k}_ms"] = round((time.perf_counter() - t) * 1000, 1)
        out["toast_bytes"] = self.c.execute(
            f"SELECT pg_total_relation_size(reltoastrelid) FROM pg_class WHERE relname='{NAME}'").fetchone()[0]
        return out

    def set_knob(self, value):
        self._knob = value
        self.c.execute("RESET hnsw.ef_search" if value is None else f"SET hnsw.ef_search = {int(value)}")

    def search(self, vec, k=10):
        return [r[0] for r in self.c.execute(f"SELECT id FROM {NAME} ORDER BY embedding <=> %s LIMIT {k}",
                                             (vec,)).fetchall()]

    def insert_one(self, i, vec):
        self.c.execute(f"INSERT INTO {NAME} (id, embedding) VALUES (%s, %s)", (int(i), vec))

    def count(self):
        return self.c.execute(f"SELECT count(*) FROM {NAME}").fetchone()[0]

    def close(self):
        self.c.close()


# --------------------------------------------------------------------------------------------- Qdrant
class Qdrant(Engine):
    name, service, knob = "qdrant", "qdrant", "hnsw_ef"

    def connect(self):
        import httpx
        from qdrant_client import QdrantClient
        # The client's default transport (REST). For host "localhost" the client turns keep-alive off and opens a TCP
        # connection per request; at ~700 q/s that ran out of local ports (connection resets in the pilot). Against
        # any other host it keeps connections, so pass httpx's normal pool: what a deployed app gets.
        self.c = QdrantClient(url="http://localhost:6333", timeout=300, limits=httpx.Limits())
        _retry(self.c.get_collections)

    def setup(self):
        from qdrant_client import models as m
        self.c.create_collection(NAME, vectors_config=m.VectorParams(size=DIM, distance=m.Distance.COSINE))

    def load_batch(self, ids, vecs):
        from qdrant_client import models as m
        self.c.upsert(NAME, points=m.Batch(ids=[int(i) for i in ids], vectors=vecs.tolist()))

    def wait_indexed(self):
        # green = no optimization (index build, merge) pending; small segments stay unindexed by design
        green = 0
        while green < 3:
            time.sleep(2)
            info = self.c.get_collection(NAME)
            green = green + 1 if str(info.status).lower().endswith("green") else 0
        return {"points": info.points_count, "indexed_vectors": info.indexed_vectors_count}

    def settings(self):
        info = self.c.get_collection(NAME)
        return json.loads(info.model_dump_json(include={"config", "status", "segments_count"}))

    def search(self, vec, k=10):
        from qdrant_client import models as m
        params = None if self._knob is None else m.SearchParams(hnsw_ef=int(self._knob))
        return [p.id for p in self.c.query_points(NAME, query=vec.tolist(), limit=k, search_params=params).points]

    def count(self):
        return self.c.count(NAME, exact=True).count


# --------------------------------------------------------------------------------------------- Milvus
class Milvus(Engine):
    name, service, knob = "milvus", "milvus", "ef"

    def connect(self):
        from pymilvus import MilvusClient
        self.c = _retry(lambda: MilvusClient(uri="http://localhost:19530"), 300)
        _retry(self.c.list_collections, 300)

    def setup(self):
        # quick setup: id (int64, primary) + vector, AUTOINDEX, loaded
        self.c.create_collection(NAME, dimension=DIM, metric_type="COSINE")

    def load_batch(self, ids, vecs):
        self.c.insert(NAME, [{"id": int(i), "vector": v} for i, v in zip(ids, vecs.tolist())])

    def wait_indexed(self):
        self.c.flush(NAME)
        while True:
            d = self.c.describe_index(NAME, index_name=self._index_name())
            if d.get("pending_index_rows", 1) == 0 and d.get("indexed_rows", 0) >= d.get("total_rows", 1):
                break
            time.sleep(2)
        self.c.load_collection(NAME)  # quick setup already loaded it; this waits until the new segments are in
        return {k: d.get(k) for k in ("index_type", "indexed_rows", "total_rows", "state")}

    def _index_name(self):
        return self.c.list_indexes(NAME)[0]

    def _segments(self):
        from pymilvus import connections, utility
        if not connections.has_connection("ep02"):
            connections.connect("ep02", uri="http://localhost:19530")
        return sorted((s.segmentID, s.num_rows) for s in utility.get_query_segment_info(NAME, using="ep02"))

    def settle(self, stable_s=180, max_s=1800):
        """Milvus compacts small segments into bigger ones minutes after loading; results change when it does.
        Wait until the loaded segments stay the same for stable_s seconds."""
        t0, last, since = time.time(), None, time.time()
        history = []
        while time.time() - t0 < max_s:
            segs = self._segments()
            if segs != last:
                history.append({"t_s": round(time.time() - t0), "segments": len(segs),
                                "rows": [n for _, n in segs]})
                last, since = segs, time.time()
            elif time.time() - since >= stable_s:
                break
            time.sleep(10)
        return {"settle_s": round(time.time() - t0), "segment_history": history}

    def settings(self):
        d = self.c.describe_collection(NAME)
        # describe_index says only "AUTOINDEX"; the index node logs what that resolved to
        logs = subprocess.run(["docker", "logs", "bd2-milvus"], capture_output=True, text=True).stdout
        logs += subprocess.run(["docker", "logs", "bd2-milvus"], capture_output=True, text=True).stderr
        built = sorted({ln[ln.find("[index_type="):][:200] for ln in logs.splitlines()
                        if "efConstruction=" in ln and "[index_type=" in ln})
        return {"index": self.c.describe_index(NAME, index_name=self._index_name()), "autoindex_built_as": built,
                "consistency_level": d.get("consistency_level"), "fields": d.get("fields")}

    def search(self, vec, k=10):
        # the default index is 4-bit (HNSW_SQ, SQ4U) with refine: ef sets the candidate list and refine_k how many
        # times k candidates are re-ranked with the full vectors (default 1); the sweep raises both together
        sp = {} if self._knob is None else {"params": {"ef": int(self._knob),
                                                        "refine_k": max(1, int(self._knob) // 10)}}
        res = self.c.search(NAME, data=[vec.tolist()], limit=k, search_params=sp)
        return [h["id"] for h in res[0]]

    def count(self):
        return self.c.query(NAME, filter="", output_fields=["count(*)"])[0]["count(*)"]

    def close(self):
        self.c.close()


# --------------------------------------------------------------------------------------------- Weaviate
def _uuid(i: int) -> str:
    return str(uuid.UUID(int=int(i)))


class Weaviate(Engine):
    name, service, knob = "weaviate", "weaviate", "ef"
    knob_is_global = True

    def connect(self):
        import weaviate
        self.client = _retry(lambda: weaviate.connect_to_local(port=8081, grpc_port=50051))
        self.coll = None

    def setup(self):
        from weaviate.classes.config import Configure
        # self-provided vectors, nothing else (Weaviate's default distance is cosine)
        self.coll = self.client.collections.create(NAME, vector_config=Configure.Vectors.self_provided())

    def _c(self):
        if self.coll is None:
            self.coll = self.client.collections.get(NAME)
        return self.coll

    def load_batch(self, ids, vecs):
        from weaviate.classes.data import DataObject
        r = self._c().data.insert_many([DataObject(uuid=_uuid(i), vector=v) for i, v in zip(ids, vecs.tolist())])
        if r.has_errors:
            raise RuntimeError(str(list(r.errors.values())[:3]))

    def _queue(self) -> int:
        import httpx
        nodes = httpx.get("http://localhost:8081/v1/nodes?output=verbose", timeout=30).json()["nodes"]
        return sum(s.get("vectorQueueLength", 0) for n in nodes for s in n.get("shards") or [])

    def wait_indexed(self):
        while self._queue() > 0:
            time.sleep(2)
        return {"vector_queue": 0}

    def settings(self):
        import httpx
        schema = httpx.get(f"http://localhost:8081/v1/schema/{NAME[0].upper() + NAME[1:]}", timeout=30).json()
        meta = httpx.get("http://localhost:8081/v1/meta", timeout=30).json()
        return {"version": meta.get("version"), "vectorConfig": schema.get("vectorConfig"),
                "vectorIndexConfig": schema.get("vectorIndexConfig")}

    def set_knob(self, value):
        from weaviate.classes.config import Reconfigure
        self._knob = value
        ef = -1 if value is None else int(value)  # -1 = the default dynamic ef
        self._c().config.update(vector_config=Reconfigure.Vectors.update(
            name="default", vector_index_config=Reconfigure.VectorIndex.hnsw(ef=ef)))
        time.sleep(1)

    def search(self, vec, k=10):
        r = self._c().query.near_vector(vec.tolist(), limit=k, return_properties=[])
        return [o.uuid.int for o in r.objects]

    def count(self):
        return self._c().aggregate.over_all(total_count=True).total_count

    def close(self):
        self.client.close()


# --------------------------------------------------------------------------------------------- Elasticsearch
class Elastic(Engine):
    name, service, knob = "elasticsearch", "elasticsearch", "num_candidates"

    def connect(self):
        from elasticsearch import Elasticsearch
        self.c = Elasticsearch("http://localhost:9201", request_timeout=600)
        _retry(lambda: self.c.cluster.health(wait_for_status="yellow", timeout="5s"), 300)

    def setup(self):
        self.c.indices.create(index=NAME, mappings={"properties": {
            "embedding": {"type": "dense_vector", "dims": DIM, "similarity": "cosine"}}})

    def load_batch(self, ids, vecs):
        from elasticsearch import helpers
        ok, errors = helpers.bulk(self.c, ({"_index": NAME, "_id": str(int(i)), "embedding": v}
                                           for i, v in zip(ids, vecs.tolist())), chunk_size=len(ids),
                                  raise_on_error=True)

    def wait_indexed(self):
        self.c.indices.refresh(index=NAME)
        while True:
            s = self.c.indices.stats(index=NAME, metric="merge,segments,docs")["indices"][NAME]["primaries"]
            if s["merges"]["current"] == 0:
                return {"segments": s["segments"]["count"], "docs": s["docs"]["count"]}
            time.sleep(2)

    def settings(self):
        f = self.c.indices.get_field_mapping(index=NAME, fields="embedding", include_defaults=True)
        info = self.c.info()
        return {"version": info["version"]["number"], "license": self.c.license.get()["license"]["type"],
                "mapping": f[NAME]["mappings"]["embedding"]["mapping"]["embedding"],
                "segments": self.c.indices.stats(index=NAME, metric="segments")["indices"][NAME]["primaries"][
                    "segments"]["count"]}

    def search(self, vec, k=10):
        knn: dict[str, Any] = {"field": "embedding", "query_vector": vec.tolist(), "k": k}
        if self._knob is not None:
            # default index is 1-bit (bbq_hnsw) rescored with 3x oversampling; the sweep raises the candidate list
            # and the number rescored with full vectors together (k * oversample = the knob, never below 3x)
            knn["num_candidates"] = int(self._knob)
            knn["rescore_vector"] = {"oversample": max(3.0, int(self._knob) / k)}
        r = self.c.search(index=NAME, knn=knn, source=False, size=k)
        return [int(h["_id"]) for h in r["hits"]["hits"]]

    def count(self):
        self.c.indices.refresh(index=NAME)
        return self.c.count(index=NAME)["count"]

    def close(self):
        self.c.close()


# --------------------------------------------------------------------------------------------- Chroma
class Chroma(Engine):
    name, service, knob = "chroma", "chroma", "ef_search"
    knob_is_global = True

    def connect(self):
        import chromadb
        self.client = _retry(lambda: chromadb.HttpClient(host="localhost", port=8001))
        _retry(self.client.heartbeat)
        self.coll = None


    def setup(self):
        self.coll = self.client.create_collection(NAME, configuration={"hnsw": {"space": "cosine"}})

    def _c(self):
        if self.coll is None:
            self.coll = self.client.get_collection(NAME)
        return self.coll

    def load_batch(self, ids, vecs):
        self._c().add(ids=[str(int(i)) for i in ids], embeddings=vecs)

    def settings(self):
        c = self._c()
        return {"version": self.client.get_version(), "configuration": json.loads(json.dumps(
            c.configuration_json if hasattr(c, "configuration_json") else c.configuration, default=str))}

    def set_knob(self, value):
        # Chroma 1.5.9 stores a new ef_search at once but keeps searching with the old one until the server
        # restarts (the loaded index is cached), so a change here is modify + restart
        self._knob = value
        self._c().modify(configuration={"hnsw": {"ef_search": 100 if value is None else int(value)}})
        subprocess.run(["docker", "restart", "bd2-chroma"], capture_output=True, check=True)
        self.connect()
        self._c().query(query_embeddings=[np.ones(DIM, np.float32) / DIM ** 0.5], n_results=1, include=[])

    def search(self, vec, k=10):
        r = self._c().query(query_embeddings=[vec], n_results=k, include=[])
        return [int(i) for i in r["ids"][0]]

    def count(self):
        return self._c().count()


ENGINES: dict[str, type[Engine]] = {e.name: e for e in (PgVector, Qdrant, Milvus, Weaviate, Elastic, Chroma)}

COMPOSE = ["docker", "compose", "-f", "docker-compose.ep02.yml"]


def container(engine: Engine) -> str:
    return f"bd2-{engine.service}"


def mem_mib(engine: Engine) -> float:
    """Container memory as docker stats reports it (cgroup usage minus inactive page cache), in MiB."""
    out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container(engine)],
                         capture_output=True, text=True, check=True).stdout.split("/")[0].strip()
    num, unit = float("".join(ch for ch in out if ch.isdigit() or ch == ".")), out.lstrip("0123456789.")
    return num * {"B": 1 / 2**20, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[unit]


def disk_bytes(engine: Engine) -> int:
    vol = f"beyonddata-ep02_{engine.service}"
    out = subprocess.run(["docker", "run", "--rm", "-v", f"{vol}:/v:ro", "alpine:3.20", "du", "-sb", "/v"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.split()[0])
