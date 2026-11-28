"""Episode 6: eight ways to keep a vector index in step with the record, and the one I'd build.

Each design is driven by the replay (sync/replay.py) on a simulated clock. A design hands the replay *jobs*; a job's
`prepare()` runs when the design's worker starts it (reading the record as it is then) and returns how many chunks
it will embed and an `apply()` that the replay runs when the job finishes, `chunks x SECONDS_PER_CHUNK` later. One
worker per design: jobs run one after another, so changes that arrive while it is busy wait.

    once           the tutorial, run once: split, add_documents (random ids)
    rerun          the same script every night at 02:00 into the same collection
    rebuild        every night: a fresh collection from every article; queries switch when it's done
    upsert         every night: add_documents with ids from URL and chunk number; nothing deleted
    record_manager LangChain index() with a SQLRecordManager: incremental every 5 minutes, full at 02:00
    poll           every 5 minutes: rows with updated_at in the last interval; replace those articles' chunks
    cdc            logical decoding: every committed insert, update or delete replaces (or deletes) that article's chunks
    same_db        chunks and vectors in the record's database, written in the save's transaction; ON DELETE CASCADE
    built          cdc, embedding only new chunk texts, a check of every retrieved chunk against the record at query
                   time, and a nightly reconciliation
    rebuild_check  (exploratory) rebuild with the same query-time check
    cdc_outage, built_outage   (exploratory) cdc and built with the worker down for 12 office hours on one day
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from sync import index as ix
from sync.embed import Embedder
from sync.record import DSN, Record, chunk_texts, chunks

K = 4            # the tutorial's k
K_CHECK = 8      # the query-time check fetches this many and keeps the first K that pass
RM_URL = DSN.replace("postgresql://", "postgresql+psycopg://")


@dataclass
class Job:
    name: str
    prepare: Callable[[], tuple[int, Callable[[], dict], list[int] | None]]   # -> (chunks to embed, apply, articles)
    meta: dict = field(default_factory=dict)


def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


class Design:
    name = ""
    act = 2
    uses_slot = False
    ticks: list[tuple[str, object]] = []        # ("nightly", hour) or ("every", seconds)
    check = False

    def __init__(self, record: Record, client, emb: Embedder):
        self.record, self.client, self.emb = record, client, emb
        self.dirty = False
        self.notes: dict = {}

    # what the replay calls
    def start(self, rows: list[dict]) -> None: ...
    def on_event(self, ev: dict) -> list[Job]: return []
    def tick(self, kind: str, t: str) -> Job | None: return None
    def app_hook(self): return None
    def near(self, vec: np.ndarray, k: int) -> list[dict]: ...
    def of_article(self, article_id: int) -> list[dict]: ...
    def entries(self) -> list[dict]: ...

    def retrieve(self, vec: np.ndarray) -> tuple[list[dict], list[dict]]:
        """The K chunks the model reads, and (with the check) the ones dropped on the way.

        The check: fetch the K_CHECK nearest, read their articles from the record, and keep a chunk only if its text
        is still one of its article's chunks as the record has it now (a deleted article has none)."""
        if not self.check:
            return self.near(vec, K), []
        got = self.near(vec, K_CHECK)
        ids = list({int(g["article_id"]) for g in got})
        now = {r["id"]: set(chunk_texts(r)) for r in self.record.rows("WHERE id = ANY(%s)", (ids,))}
        keep, dropped = [], []
        for g in got:
            if g["text"] not in now.get(int(g["article_id"]), ()):
                dropped.append(g)
            elif len(keep) < K:
                keep.append(g)
        return keep, dropped


# --------------------------------------------------------------------------------------------- Weaviate designs
class WeaviateDesign(Design):
    def coll_name(self) -> str:
        return "D_" + self.name

    def new_collection(self, name: str | None = None):
        self.coll = ix.create(self.client, name or self.coll_name())
        return self.coll

    def store(self):
        from langchain_weaviate import WeaviateVectorStore
        return WeaviateVectorStore(self.client, index_name=self.coll.name, text_key="text", embedding=self.emb)

    def near(self, vec, k):
        return ix.near(self.coll, vec, k)

    def of_article(self, article_id):
        return ix.of_article(self.coll, article_id)

    def entries(self):
        return ix.entries(self.coll)


def all_docs(record: Record) -> list:
    return [d for r in record.rows() for d in chunks(r)]


class Once(WeaviateDesign):
    name, act = "once", 1

    def start(self, rows):
        self.new_collection()
        self.store().add_documents(all_docs(self.record))      # the tutorial: no ids


class Rerun(Once):
    name, act = "rerun", 1
    ticks = [("nightly", 2)]

    def tick(self, kind, t):
        def prepare():
            docs = all_docs(self.record)
            return len(docs), lambda: {"added": len(self.store().add_documents(docs))}, None
        return Job("rerun", prepare)


