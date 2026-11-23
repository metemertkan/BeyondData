"""Episode 3: the Episode 2 adapters with filter fields and filtered search.

Each adapter adds: setup(deployment) — the collection or table with the six fields stored the way that
deployment says; load_batch(ids, vecs, fields); apply(option) — a documented filter option (query-time, or a change
to the loaded collection such as adding an index); search(vec, k, cond, value) — top-k ids with the filter
`cond == value` (cond "none": no filter). Option "default" is the database as its quickstart leaves it.
"""
from __future__ import annotations

import subprocess
import time
from typing import Any

import numpy as np

from vectors.engines import DIM, NAME, Chroma, Elastic, Engine, Milvus, PgVector, Qdrant, Weaviate, _uuid
from vectors.filters import FIELDS

COMPOSE = ["docker", "compose", "-f", "docker-compose.ep03.yml"]


class Filtered(Engine):
    prefix, project = "bd3", "beyonddata-ep03"
    deployments: dict[str, list[str]] = {"base": ["default"]}  # deployment -> options measured on it, in order
    option = "default"

    # setup(), load_batch(ids, vecs, fields) and search(vec, k, cond, value) are defined per database below

    def setup_deployment(self, deployment: str) -> None:
        self.setup()

    def apply(self, option: str) -> dict:
        self.option = option
        return {}

    def filter_settings(self) -> dict:
        return {}


def _rows(fields: np.ndarray, i: int) -> dict:
    return {f: int(fields[i, j]) for j, f in enumerate(FIELDS)}


