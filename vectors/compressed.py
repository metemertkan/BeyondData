"""Episode 4: the Episode 2 adapters with each database's documented vector compression.

A deployment is one compression setting that needs a fresh collection, table or index (its own load). Each adapter
adds: setup_deployment(name) — the collection, table or index the way that database's compression docs show it,
everything else at its defaults; set_knob(c) — the search-time setting at c candidates (None = no search parameters,
as shipped); settings() — the effective configuration read back from the running database.

The knob c means "look at c candidates": for a compressed index, the number re-scored with the original vectors
(oversampling c / k); for float32, the HNSW candidate list (ef). Per database:
  pgvector  vector/halfvec: hnsw.ef_search = c; bit: the README's re-rank query with an inner LIMIT c and
            hnsw.ef_search = max(40, c). Every setting runs on its own connection (Episode 3, amendment 4).
  Qdrant    none: hnsw_ef = c; quantized: rescore on, oversampling c / k.
  Milvus    HNSW, HNSW_SQ: ef = c; AUTOINDEX (4-bit + FP16 refine): ef = c, refine_k = c / k;
            IVF_RABITQ (+ SQ8 refine): refine_k = c / k, nprobe = 8 x refine_k (the default ratio), at most nlist.
  Weaviate  none, bq: ef = c; rq: rescoreLimit = c and ef = c (amendment 2: a rescoreLimit above the candidate
            list re-scores no more).
  Elastic   hnsw: num_candidates = c; quantized: num_candidates = c, rescore_vector.oversample = c / k.
  Chroma    ef_search = c (applied by a restart, Episode 2's finding).
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

import numpy as np

from vectors.engines import DIM, NAME, Chroma, Elastic, Engine, Milvus, PgVector, Qdrant, Weaviate

COMPOSE = ["docker", "compose", "-f", "docker-compose.ep04.yml"]
K = 10
READY_S = 600  # after a restart under a memory limit: a database not answering within 10 minutes didn't start

# While a restarted container comes up, the adapters' connection retries give up at once if it has exited (killed
# for memory) instead of retrying for minutes against a container that isn't there.
import vectors.engines as _engines  # noqa: E402

_WATCH: dict[str, str | None] = {"container": None}


def _retry_watch(fn, seconds=180):
    end = time.time() + seconds
    while True:
        try:
            return fn()
        except Exception:
            name = _WATCH["container"]
            if name and _status(name) not in ("running", "restarting", "created"):
                raise
            if time.time() > end:
                raise
            time.sleep(2)


def _status(name: str) -> str:
    out = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", name], capture_output=True, text=True)
    return out.stdout.strip()


_engines._retry = _retry_watch


class Compressed(Engine):
    prefix, project = "bd4", "beyonddata-ep04"
    deployments: dict[str, str] = {}     # name -> what it is (for the plan and the summary)
    datadir = ""                          # data directory inside the container (read in to warm the cache)
    deployment = ""

    def setup_deployment(self, name: str) -> None:
        self.deployment = name
        self.setup()

    def shipped_knob_note(self) -> str:
        return ""


# --------------------------------------------------------------------------------------------- pgvector
class PgCompressed(PgVector, Compressed):
    deployments = {
        "vector": "float32: HNSW on the vector column (README)",
        "halfvec": "16-bit: HNSW on embedding::halfvec(1024) (README, half-precision indexing)",
        "bit": "1-bit: HNSW on binary_quantize(embedding)::bit(1024), the README's re-rank query",
    }
    datadir = "/var/lib/postgresql"
    SHIPPED_RERANK = 40  # the README re-ranks LIMIT 20 for a top 5: 4 x k

    def setup_deployment(self, name):
        self.deployment = name
        self.c.execute(f"CREATE TABLE {NAME} (id bigint PRIMARY KEY, embedding vector({DIM}))")

    def _index_sql(self) -> str:
        return {
            "vector": f"CREATE INDEX ON {NAME} USING hnsw (embedding vector_cosine_ops)",
            "halfvec": f"CREATE INDEX ON {NAME} USING hnsw ((embedding::halfvec({DIM})) halfvec_cosine_ops)",
            "bit": f"CREATE INDEX ON {NAME} USING hnsw ((binary_quantize(embedding)::bit({DIM})) bit_hamming_ops)",
        }[self.deployment]

    def wait_indexed(self):
        # graph parameters at their defaults (m 16, ef_construction 64); the README's build-speed advice, so three
        # builds take minutes instead of Episode 2's 51 for one: the graph fits in maintenance_work_mem, 7 workers
        self.c.execute("SET maintenance_work_mem = '8GB'")
        self.c.execute("SET max_parallel_maintenance_workers = 7")
        t = time.time()
        self.c.execute(self._index_sql())
        out = {"index_build_s": round(time.time() - t, 1), "notices": list(dict.fromkeys(self.notices))}
        self.c.execute("RESET maintenance_work_mem")
        self.c.execute("RESET max_parallel_maintenance_workers")
        self.c.execute(f"ANALYZE {NAME}")
        return out

    def _sql(self, k: int) -> str:
        if self.deployment == "vector":
            return f"SELECT id FROM {NAME} ORDER BY embedding <=> %(v)s LIMIT {k}"
        if self.deployment == "halfvec":
            return (f"SELECT id FROM {NAME} ORDER BY embedding::halfvec({DIM}) <=> %(v)s::vector({DIM})::halfvec({DIM}) "
                    f"LIMIT {k}")
        n = self.SHIPPED_RERANK if self._knob is None else int(self._knob)
        return (f"SELECT id FROM (SELECT id, embedding FROM {NAME} ORDER BY binary_quantize(embedding)::bit({DIM}) "
                f"<~> binary_quantize(%(v)s::vector({DIM})) LIMIT {n}) t ORDER BY embedding <=> %(v)s LIMIT {k}")

    def set_knob(self, value):
        # a new connection per setting: a prepared statement keeps the plan made under the old setting (Episode 3)
        self._knob = value
        self.close()
        self.connect()
        if value is not None:
            ef = int(value) if self.deployment != "bit" else max(40, int(value))
            self.c.execute(f"SET hnsw.ef_search = {ef}")

    def search(self, vec, k=10):
        return [r[0] for r in self.c.execute(self._sql(k), {"v": vec}).fetchall()]

    def plan(self, vec, k=10) -> str:
        rows = [r[0] for r in self.c.execute("EXPLAIN " + self._sql(k), {"v": vec}).fetchall()]
        rows = [re.sub(r"'\[[^']*\]'", "'[...]'", r.strip()) for r in rows]
        return " / ".join(r for r in rows if "Scan" in r or "Limit" in r or "Sort" in r)

    def settings(self):
        q = lambda s: self.c.execute(s).fetchone()[0]  # noqa: E731
        idx = q(f"SELECT indexname FROM pg_indexes WHERE tablename='{NAME}' AND indexdef LIKE '%hnsw%'")
        return {"version": q("SELECT extversion FROM pg_extension WHERE extname='vector'"),
                "index": q(f"SELECT indexdef FROM pg_indexes WHERE indexname='{idx}'"),
                "reloptions (empty = m 16, ef_construction 64)": q(f"SELECT reloptions FROM pg_class WHERE relname='{idx}'"),
                "index_bytes": q(f"SELECT pg_relation_size('{idx}')"),
                "table_bytes": q(f"SELECT pg_table_size('{NAME}')"),
                "toast_bytes": q(f"SELECT pg_total_relation_size(reltoastrelid) FROM pg_class WHERE relname='{NAME}'"),
                "hnsw.ef_search": q("SHOW hnsw.ef_search"), "shared_buffers": q("SHOW shared_buffers"),
                "plan": self.plan(np.ones(DIM, np.float32) / DIM ** 0.5)}


# --------------------------------------------------------------------------------------------- Qdrant
class QdrantCompressed(Qdrant, Compressed):
    deployments = {
        "none": "float32: no quantization (default)",
        "scalar": "8-bit: scalar int8",
        "turbo4": "4-bit: TurboQuant bits4",
        "turbo2": "2-bit: TurboQuant bits2",
        "binary": "1-bit: binary quantization (the docs' first example)",
        "turbo1": "1-bit: TurboQuant bits1",
    }
    datadir = "/qdrant/storage"

    def _quantization(self):
        from qdrant_client import models as m
        pinned = m.Memory.PINNED  # every example in the quantization docs pins the quantized copy in RAM
        return {
            "none": None,
            "scalar": m.ScalarQuantization(scalar=m.ScalarQuantizationConfig(type=m.ScalarType.INT8, memory=pinned)),
            "turbo4": m.TurboQuantization(turbo=m.TurboQuantQuantizationConfig(bits=m.TurboQuantBitSize.BITS4, memory=pinned)),
            "turbo2": m.TurboQuantization(turbo=m.TurboQuantQuantizationConfig(bits=m.TurboQuantBitSize.BITS2, memory=pinned)),
            "binary": m.BinaryQuantization(binary=m.BinaryQuantizationConfig(memory=pinned)),
            "turbo1": m.TurboQuantization(turbo=m.TurboQuantQuantizationConfig(bits=m.TurboQuantBitSize.BITS1, memory=pinned)),
        }[self.deployment]

    def setup_deployment(self, name):
        from qdrant_client import models as m
        self.deployment = name
        self.c.create_collection(NAME, vectors_config=m.VectorParams(size=DIM, distance=m.Distance.COSINE),
                                 quantization_config=self._quantization())

    def search(self, vec, k=10):
        from qdrant_client import models as m
        params = None
        if self._knob is not None:
            c = int(self._knob)
            params = (m.SearchParams(hnsw_ef=c) if self.deployment == "none" else
                      m.SearchParams(quantization=m.QuantizationSearchParams(rescore=True, oversampling=c / k)))
        return [p.id for p in self.c.query_points(NAME, query=vec.tolist(), limit=k, search_params=params).points]

    def ready(self) -> None:
        """After a restart: wait until the collection answers and is green (at most READY_S)."""
        from vectors.engines import _retry
        end = time.time() + READY_S
        _retry(lambda: self.c.get_collection(NAME), READY_S)
        while not str(self.c.get_collection(NAME).status).lower().endswith("green"):
            if time.time() > end:
                raise TimeoutError("collection not green")
            time.sleep(2)


# --------------------------------------------------------------------------------------------- Milvus
class MilvusCompressed(Milvus, Compressed):
    deployments = {
        "hnsw": "float32: HNSW",
        "hnsw_sq8": "8-bit: HNSW_SQ (sq_type default SQ8, no refine)",
        "autoindex": "4-bit + FP16 refine: AUTOINDEX, the quick setup (Episode 2's default)",
        "ivf_rabitq": "1-bit + SQ8 refine: IVF_RABITQ with the docs' refine for 0.9+ recall",
    }
    datadir = "/var/lib/milvus"
    NLIST = 128  # IVF_RABITQ's default

    def setup_deployment(self, name):
        from pymilvus import DataType, MilvusClient
        self.deployment = name
        if name == "autoindex":
            self.c.create_collection(NAME, dimension=DIM, metric_type="COSINE")
            return
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=DIM)
        ip = self.c.prepare_index_params()
        kind, params = {"hnsw": ("HNSW", {}), "hnsw_sq8": ("HNSW_SQ", {}),
                        "ivf_rabitq": ("IVF_RABITQ", {"refine": True, "refine_type": "SQ8"})}[name]
        ip.add_index(field_name="vector", index_type=kind, metric_type="COSINE", params=params)
        self.c.create_collection(NAME, schema=schema, index_params=ip)

    def search(self, vec, k=10):
        sp: dict[str, Any] = {}
        if self._knob is not None:
            c = int(self._knob)
            p = {"hnsw": {"ef": c}, "hnsw_sq8": {"ef": c}, "autoindex": {"ef": c, "refine_k": max(1, c // k)},
                 "ivf_rabitq": {"refine_k": max(1, c // k), "nprobe": min(self.NLIST, 8 * max(1, c // k))}}
            sp = {"params": p[self.deployment]}
        res = self.c.search(NAME, data=[vec.tolist()], limit=k, search_params=sp)
        return [h["id"] for h in res[0]]

    def ready(self) -> None:
        # load_collection has no deadline of its own: at too small a limit it waits forever (pilot, 0.5 GiB)
        from vectors.engines import _retry
        self.connect()
        _retry(lambda: self.c.load_collection(NAME, timeout=READY_S), READY_S)

    def settle(self, stable_s=180, max_s=3600):
        """Amendment 5 (found in the full run's read-back): Episode 2's settle waits until the loaded segments stop
        changing, but Milvus builds indexes for compacted segments in the background and keeps serving the old ones
        meanwhile (HNSW at 1M: 811,511 rows pending after the sweep, a build still running during the ladder). Wait
        until no rows are pending too, then for the segments to stay the same again."""
        t0, rounds = time.time(), []
        while True:
            s = super().settle(stable_s=stable_s, max_s=max(60, int(max_s - (time.time() - t0))))
            pending = self.c.describe_index(NAME, index_name=self._index_name()).get("pending_index_rows", 0)
            rounds.append({**s, "pending_index_rows": pending})
            if not pending or time.time() - t0 > max_s:
                break
            while pending and time.time() - t0 < max_s:
                time.sleep(10)
                pending = self.c.describe_index(NAME, index_name=self._index_name()).get("pending_index_rows", 0)
        return {"settle_s": round(time.time() - t0), "rounds": rounds,
                "segment_history": rounds[-1].get("segment_history", [])}


# --------------------------------------------------------------------------------------------- Weaviate
class WeaviateCompressed(Weaviate, Compressed):
    deployments = {
        "none": "float32: no compression (default; DEFAULT_QUANTIZATION unset)",
        "rq8": "8-bit: rotational quantization (rq(), the docs' first example)",
        "rq4": "4-bit: RQ bits=4 (new in 1.40)",
        "rq1": "1-bit: RQ bits=1",
        "bq": "1-bit: binary quantization",
    }
    datadir = "/var/lib/weaviate"
    RQ_BITS = {"rq8": 8, "rq4": 4, "rq1": 1}

    def setup_deployment(self, name):
        from weaviate.classes.config import Configure
        self.deployment = name
        q = Configure.VectorIndex.Quantizer
        quantizer = {"none": None, "rq8": q.rq(), "rq4": q.rq(bits=4), "rq1": q.rq(bits=1), "bq": q.bq()}[name]
        self.coll = self.client.collections.create(NAME, vector_config=Configure.Vectors.self_provided(
            quantizer=quantizer))

    def set_knob(self, value):
        from weaviate.classes.config import Reconfigure
        self._knob = value
        if self.deployment in self.RQ_BITS:
            # back to the defaults for "as shipped": rescoreLimit 20 for 8- and 4-bit RQ, 512 for 1-bit (docs), dynamic
            # ef. A rescoreLimit above the graph's candidate list re-scores no more candidates (pilot: recall flat
            # from c 20 to 500), so c sets both, as for Elasticsearch and Milvus (amendment 2)
            limit = (512 if self.deployment == "rq1" else 20) if value is None else int(value)
            ef = -1 if value is None else int(value)
            self._c().config.update(vector_config=Reconfigure.Vectors.update(
                name="default", vector_index_config=Reconfigure.VectorIndex.hnsw(
                    ef=ef, quantizer=Reconfigure.VectorIndex.Quantizer.rq(rescore_limit=limit))))
            time.sleep(1)
        else:
            super().set_knob(value)

    def wait_indexed(self, deadline_s: float | None = None):
        import httpx
        end = None if deadline_s is None else time.time() + deadline_s
        while True:
            if end is not None and time.time() > end:
                raise TimeoutError("shards not READY")
            nodes = httpx.get("http://localhost:8081/v1/nodes?output=verbose", timeout=30).json()["nodes"]
            shards = [s for n in nodes for s in n.get("shards") or []]
            queue = sum(s.get("vectorQueueLength", 0) for s in shards)
            status = {s.get("vectorIndexingStatus") for s in shards}
            if queue == 0 and status <= {"READY"}:
                return {"vector_queue": 0, "shards": len(shards)}
            time.sleep(2)

    def ready(self) -> None:
        self.connect()
        from vectors.engines import _retry
        _retry(lambda: self._c().aggregate.over_all(total_count=True), READY_S)
        self.wait_indexed(deadline_s=READY_S)


# --------------------------------------------------------------------------------------------- Elasticsearch
class ElasticCompressed(Elastic, Compressed):
    deployments = {
        "hnsw": "float32: index_options type hnsw",
        "int8_hnsw": "8-bit: int8_hnsw",
        "int4_hnsw": "4-bit: int4_hnsw",
        "bbq_hnsw": "1-bit: bbq_hnsw (the default for 384+ dimensions on this license; mapping left as shipped)",
    }
    datadir = "/usr/share/elasticsearch/data"

    def setup_deployment(self, name):
        self.deployment = name
        field: dict[str, Any] = {"type": "dense_vector", "dims": DIM, "similarity": "cosine"}
        if name != "bbq_hnsw":
            field["index_options"] = {"type": name}
        self.c.indices.create(index=NAME, mappings={"properties": {"embedding": field}})

    def search(self, vec, k=10):
        knn: dict[str, Any] = {"field": "embedding", "query_vector": vec.tolist(), "k": k}
        if self._knob is not None:
            c = int(self._knob)
            knn["num_candidates"] = c
            if self.deployment != "hnsw":
                knn["rescore_vector"] = {"oversample": c / k}
        r = self.c.search(index=NAME, knn=knn, source=False, size=k)
        return [int(h["_id"]) for h in r["hits"]["hits"]]

    def ready(self) -> None:
        self.connect()
        from vectors.engines import _retry
        _retry(lambda: self.c.cluster.health(index=NAME, wait_for_status="yellow", timeout="30s"), READY_S)


# --------------------------------------------------------------------------------------------- Chroma
class ChromaCompressed(Chroma, Compressed):
    deployments = {"default": "float32: the only option (no quantization setting in Chroma 1.5.9)"}
    datadir = "/data"
    knob_needs_restart = True

    def setup_deployment(self, name):
        self.deployment = name
        self.setup()

    def store_knob(self, value) -> None:
        """Store ef_search without restarting; it takes effect at the next start."""
        self._knob = value
        self._c().modify(configuration={"hnsw": {"ef_search": 100 if value is None else int(value)}})

    def ready(self) -> None:
        self.connect()
        self._c().query(query_embeddings=[np.ones(DIM, np.float32) / DIM ** 0.5], n_results=1, include=[])


def _ready_default(self) -> None:
    self.connect()


PgCompressed.ready = _ready_default  # type: ignore[attr-defined]
ENGINES: dict[str, type[Compressed]] = {e.name: e for e in (PgCompressed, QdrantCompressed, MilvusCompressed,
                                                            WeaviateCompressed, ElasticCompressed, ChromaCompressed)}


def compose(*args, check=True):
    return subprocess.run(COMPOSE + list(args), capture_output=True, text=True, check=check)


def container(E: Compressed) -> str:
    return f"{E.prefix}-{E.service}"


def volume(E: Compressed) -> str:
    return f"{E.project}_{E.service}"


def state(E: Compressed) -> dict:
    out = subprocess.run(["docker", "inspect", "-f", "{{json .State}}", container(E)], capture_output=True, text=True)
    s = json.loads(out.stdout) if out.returncode == 0 else {}
    return {"status": s.get("Status"), "oom_killed": s.get("OOMKilled"), "exit_code": s.get("ExitCode")}


EVICT = r"""
import os, sys
n = b = 0
for root, _, files in os.walk('/v'):
    for f in files:
        p = os.path.join(root, f)
        try:
            fd = os.open(p, os.O_RDONLY)
        except OSError:
            continue
        try:
            os.fsync(fd)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            n += 1; b += os.fstat(fd).st_size
        except OSError:
            pass
        finally:
            os.close(fd)
print(n, b)
"""


def evict(E: Compressed) -> dict:
    """Drop the volume's files from the host page cache (the container must be stopped). Without this, pages a
    previous run cached stay charged to the old, removed cgroup, and a restarted container reads them for free."""
    out = subprocess.run(["docker", "run", "--rm", "-v", f"{volume(E)}:/v", "python:3.12-slim", "python", "-c", EVICT],
                         capture_output=True, text=True, check=True).stdout.split()
    return {"files": int(out[0]), "bytes": int(out[1])}


def restart_with_budget(E: Compressed, gib: float, timeout_s: int = 900) -> dict:
    """Stop, drop the data from the page cache, set the memory limit (no swap), start, wait until the database
    answers, then read its data directory once inside the container (warming the cache the container is charged
    for). Returns what happened; "ok" False if it didn't come up (OOM-killed, exited, or timed out)."""
    name, mem = container(E), f"{int(gib * 1024)}m"
    t0 = time.time()
    subprocess.run(["docker", "stop", "-t", "120", name], capture_output=True, check=True)
    ev = evict(E)
    subprocess.run(["docker", "update", "--memory", mem, "--memory-swap", mem, name], capture_output=True, check=True)
    subprocess.run(["docker", "start", name], capture_output=True, check=True)
    out: dict[str, Any] = {"budget_gib": gib, "evicted": ev}
    _WATCH["container"] = name
    try:
        E.ready()  # type: ignore[attr-defined]
    except Exception as e:  # noqa: BLE001
        out.update(ok=False, error=f"{type(e).__name__}: {e}"[:300], **state(E))
        return out
    finally:
        _WATCH["container"] = None
    st = state(E)
    if st["status"] != "running":
        out.update(ok=False, error="not running", **st)
        return out
    t1 = time.time()
    r = subprocess.run(["docker", "exec", name, "sh", "-c", f"find {E.datadir} -type f -exec cat {{}} + > /dev/null"],
                       capture_output=True, text=True, timeout=timeout_s)
    out.update(ok=state(E)["status"] == "running", ready_s=round(t1 - t0, 1), preread_s=round(time.time() - t1, 1),
               preread_rc=r.returncode, **state(E))
    return out


def set_memory(E: Compressed, gib: float) -> None:
    mem = f"{int(gib * 1024)}m"
    subprocess.run(["docker", "update", "--memory", mem, "--memory-swap", mem, container(E)], capture_output=True,
                   check=True)