class Rebuild(WeaviateDesign):
    name = "rebuild"
    ticks = [("nightly", 2)]

    def _docs(self):
        return all_docs(self.record)

    def start(self, rows):
        self.gen = 0
        self.new_collection(f"{self.coll_name()}_0")
        self.store().add_documents(self._docs())

    def tick(self, kind, t):
        def prepare():
            docs = self._docs()

            def apply():
                old = self.coll
                self.gen += 1
                self.new_collection(f"{self.coll_name()}_{self.gen}")
                self.store().add_documents(docs)
                self.client.collections.delete(old.name)          # queries switch to the new one now
                return {"chunks": len(docs)}
            return len(docs), apply, None
        return Job("rebuild", prepare)


class RebuildCheck(Rebuild):
    name, act = "rebuild_check", 2
    check = True


def upsert_id(d) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{d.metadata['source']}#{d.metadata['n']}"))


class Upsert(WeaviateDesign):
    name = "upsert"
    ticks = [("nightly", 2)]

    def _docs(self):
        docs = []
        for r in self.record.rows():
            for n, d in enumerate(chunks(r)):
                d.metadata["n"] = n
                docs.append(d)
        return docs

    def _write(self, docs):
        ids = [upsert_id(d) for d in docs]
        for d in docs:
            d.metadata.pop("n")
        return self.store().add_documents(docs, ids=ids)

    def start(self, rows):
        self.new_collection()
        self._write(self._docs())

    def tick(self, kind, t):
        def prepare():
            docs = self._docs()
            return len(docs), lambda: {"written": len(self._write(docs))}, None
        return Job("upsert", prepare)


class RecordManager(WeaviateDesign):
    name = "record_manager"
    ticks = [("every", 300), ("nightly", 2)]
    KEY = "sha1"   # the default; "sha256" ids are not UUIDs, which Weaviate rejects

    def start(self, rows):
        from langchain_classic.indexes import SQLRecordManager
        self.new_collection()
        self.record.c.execute("DROP TABLE IF EXISTS upsertion_record")
        self.rm = SQLRecordManager(namespace="weaviate/help-center", db_url=RM_URL)
        self.rm.create_schema()
        self._index(all_docs(self.record), "full")

    def _index(self, docs, cleanup):
        from langchain_core.indexing import index
        return index(docs, self.rm, self.store(), cleanup=cleanup, source_id_key="source", key_encoder=self.KEY)

    def _new(self, docs) -> int:
        from langchain_core.indexing.api import _get_document_with_hash
        ids = [_get_document_with_hash(d, key_encoder=self.KEY).id for d in docs]
        return sum(1 for e in self.rm.exists(ids) if not e)

    def tick(self, kind, t):
        if kind == "every" and not self.dirty:
            return None   # nothing changed since the last run: index() would skip every chunk (shortcut, same result)
        cleanup = "incremental" if kind == "every" else "full"
        self.dirty = False

        def prepare():
            docs = all_docs(self.record)
            n = self._new(docs)
            return n, lambda: dict(self._index(docs, cleanup)), None
        return Job(f"record_manager {cleanup}", prepare)


class Poll(WeaviateDesign):
    name = "poll"
    ticks = [("every", 300)]

    def start(self, rows):
        self.new_collection()
        self.last = None
        for r in self.record.rows():
            self._replace(r, chunks(r))

    def _replace(self, row, docs):
        ix.delete_article(self.coll, row["id"])
        if docs:
            ix.insert(self.coll, [d.metadata | {"text": d.page_content} for d in docs],
                      self.emb.vectors([d.page_content for d in docs]))

    def tick(self, kind, t):
        since, self.last = self.last, t

        def prepare():
            rows = self.record.rows("WHERE updated_at > %s AND updated_at <= %s", (since, t)) if since else []
            work = [(r, chunks(r)) for r in rows]

            def apply():
                for r, docs in work:
                    self._replace(r, docs)
                return {"articles": len(work)}
            return sum(len(d) for _, d in work), apply, [r["id"] for r in rows]
        return Job("poll", prepare) if since else None

    def start_clock(self, t):
        self.last = t


class Cdc(WeaviateDesign):
    name = "cdc"
    uses_slot = True

    def start(self, rows):
        self.new_collection()
        for r in self.record.rows():
            self._put(r)

    def _put(self, row):
        docs = chunks(row)
        ix.insert(self.coll, [d.metadata | {"text": d.page_content} for d in docs],
                  self.emb.vectors([d.page_content for d in docs]))

    def on_event(self, ev):
        return [self._job(op, aid) for op, aid in self.record.changes()]

    def _job(self, op, aid):
        def prepare():
            row = self.record.row(aid)
            n = len(chunks(row)) if row else 0

            def apply():
                gone = ix.delete_article(self.coll, aid)
                if row:
                    self._put(row)
                return {"deleted": gone}
            return n, apply, [aid]
        return Job(f"cdc {op}", prepare, {"article": aid})