# --------------------------------------------------------------------------------------------- pgvector
class PgFiltered(PgVector, Filtered):
    deployments = {"base": ["default", "iterative", "btree"]}

    def setup_deployment(self, deployment):
        cols = ", ".join(f"{f} int" for f in FIELDS)
        self.c.execute(f"CREATE TABLE {NAME} (id bigint PRIMARY KEY, embedding vector({DIM}), {cols})")

    def load_batch(self, ids, vecs, fields=None):
        with self.c.cursor().copy(f"COPY {NAME} (id, embedding, {', '.join(FIELDS)}) FROM STDIN WITH (FORMAT BINARY)") as cp:
            cp.set_types(["int8", "vector"] + ["int4"] * len(FIELDS))
            for i, v, f in zip(ids, vecs, fields):
                cp.write_row((int(i), v, *(int(x) for x in f)))

    def wait_indexed(self):
        out = super().wait_indexed()
        # autovacuum would gather planner statistics on its own after a bulk load; run it now so they're there
        self.c.execute(f"ANALYZE {NAME}")
        return out

    def apply(self, option):
        self.option = option
        out = {}
        if option == "default":
            self.c.execute("RESET hnsw.iterative_scan")
        elif option == "iterative":
            self.c.execute("SET hnsw.iterative_scan = relaxed_order")
        elif option == "btree":
            t = time.time()
            for f in FIELDS:
                self.c.execute(f"CREATE INDEX IF NOT EXISTS {NAME}_{f}_idx ON {NAME} ({f})")
            self.c.execute(f"ANALYZE {NAME}")
            self.c.execute("SET hnsw.iterative_scan = relaxed_order")
            out["btree_build_s"] = round(time.time() - t, 1)
        else:
            raise ValueError(option)
        return out

    def _sql(self, cond, k):
        where = "" if cond == "none" else f"WHERE {cond} = %s"
        if self.option == "default":
            return f"SELECT id FROM {NAME} {where} ORDER BY embedding <=> %s LIMIT {k}"
        # relaxed order can return results slightly out of order; the README re-sorts them like this
        return (f"WITH r AS MATERIALIZED (SELECT id, embedding <=> %s AS d FROM {NAME} {where} ORDER BY d LIMIT {k}) "
                f"SELECT id FROM r ORDER BY d + 0")

    def _args(self, vec, cond, value):
        if cond == "none":
            return (vec,)
        return (value, vec) if self.option == "default" else (vec, value)

    def search(self, vec, k=10, cond="none", value=None):
        return [r[0] for r in self.c.execute(self._sql(cond, k), self._args(vec, cond, value)).fetchall()]

    def set_knob(self, value):
        # Amendment 4: psycopg prepares a statement after 5 runs, and Postgres may then keep one generic plan for it,
        # made under the settings of that moment; a later SET doesn't replan it. So each setting runs on a new
        # connection opened with it, as from a pool configured with the setting.
        self.c.close()
        self.connect()
        self.c.execute("SELECT '[1]'::vector", prepare=False)  # loads pgvector's library, which defines its settings
        if self.option != "default":
            self.c.execute("SET hnsw.iterative_scan = relaxed_order")
        super().set_knob(value)

    @staticmethod
    def _pg_text(sql: str) -> str:
        """The statement as psycopg sends it and pg_prepared_statements shows it: each %s becomes $1, $2, ..."""
        parts = sql.split("%s")
        return "".join(p + (f"${i + 1}" if i < len(parts) - 1 else "") for i, p in enumerate(parts))

    def _prepared(self, cond, k=10):
        return self.c.execute("SELECT name, generic_plans, custom_plans FROM pg_prepared_statements WHERE statement = %s",
                              (self._pg_text(self._sql(cond, k)),), prepare=False).fetchone()

    def prepared_counts(self, cond, k=10) -> dict:
        """How often Postgres planned the cell's statement for its values (custom) or reused one plan (generic)."""
        r = self._prepared(cond, k)
        return {"generic": int(r[1]), "custom": int(r[2])} if r else {}

    def prepared_plan(self, vec, cond, value, k=10) -> str:
        """The plan the cell's prepared statement runs with now (EXPLAIN EXECUTE): its kept generic plan, if it has one.
        Plain EXPLAIN plans the query afresh, which is what the statement does only while it gets custom plans."""
        r = self._prepared(cond, k)
        if not r:
            return ""
        lit = {"vec": "'[" + ",".join(repr(float(x)) for x in vec) + "]'::vector", "val": str(int(value or 0))}
        args = [lit["vec"] if a is vec else lit["val"] for a in self._args(vec, cond, value)]
        return self._nodes(x[0] for x in self.c.execute(f"EXPLAIN EXECUTE {r[0]}({', '.join(args)})",
                                                        prepare=False).fetchall())

    def plan(self, vec, cond, value, k=10) -> str:
        """The plan's scan nodes, e.g. 'Index Scan docs_embedding_idx' or 'Bitmap Index Scan docs_team_idx'."""
        return self._nodes(r[0] for r in self.c.execute("EXPLAIN " + self._sql(cond, k),
                                                        self._args(vec, cond, value), prepare=False).fetchall())

    @staticmethod
    def _nodes(lines) -> str:
        nodes = []
        for ln in lines:
            s = ln.strip().lstrip("-> ").strip()
            for node in ("Index Scan", "Bitmap Index Scan", "Seq Scan", "Parallel Seq Scan", "Index Only Scan"):
                if s.startswith(node):
                    nodes.append(s.split("  (")[0].replace(" using ", " ").replace(" on ", " "))
                    break
        return " + ".join(nodes)

    def filter_settings(self):
        q = lambda s: self.c.execute(s).fetchone()[0]  # noqa: E731
        return {"hnsw.iterative_scan": q("SHOW hnsw.iterative_scan"), "hnsw.max_scan_tuples": q("SHOW hnsw.max_scan_tuples"),
                "hnsw.scan_mem_multiplier": q("SHOW hnsw.scan_mem_multiplier"), "hnsw.ef_search": q("SHOW hnsw.ef_search"),
                "indexes": [r[0] for r in self.c.execute(
                    f"SELECT indexdef FROM pg_indexes WHERE tablename='{NAME}'").fetchall()],
                "table_bytes": q(f"SELECT pg_total_relation_size('{NAME}')")}


# --------------------------------------------------------------------------------------------- Qdrant
class QdrantFiltered(Qdrant, Filtered):
    deployments = {"noindex": ["default", "index_later"], "index_first": ["index_first", "acorn"]}
    acorn = False

    def _payload_indexes(self):
        from qdrant_client import models as m
        for f in FIELDS:
            self.c.create_payload_index(NAME, field_name=f, field_schema=m.PayloadSchemaType.INTEGER, wait=True)

    def setup_deployment(self, deployment):
        self.setup()
        if deployment == "index_first":
            self._payload_indexes()

    def load_batch(self, ids, vecs, fields=None):
        from qdrant_client import models as m
        self.c.upsert(NAME, points=m.Batch(ids=[int(i) for i in ids], vectors=vecs.tolist(),
                                            payloads=[_rows(fields, j) for j in range(len(ids))]))

    def apply(self, option):
        self.option = option
        self.acorn = option == "acorn"
        out = {}
        if option == "index_later":
            t = time.time()
            self._payload_indexes()
            out["payload_index_s"] = round(time.time() - t, 1)
            t = time.time()
            out["after_index"] = self.wait_indexed()
            out["wait_green_s"] = round(time.time() - t, 1)
        return out

    def search(self, vec, k=10, cond="none", value=None):
        from qdrant_client import models as m
        flt = None if cond == "none" else m.Filter(must=[m.FieldCondition(key=cond, match=m.MatchValue(value=int(value)))])
        params = None
        if self._knob is not None or self.acorn:
            params = m.SearchParams(hnsw_ef=None if self._knob is None else int(self._knob),
                                    acorn=m.AcornSearchParams(enable=True) if self.acorn else None)
        return [p.id for p in self.c.query_points(NAME, query=vec.tolist(), query_filter=flt, limit=k,
                                                  search_params=params).points]

    def filter_settings(self):
        info = self.c.get_collection(NAME)
        return {"hnsw_config": info.config.hnsw_config.model_dump(), "payload_schema": {
            k: v.model_dump(exclude_none=True) for k, v in (info.payload_schema or {}).items()},
                "segments": info.segments_count, "indexed_vectors": info.indexed_vectors_count}


