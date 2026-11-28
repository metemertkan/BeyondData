"""Episode 6: replay one month of changes to the help center into one design, on a simulated clock.

The record is reset to the start of the month, the design builds its index from it, and then every change is
applied to Postgres at its time, in order: saves through the application (`updated_at` set to the change's time),
hard deletes, and the migration's SQL. The design learns about changes only its own way (a nightly read, a poll
of `updated_at`, the logical decoding slot, or the save's transaction).

Jobs take simulated time: chunks embedded x SECONDS_PER_CHUNK. A question at time t sees what had finished by t.
Every question's retrieved chunks are logged and classified against the record at that moment; the index is
audited at 12:00 every day; and for every change, the replay records when the index first held the article's
current chunks ("current") and when it held nothing else of it ("clean").
"""
from __future__ import annotations

import heapq
import json
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sync import score
from sync.designs import DESIGNS, Design
from sync.embed import SECONDS_PER_CHUNK, Embedder
from sync.record import Record

PRIO = {"event": 0, "done": 1, "tick": 2, "start": 3, "question": 4, "audit": 5}


def ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def iso(x: float) -> str:
    return datetime.fromtimestamp(x, tz=timezone.utc).isoformat()


class Replay:
    def __init__(self, name: str, kb: dict, record: Record, client, emb: Embedder, out: Path, log=print):
        self.name, self.kb, self.record, self.client, self.emb = name, kb, record, client, emb
        self.out, self.log = out, log
        self.d: Design = DESIGNS[name](record, client, emb)
        self.heap: list = []
        self.seq = 0
        self.queue: deque = deque()
        self.busy = False
        self.live: dict[int, dict] = {}
        self.pending: dict[int, dict] = {}     # article -> {"t": first unsynced change, "current": t or None}
        self.sync_log: list[dict] = []
        self.jobs: list[dict] = []
        self.qlog: list[dict] = []
        self.audits: list[dict] = []

    def push(self, t: float, kind: str, payload=None):
        heapq.heappush(self.heap, (t, PRIO[kind], self.seq, kind, payload))
        self.seq += 1

    # ------------------------------------------------------------------ setup
    def setup(self) -> dict:
        kb = self.kb
        self.t0, self.t_end = ts(kb["meta"]["start"]), ts(kb["meta"]["end"])
        self.record.reset(kb["articles"], slot=self.d.uses_slot)
        for name in list(self.client.collections.list_all()):
            if name.lower().startswith("d_" + self.d.name.lower()):
                self.client.collections.delete(name)
        self.live = {a["id"]: a for a in kb["articles"]}
        r0, c0, s0 = self.emb.requested, self.emb.computed, time.time()
        self.d.start(kb["articles"])
        if hasattr(self.d, "start_clock"):
            self.d.start_clock(kb["meta"]["start"])
        initial = {"chunks_embedded": self.emb.requested - r0, "computed": self.emb.computed - c0,
                   "wall_s": round(time.time() - s0, 1), "entries": len(self.d.entries())}
        for e in kb["events"]:
            self.push(ts(e["t"]), "event", e)
        for q in kb["questions"]:
            self.push(ts(q["t"]), "question", q)
        start = datetime.fromisoformat(kb["meta"]["start"])
        for i in range(int((self.t_end - self.t0) // 86400) + 1):
            noon = (start + timedelta(days=i)).replace(hour=12)
            if noon.timestamp() < self.t_end:
                self.push(noon.timestamp(), "audit")
        if hasattr(self.d, "outage_day"):
            day = start + timedelta(days=self.d.outage_day[self.kb["meta"]["run"]])
            self.d.outage = (day.replace(hour=8).timestamp(), day.replace(hour=20).timestamp())
            self.push(self.d.outage[1], "tick", ("resume", self.d.outage[1]))
        for kind, arg in self.d.ticks:
            if kind == "nightly":
                for i in range(1, int((self.t_end - self.t0) // 86400) + 1):
                    t = (start + timedelta(days=i)).replace(hour=arg).timestamp()
                    if t < self.t_end:
                        self.push(t, "tick", (kind, t))
            else:
                t = self.t0 + arg
                while t < self.t_end:
                    self.push(t, "tick", (kind, t))
                    t += arg
        return initial

    # ------------------------------------------------------------------ the loop
    def run(self) -> dict:
        wall = time.time()
        initial = self.setup()
        r_month = self.emb.requested
        n = 0
        while self.heap:
            t, _, _, kind, p = heapq.heappop(self.heap)
            self.now = t
            getattr(self, "on_" + kind)(t, p)
            n += 1
            if n % 2000 == 0:
                self.log(f"  {self.d.name}: {iso(t)[:16]} queue {len(self.queue)} pending {len(self.pending)}")
        for aid, p in self.pending.items():
            self.sync_log.append({"article": aid, "t": p["t"], "why": p["why"], "current_s": p["current"],
                                  "clean_s": None})
        res = {"design": self.d.name, "act": self.d.act, "initial": initial,
               "month": {"chunks_embedded": self.emb.requested - r_month,
                         "embed_cpu_s": round((self.emb.requested - r_month) * SECONDS_PER_CHUNK, 1),
                         "jobs": len(self.jobs)},
               "final": self.audits[-1] if self.audits else {}, "notes": self.d.notes,
               "wall_s": round(time.time() - wall, 1)}
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / f"{self.d.name}.json").write_text(json.dumps(
            res | {"audits": self.audits, "jobs": self.jobs, "sync": self.sync_log}, indent=1, default=str))
        with (self.out / f"{self.d.name}.questions.jsonl").open("w") as f:
            for x in self.qlog:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        return res

    # ------------------------------------------------------------------ handlers
    def on_event(self, t, e):
        hook = self.d.app_hook()
        if e["op"] == "save":
            self.record.save(e["row"], e["t"], hook=hook)
            self.live[e["row"]["id"]] = e["row"]
            touched = [e["row"]["id"]]
        elif e["op"] == "delete":
            self.record.delete(e["id"])
            self.live.pop(e["id"], None)
            touched = [e["id"]]
        else:
            before = {k: (v["title"], v["body"]) for k, v in self.live.items()}
            rows = self.record.sql(e["sql"])
            self.live = {r["id"]: r for r in self.record.rows()}
            touched = [k for k, v in self.live.items() if (v["title"], v["body"]) != before.get(k)]
            e = e | {"rows_changed": rows}
        why = e["why"]
        for aid in touched:
            if aid not in self.pending:
                self.pending[aid] = {"t": t, "why": why, "current": None}
        self.d.dirty = True
        if hook is not None:                    # same database: the save itself updated the chunks
            self.check_sync(t, touched)
        for job in self.d.on_event(e):
            self.enqueue(t, job)

    def on_tick(self, t, p):
        jobs = self.d.tick(p[0], iso(p[1]))
        for job in (jobs if isinstance(jobs, list) else [jobs]):
            if job is not None:
                self.enqueue(t, job)

    def enqueue(self, t, job):
        self.queue.append((t, job))
        if not self.busy:
            self.busy = True
            self.push(t, "start")

    def on_start(self, t, _):
        enq, job = self.queue.popleft()
        n, apply, articles = job.prepare()
        self.push(t + n * SECONDS_PER_CHUNK, "done", (job, enq, t, n, apply, articles))

    def on_done(self, t, p):
        job, enq, started, n, apply, articles = p
        w = time.time()
        r0 = self.emb.requested
        out = apply()
        charged = self.emb.requested - r0
        self.jobs.append({"job": job.name, "enqueued": enq, "started": started, "done": t, "chunks": n,
                          "charged": charged, "db_s": round(time.time() - w, 3), "out": out, **job.meta})
        self.check_sync(t, articles)
        if self.queue:
            self.push(t, "start")
        else:
            self.busy = False

    def check_sync(self, t, articles):
        """After a job (or a same-database save): which pending articles are now current, and clean?"""
        ids = list(self.pending) if articles is None else [a for a in articles if a in self.pending]
        for aid in ids:
            p = self.pending[aid]
            has_all, clean = score.in_sync(self.d.of_article(aid), self.live.get(aid))
            if has_all and p["current"] is None:
                p["current"] = t - p["t"]
            if clean:
                self.sync_log.append({"article": aid, "t": p["t"], "why": p["why"], "current_s": p["current"],
                                      "clean_s": t - p["t"]})
                del self.pending[aid]

    def on_question(self, t, q):
        vec = self.emb.query(q["question"])
        got, dropped = self.d.retrieve(vec)
        classes = score.classify(got, self.live)
        ctx = "\n\n".join(g["text"] for g in got)
        right, stale = score.mentions(q, ctx)
        self.qlog.append({"qid": q["qid"], "t": q["t"], "kind": q["kind"], "delay": q["delay"],
                          "chunks": [{"text": g["text"], "article_id": int(g["article_id"]), "source": g.get("source"),
                                      "class": c} for g, c in zip(got, classes)],
                          "dropped": [{"article_id": int(g["article_id"]), "class": c} for g, c in
                                      zip(dropped, score.classify(dropped, self.live))],
                          "context_right": right, "context_stale": stale})

    def on_audit(self, t, _):
        a = score.audit(self.d.entries(), self.live)
        self.audits.append({"t": iso(t), **a, "pending": len(self.pending), "queue": len(self.queue)})