class Built(Cdc):
    name, act = "built", 3
    ticks = [("nightly", 2)]
    check = True

    def _objs(self, row):
        return [(d.metadata | {"text": d.page_content, "chunk_hash": chunk_hash(d.page_content)}) for d in chunks(row)]

    def _put(self, row):
        objs = self._objs(row)
        ix.insert(self.coll, objs, self.emb.vectors([o["text"] for o in objs]))

    def _plan(self, aid, row, have):
        """What to add, delete and re-stamp for one article, given its entries in the index."""
        want = self._objs(row) if row else []
        want_by = {}
        for o in want:
            want_by.setdefault(o["chunk_hash"], []).append(o)
        add, delete, stamp = [], [], []
        seen = set()
        for e in have:
            ch = e.get("chunk_hash")
            if ch in want_by and ch not in seen:
                seen.add(ch)
                w = want_by[ch][0]
                if e.get("source") != w["source"]:          # a rename: the text is the same, the URL isn't
                    stamp.append((e["uuid"], {"source": w["source"]}))
            else:
                delete.append(e["uuid"])
        add = [o for ch, os_ in want_by.items() if ch not in seen for o in os_[:1]]
        return add, delete, stamp

    def _apply_plan(self, add, delete, stamp):
        from weaviate.classes.query import Filter
        if delete:
            self.coll.data.delete_many(where=Filter.by_id().contains_any(delete))
        for u, props in stamp:
            self.coll.data.update(uuid=u, properties=props)
        if add:
            ix.insert(self.coll, add, self.emb.vectors([o["text"] for o in add]))
        return {"added": len(add), "deleted": len(delete), "restamped": len(stamp)}

    def _job(self, op, aid):
        def prepare():
            row = self.record.row(aid)
            add, delete, stamp = self._plan(aid, row, ix.of_article(self.coll, aid))
            return len(add), lambda: self._apply_plan(add, delete, stamp), [aid]
        return Job(f"built {op}", prepare, {"article": aid})

    def tick(self, kind, t):
        def prepare():
            rows = {r["id"]: r for r in self.record.rows()}
            by = {}
            for e in ix.entries(self.coll):
                by.setdefault(int(e["article_id"]), []).append(e)
            add, delete, stamp = [], [], []
            for aid in set(rows) | set(by):
                a, d, s = self._plan(aid, rows.get(aid), by.get(aid, []))
                add += a
                delete += d
                stamp += s

            def apply():
                out = self._apply_plan(add, delete, stamp)
                self.notes.setdefault("reconciliation", []).append({"t": t, **out})
                return out
            return len(add), apply, None
        return Job("built reconciliation", prepare)


class Outage:
    """Exploratory: the CDC worker is down for 12 office hours (08:00-20:00 on outage_day). Changes wait in the
    replication slot, and are read when the worker comes back."""
    outage_day = {"pilot": 2, "full": 9}
    outage: tuple[float, float] = (0, 0)

    def on_event(self, ev):
        from sync.replay import ts
        if self.outage[0] <= ts(ev["t"]) < self.outage[1]:
            return []
        return super().on_event(ev)

    def tick(self, kind, t):
        if kind == "resume":
            return [self._job(op, aid) for op, aid in self.record.changes()]
        return super().tick(kind, t)


class CdcOutage(Outage, Cdc):
    name = "cdc_outage"


class BuiltOutage(Outage, Built):
    name, act = "built_outage", 2


# --------------------------------------------------------------------------------------------- same database
class SameDb(Design):
    name = "same_db"

    def start(self, rows):
        self.pg = ix.PgChunks(self.record.c)
        self.record.c.execute("TRUNCATE chunks")
        for r in self.record.rows():
            with self.record.c.transaction():
                with self.record.c.cursor() as cur:
                    self._hook(cur, r)

    def _hook(self, cur, row):
        docs = chunks(row)
        self.pg.write(cur, row["id"], docs, self.emb.vectors([d.page_content for d in docs]))

    def app_hook(self):
        return self._hook

    def near(self, vec, k):
        return self.pg.near(vec, k)

    def of_article(self, article_id):
        return self.pg.of_article(article_id)

    def entries(self):
        return self.pg.entries()


DESIGNS = {d.name: d for d in [Once, Rerun, Rebuild, Upsert, RecordManager, Poll, Cdc, SameDb, Built, RebuildCheck,
                                CdcOutage, BuiltOutage]}
ORDER = ["once", "rerun", "rebuild", "upsert", "record_manager", "poll", "cdc", "same_db", "built", "rebuild_check",
         "cdc_outage", "built_outage"]