# --------------------------------------------------------------------------------------------- Milvus
class MilvusFiltered(Milvus, Filtered):
    deployments = {"dynamic": ["default"], "schema": ["schema", "schema_index"]}

    def setup_deployment(self, deployment):
        if deployment == "dynamic":
            return self.setup()  # quick setup: id + vector + dynamic field; the six fields land in $meta
        from pymilvus import DataType
        schema = self.c.create_schema(auto_id=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=DIM)
        for f in FIELDS:
            schema.add_field(f, DataType.INT64)
        idx = self.c.prepare_index_params()
        idx.add_index("vector", index_type="AUTOINDEX", metric_type="COSINE")  # what quick setup creates
        self.c.create_collection(NAME, schema=schema, index_params=idx)

    def load_batch(self, ids, vecs, fields=None):
        self.c.insert(NAME, [{"id": int(i), "vector": v, **_rows(fields, j)}
                             for j, (i, v) in enumerate(zip(ids, vecs.tolist()))])

    def _index_name(self):
        return next(n for n in self.c.list_indexes(NAME) if n not in FIELDS)

    def apply(self, option):
        self.option = option
        out = {}
        if option == "schema_index":
            t = time.time()
            self.c.release_collection(NAME)
            idx = self.c.prepare_index_params()
            for f in FIELDS:
                idx.add_index(f, index_type="AUTOINDEX", index_name=f)
            self.c.create_index(NAME, idx)
            for f in FIELDS:
                while True:
                    d = self.c.describe_index(NAME, index_name=f)
                    if d.get("pending_index_rows", 1) == 0 and d.get("indexed_rows", 0) >= d.get("total_rows", 1):
                        break
                    time.sleep(2)
            self.c.load_collection(NAME)
            out["scalar_index_s"] = round(time.time() - t, 1)
            out["scalar_indexes"] = {f: self.c.describe_index(NAME, index_name=f) for f in FIELDS}
        return out

    def search(self, vec, k=10, cond="none", value=None):
        sp = {} if self._knob is None else {"params": {"ef": int(self._knob), "refine_k": max(1, int(self._knob) // 10)}}
        flt = "" if cond == "none" else f"{cond} == {int(value)}"
        res = self.c.search(NAME, data=[vec.tolist()], limit=k, filter=flt, search_params=sp)
        return [h["id"] for h in res[0]]

    def filter_settings(self):
        d = self.c.describe_collection(NAME)
        return {"enable_dynamic_field": d.get("enable_dynamic_field"),
                "fields": [{k: f.get(k) for k in ("name", "type")} for f in d.get("fields", [])],
                "indexes": {n: self.c.describe_index(NAME, index_name=n) for n in self.c.list_indexes(NAME)}}


# --------------------------------------------------------------------------------------------- Weaviate
class WeaviateFiltered(Weaviate, Filtered):
    # the strategy as shipped is measured as "default"; the others are set in place (the setting is mutable)
    deployments = {"base": ["default", "sweeping", "acorn", "pathseer"]}

    def load_batch(self, ids, vecs, fields=None):
        from weaviate.classes.data import DataObject
        r = self._c().data.insert_many([DataObject(uuid=_uuid(i), vector=v, properties=_rows(fields, j))
                                        for j, (i, v) in enumerate(zip(ids, vecs.tolist()))])
        if r.has_errors:
            raise RuntimeError(str(list(r.errors.values())[:3]))

    def shipped_strategy(self) -> str:
        return str(self.filter_settings()["vectorIndexConfig"].get("filterStrategy"))

    def apply(self, option):
        from weaviate.classes.config import Reconfigure, VectorFilterStrategy
        self.option = option
        if option != "default":
            self._c().config.update(vector_config=Reconfigure.Vectors.update(
                name="default", vector_index_config=Reconfigure.VectorIndex.hnsw(
                    filter_strategy=VectorFilterStrategy(option))))
            time.sleep(2)
        return {"filterStrategy": self.shipped_strategy()}

    def search(self, vec, k=10, cond="none", value=None):
        from weaviate.classes.query import Filter
        flt = None if cond == "none" else Filter.by_property(cond).equal(int(value))
        r = self._c().query.near_vector(vec.tolist(), limit=k, filters=flt, return_properties=[])
        return [o.uuid.int for o in r.objects]

    def filter_settings(self):
        import httpx
        schema = httpx.get(f"http://localhost:8081/v1/schema/{NAME[0].upper() + NAME[1:]}", timeout=30).json()
        vic = (schema.get("vectorConfig") or {}).get("default", {}).get("vectorIndexConfig") or schema.get(
            "vectorIndexConfig") or {}
        return {"vectorIndexConfig": {k: vic.get(k) for k in ("filterStrategy", "flatSearchCutoff", "ef", "efConstruction",
                                                               "maxConnections")},
                "properties": [{k: p.get(k) for k in ("name", "dataType", "indexFilterable", "indexRangeFilters")}
                               for p in schema.get("properties", [])]}


# --------------------------------------------------------------------------------------------- Elasticsearch
class ElasticFiltered(Elastic, Filtered):
    deployments = {"base": ["default", "fanout", "exact"]}

    def apply(self, option):
        # fanout: the filter heuristic before 9.1's ACORN default (index.dense_vector.hnsw_filter_heuristic, dynamic)
        self.option = option
        if option in ("default", "fanout"):
            self.c.indices.put_settings(index=NAME, settings={
                "index.dense_vector.hnsw_filter_heuristic": "fanout" if option == "fanout" else None})
        return {}

    def load_batch(self, ids, vecs, fields=None):
        from elasticsearch import helpers
        helpers.bulk(self.c, ({"_index": NAME, "_id": str(int(i)), "embedding": v, **_rows(fields, j)}
                              for j, (i, v) in enumerate(zip(ids, vecs.tolist()))), chunk_size=len(ids),
                     raise_on_error=True)

    def search(self, vec, k=10, cond="none", value=None):
        flt = None if cond == "none" else {"term": {cond: int(value)}}
        if self.option == "exact":
            # the docs' exact kNN: script_score over the documents the filter matches, with the full vectors
            q: dict[str, Any] = {"script_score": {"query": flt or {"match_all": {}}, "script": {
                "source": "cosineSimilarity(params.q, 'embedding') + 1.0", "params": {"q": vec.tolist()}}}}
            r = self.c.search(index=NAME, query=q, source=False, size=k)
            return [int(h["_id"]) for h in r["hits"]["hits"]]
        knn: dict[str, Any] = {"field": "embedding", "query_vector": vec.tolist(), "k": k}
        if flt:
            knn["filter"] = flt
        if self._knob is not None:
            knn["num_candidates"] = int(self._knob)
            knn["rescore_vector"] = {"oversample": max(3.0, int(self._knob) / k)}
        r = self.c.search(index=NAME, knn=knn, source=False, size=k)
        return [int(h["_id"]) for h in r["hits"]["hits"]]

    def filter_settings(self):
        m = self.c.indices.get_mapping(index=NAME)[NAME]["mappings"]["properties"]
        s = self.c.indices.get_settings(index=NAME, include_defaults=True)[NAME]
        flat = {}

        def walk(d, p=""):
            for k, v in d.items():
                if isinstance(v, dict):
                    walk(v, f"{p}{k}.")
                elif any(w in f"{p}{k}" for w in ("vector", "knn", "hnsw", "filter")):
                    flat[f"{p}{k}"] = v
        walk(s)
        return {"field_mappings": {f: m.get(f) for f in FIELDS}, "vector_settings": flat}


# --------------------------------------------------------------------------------------------- Chroma
class ChromaFiltered(Chroma, Filtered):
    def load_batch(self, ids, vecs, fields=None):
        self._c().add(ids=[str(int(i)) for i in ids], embeddings=vecs,
                      metadatas=[_rows(fields, j) for j in range(len(ids))])

    def search(self, vec, k=10, cond="none", value=None):
        where = None if cond == "none" else {cond: int(value)}
        r = self._c().query(query_embeddings=[vec], n_results=k, where=where, include=[])
        return [int(i) for i in r["ids"][0]]

    def filter_settings(self):
        return self.settings()


ENGINES: dict[str, type[Filtered]] = {e.name: e for e in (PgFiltered, QdrantFiltered, MilvusFiltered, WeaviateFiltered,
                                                         ElasticFiltered, ChromaFiltered)}


def compose(*args, cwd=None, check=True):
    return subprocess.run(COMPOSE + list(args), cwd=cwd, capture_output=True, text=True, check=check)
