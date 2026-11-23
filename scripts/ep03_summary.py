"""Episode 3 summary: results/ep03/<size>/*.json|npz -> summary.json and summary.md.

    uv run python -m scripts.ep03_summary --size full

Every reported number is on test questions (the ones the run covered); tuning questions only choose settings.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from scripts.ep03_run import sweep_questions
from vectors.data import K
from vectors.filters import CONDS, FIELDS, RANDOM, SELECTIVITY, Filters

ROOT = Path(__file__).resolve().parent.parent
DBS = ["pgvector", "qdrant", "milvus", "weaviate", "elasticsearch", "chroma"]
TARGETS = [0.80, 0.85, 0.90, 0.95, 0.97, 0.99]
NDCG_SLACK = 0.005
CHECK_N = 200
SEED = 7
CHECKED = ["none"] + RANDOM            # the fields the built procedure tunes and checks
SAME_BAND = {"topic": "team", "subtopic": "project"}  # topical fields get the setting of the same selectivity
# per database: deployments (what needs a reload or a collection-wide change) -> options usable per query on it
GROUPS = {
    "pgvector": {"as shipped": ["default", "iterative"], "B-tree indexes": ["btree"]},
    "qdrant": {"no payload index": ["default"], "payload index added later": ["index_later"],
               "payload index first": ["index_first", "acorn"]},
    "milvus": {"dynamic field": ["default"], "declared fields": ["schema"], "declared + scalar index": ["schema_index"]},
    "weaviate": {"acorn (as shipped)": ["default"], "sweeping": ["sweeping"], "pathseer": ["pathseer"]},
    "elasticsearch": {"acorn (as shipped)": ["default", "exact"], "fanout": ["fanout", "exact"]},
    "chroma": {"as shipped": ["default"]},
}
LABEL = {"none": "no filter", **{f: f"{f} {SELECTIVITY[f]}" for f in FIELDS}}


class Cell:
    """One (option, knob, condition): per-question arrays and metrics on any question subset."""

    def __init__(self, F: Filters, cond: str, ids: np.ndarray, lat: np.ndarray):
        self.cond, self.ids, self.lat = cond, ids, lat
        self.ran = ~np.isnan(lat)
        exact, labels = F.exact(cond), F.data.labels
        self.expected = F.expected(cond)
        self.got = (ids >= 0).sum(1)
        self.wrong = self.got - F.matches(cond, ids)
        self.recall = np.array([len(set(ids[i][ids[i] >= 0]) & set(exact[i][exact[i] >= 0])) / max(1, self.expected[i])
                                for i in range(len(ids))])
        disc = 1 / np.log2(np.arange(2, K + 2))
        self.ndcg, self.hit, self.lost, self.ex_ndcg, self.ex_hit = (np.zeros(len(ids)) for _ in range(5))
        for i in range(len(ids)):
            rel = labels[i]
            ideal = disc[: min(len(rel), K)].sum()
            g = np.array([1.0 if d in rel else 0.0 for d in ids[i]])
            ge = np.array([1.0 if d in rel else 0.0 for d in exact[i]])
            self.ndcg[i], self.hit[i] = (g * disc).sum() / ideal, g.any()
            self.ex_ndcg[i], self.ex_hit[i] = (ge * disc).sum() / ideal, ge.any()
            self.lost[i] = ge.any() and not g.any()

    def qs(self, questions: np.ndarray) -> np.ndarray:
        return questions[self.ran[questions]]

    def metrics(self, questions: np.ndarray) -> dict:
        q = self.qs(questions)
        if len(q) == 0:
            return {}
        return {"n": int(len(q)), "returned": float(self.got[q].mean()),
                "short": float((self.got[q] < self.expected[q]).mean()),
                "zero": float(((self.got[q] == 0) & (self.expected[q] > 0)).mean()),
                "wrong": int(self.wrong[q].sum()), "recall": float(self.recall[q].mean()),
                "ndcg": float(self.ndcg[q].mean()), "hit": float(self.hit[q].mean()),
                "exact_ndcg": float(self.ex_ndcg[q].mean()), "lost": int(self.lost[q].sum()),
                "lost_rate": float(self.lost[q].mean()),
                "p50_ms": round(float(np.percentile(self.lat[q], 50)) * 1000, 2),
                "p95_ms": round(float(np.percentile(self.lat[q], 95)) * 1000, 2)}


def load_run(F: Filters, folder: Path, db: str):
    """One database's json and cells; the plan-cache check's arrays (pgvector) come back separately."""
    meta, arr = json.loads((folder / f"{db}.json").read_text()), np.load(folder / f"{db}.npz")
    cells, extra = {}, {}
    for k in [k for k in arr.files if k.endswith("_ids")]:
        if k.startswith("plancache__"):
            extra[k[len("plancache__"):-4]] = (arr[k], arr[k[:-4] + "_lat"])
            continue
        option, knob, cond = k[:-4].split("__")
        cells[(option, None if knob == "d" else int(knob), cond)] = Cell(F, cond, arr[k], arr[k[:-4] + "_lat"])
    return meta, cells, extra


def load(size: str):
    src = ROOT / "results" / "ep03" / size
    F = Filters(size)
    runs, extras = {}, {}
    for db in DBS:
        if not (src / f"{db}.json").exists():
            continue
        meta, cells, extra = load_run(F, src, db)
        runs[db], extras[db] = (meta, cells), extra
    return src, F, runs, extras


def fmt_knob(k):
    return "default" if k is None else str(k)


def main(size: str) -> None:
    src, F, runs, extras = load(size)
    d = F.data
    n_run = next(iter(runs.values()))[0]["questions"] if runs else 0
    in_run = np.arange(n_run)
    test = np.intersect1d(d.test, in_run)
    tune = np.intersect1d(d.tune, in_run)
    stest = np.intersect1d(sweep_questions(d, in_run), d.test)  # test questions every knob value ran on
    out: dict = {"size": size, "passages": int(len(d.rows)), "test_questions": int(len(test)), "dbs": {}}
    md = [f"# Episode 3 results ({size}: {len(d.rows):,} passages, {len(test):,} test questions)\n"]

    # the ceiling: exact filtered search, per condition
    any_cells = next(iter(runs.values()))[1] if runs else {}
    md.append("## Exact search inside the filter (the ceiling)\n\n| Condition | Median filter size | nDCG@10 | hit@10 |\n"
              "| :--- | ---: | ---: | ---: |")
    out["exact"] = {}
    for c in CONDS:
        cell = any_cells.get(("default", None, c))
        if cell is None:
            continue
        ex_hit = float(cell.ex_hit[test].mean())
        out["exact"][c] = {"ndcg": float(cell.ex_ndcg[test].mean()), "hit": ex_hit,
                           "median_size": int(np.median(F.size_of(c)[test]))}
        md.append(f"| {LABEL[c]} | {out['exact'][c]['median_size']:,} | {out['exact'][c]['ndcg']:.4f} | {ex_hit:.4f} |")

    # Act 1
    md.append("\n## Act 1: as shipped (fields stored the quickstart way, filter in the query, nothing else)\n")
    tables = [("Results returned (mean, of 10)", "returned", "{:.2f}"), ("Questions with fewer results than exist", "short", "{:.1%}"),
              ("Questions with no results at all", "zero", "{:.1%}"), ("Recall@10 inside the filter", "recall", "{:.3f}"),
              ("nDCG@10", "ndcg", "{:.3f}"), ("Answer lost (exact filtered search finds it, the database doesn't)", "lost", "{}"),
              ("p50 latency (ms)", "p50_ms", "{}")]
    act1 = {db: {c: cells[("default", None, c)].metrics(test) for c in CONDS if ("default", None, c) in cells}
            for db, (meta, cells) in runs.items()}
    for title, m, f in tables:
        md.append(f"**{title}**\n\n| Database | " + " | ".join(LABEL[c] for c in CONDS) + " |\n| :--- |" + " ---: |" * len(CONDS))
        for db, row in act1.items():
            md.append(f"| {db} | " + " | ".join(f.format(row[c][m]) + ("*" if row[c]["n"] < len(test) else "")
                                               if c in row and row[c] else "" for c in CONDS) + " |")
        if m == "ndcg":
            md.append("| exact | " + " | ".join(f"{out['exact'][c]['ndcg']:.3f}" if c in out["exact"] else "" for c in CONDS) + " |")
        md.append("")
    md.append("\\* sampled: the cell averaged over 250 ms on its first 100 questions and stopped there (pilot: at 300).\n")
    wrong = {db: sum(r[c]["wrong"] for c in r if r[c]) for db, r in act1.items()}
    md.append(f"Results that didn't match the filter: {wrong}.\n")
    for db in act1:
        out["dbs"][db] = {"act1": act1[db]}

    # pgvector plans
    if "pgvector" in runs:
        md.append("**pgvector plans**: EXPLAIN (planned afresh, 20 tuning questions per condition) → the plan the cell's "
                  "prepared statement ran with (EXPLAIN EXECUTE, first tuning question; amendment 4), generic/custom plans:\n")
        base = runs["pgvector"][0]["deployments"]["base"]
        for opt, o in base["options"].items():
            by_knob = o["plans"] if "d" in o["plans"] else {"d": o["plans"]}
            for kn, plans in by_knob.items():
                parts = []
                for c in CONDS:
                    s = ", ".join(f"{p} ×{n}" for p, n in Counter(plans[c]).most_common())
                    cell = o["cells"].get(f"{opt}__{kn}__{c}", {})
                    if cell.get("ran_plan"):
                        pc = cell.get("prepared", {})
                        s += f" → ran {cell['ran_plan']} ({pc.get('generic', 0)}/{pc.get('custom', 0)})"
                    parts.append(f"{LABEL[c]}: {s}")
                md.append(f"- {opt}, ef_search {'default' if kn == 'd' else kn}: " + "; ".join(parts))
        md.append("")
        pc = base.get("plancache_check")
        if pc and extras.get("pgvector"):
            q = F.data.tune[: pc["questions"]]
            md.append(f"**pgvector plan-cache check** (amendment 4: the same {pc['questions']} tuning questions filtered on "
                      f"{pc['cond']}, one connection)\n\n| Step | ef_search | EXPLAIN shows | Statement ran with | "
                      f"Generic / custom plans | Returned (mean) | Short | Recall | p50 ms |\n"
                      f"| :--- | ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: |")
            out["plancache_check"] = {}
            for step, st in pc["steps"].items():
                ids, lat = extras["pgvector"][step]
                m = Cell(F, pc["cond"], ids, lat).metrics(q)
                out["plancache_check"][step] = {**st, **m}
                md.append(f"| {step} {'(' + st['sql'] + ')' if st['sql'] else ''} | {st['ef_search']} | {st['explain']} | "
                          f"{st['ran']} | {st['prepared'].get('generic', 0)} / {st['prepared'].get('custom', 0)} | "
                          f"{m['returned']:.2f} | {m['short']:.0%} | {m['recall']:.3f} | {m['p50_ms']} |")
            md.append("")
        first = src / "first_run_pgvector"
        if (first / "pgvector.npz").exists():
            _, fcells, _ = load_run(F, first, "pgvector")
            cells = runs["pgvector"][1]
            md.append(f"**pgvector, same setting, two plans** (recall / short / p50 ms on {len(stest):,} test questions): "
                      "first run (statements kept the plan made at ef_search 40) → re-run (a connection per setting)\n\n"
                      "| Option | Knob | " + " | ".join(LABEL[c] for c in CONDS) + " |\n| :--- | ---: |" + " :--- |" * len(CONDS))
            out["pgvector_first_run"] = {}
            for (o, k) in sorted({(o, k) for (o, k, c) in fcells if k is not None},
                                 key=lambda x: (["default", "iterative", "btree"].index(x[0]), x[1])):
                row = []
                for c in CONDS:
                    a, b = fcells.get((o, k, c)), cells.get((o, k, c))
                    if not (a and b):
                        row.append("")
                        continue
                    ma, mb = a.metrics(stest), b.metrics(stest)
                    out["pgvector_first_run"][f"{o}__{k}__{c}"] = {"first": ma, "rerun": mb}
                    row.append(f"{ma['recall']:.3f} / {ma['short']:.0%} / {ma['p50_ms']} → "
                               f"{mb['recall']:.3f} / {mb['short']:.0%} / {mb['p50_ms']}" + ("*" if mb["n"] < len(stest) else ""))
                md.append(f"| {o} | {k} | " + " | ".join(row) + " |")
            md.append("")
            # the default-knob cells were planned under the setting they ran with in both runs: they should agree, up to
            # the HNSW graph being built again (pgvector builds it with parallel workers)
            rep = {}
            for (o, k, c), a in fcells.items():
                b = cells.get((o, k, c))
                if k is None and b is not None:
                    ma, mb = a.metrics(test), b.metrics(test)
                    rep[f"{o}__{c}"] = {"first": ma, "rerun": mb, "recall_diff": mb["recall"] - ma["recall"],
                                        "returned_diff": mb["returned"] - ma["returned"]}
            out["pgvector_repro"] = rep
            worst = max(rep.items(), key=lambda kv: abs(kv[1]["recall_diff"]))
            md.append(f"Default-knob cells, first run vs re-run ({len(rep)} cells, all test questions): largest recall "
                      f"difference {worst[1]['recall_diff']:+.3f} ({worst[0]}); largest difference in results returned "
                      f"{max(abs(v['returned_diff']) for v in rep.values()):.2f}.\n")

    # Load
    md.append("## Load, by deployment\n\n| Database | Deployment | Load (s) | Index wait (s) | Settle (s) | Option applied (s) | "
              "Disk after load (GB) | Disk at end (GB) |\n| :--- | :--- | ---: | ---: | ---: | :--- | ---: | ---: |")
    for db, (meta, cells) in runs.items():
        for dep, dres in meta["deployments"].items():
            applied = "; ".join(f"{o}: {v.get('apply_s')}" for o, v in dres.get("options", {}).items() if v.get("apply_s", 0) > 1)
            md.append(f"| {db} | {dep} | {dres.get('load_s', 0):.0f} | {dres.get('index_wait_s', 0):.0f} | {dres.get('settle_s', 0):.0f} | "
                      f"{applied} | {dres.get('disk_bytes_after_load', 0) / 1e9:.2f} | {dres.get('disk_bytes_end', 0) / 1e9:.2f} |")
        out["dbs"].setdefault(db, {})["deployments"] = {dep: {k: v for k, v in dres.items() if k != "options"} | {
            "options": {o: {k: v for k, v in ov.items() if k not in ("cells",)} for o, ov in dres.get("options", {}).items()}}
            for dep, dres in meta["deployments"].items()}

    # Act 2: every option and knob, test questions
    md.append(f"\n## Act 2: the options ({len(stest):,} test questions every setting ran on; recall inside the filter / "
              f"short results / p50 ms)\n")
    for db, (meta, cells) in runs.items():
        opts = sorted({(o, k) for (o, k, c) in cells}, key=lambda x: (list(dict.fromkeys(o for o, _, _ in cells)).index(x[0]),
                                                                       -1 if x[1] is None else x[1]))
        md.append(f"**{db}**\n\n| Option | Knob | " + " | ".join(LABEL[c] for c in CONDS) + " |\n| :--- | ---: |" + " ---: |" * len(CONDS))
        rows = []
        for o, k in opts:
            ms = {c: cells[(o, k, c)].metrics(stest) for c in CONDS if (o, k, c) in cells}
            rows.append({"option": o, "knob": k, "conds": ms})
            md.append(f"| {o} | {fmt_knob(k)} | " + " | ".join(
                f"{ms[c]['recall']:.3f} / {ms[c]['short']:.0%} / {ms[c]['p50_ms']}" + ("*" if ms[c]['n'] < len(stest) else "")
                if ms.get(c) else "" for c in CONDS) + " |")
        out["dbs"][db]["sweep"] = rows
        md.append("")

    # Act 3: target from labels
    points = []
    for db, (meta, cells) in runs.items():
        for (o, k, c), cell in cells.items():
            if c in RANDOM:
                q = cell.qs(tune)
                if len(q):
                    points.append((cell.recall[q].mean(), cell.ndcg[q].mean(), cell.ex_ndcg[q].mean()))
    target = next((t for t in TARGETS if all(n >= e - NDCG_SLACK for r, n, e in points if r >= t)), TARGETS[-1])
    out["built_target_recall"] = target
    out["target_table"] = {str(t): {"worst_ndcg_loss": max((e - n for r, n, e in points if r >= t), default=None),
                                    "settings": int(sum(r >= t for r, n, e in points))} for t in TARGETS}
    rng = np.random.default_rng(SEED)
    sample = np.sort(rng.choice(stest, min(CHECK_N, len(stest)), replace=False))

    def ok(cell, q) -> bool:
        q = cell.qs(q)
        return bool(len(q) > 0 and cell.recall[q].mean() >= target and (cell.got[q] >= cell.expected[q]).all())

    def seen(cell, q) -> dict:
        """What the deploy check saw: recall on the sample, and how many sample questions came back short."""
        q = cell.qs(q)
        return {"recall": float(cell.recall[q].mean()) if len(q) else None, "short": int((cell.got[q] < cell.expected[q]).sum())}

    md.append(f"\n## Act 3: built (target recall {target}: the lowest target at which no setting on a random filter loses more "
              f"than {NDCG_SLACK * 100:.1f} nDCG points against exact filtered search, tuning questions)\n")
    md.append("| Target recall | Settings at or above it (all databases, random filters) | Worst nDCG loss among them (points) |\n"
              "| ---: | ---: | ---: |")
    for t, v in out["target_table"].items():
        loss = v["worst_ndcg_loss"]
        md.append(f"| {t} | {v['settings']} | {'' if loss is None else f'{loss * 100:.2f}'} |")
    md.append("")
    md.append("Per database: the deployment, and per field the cheapest setting (tuning p50) with recall ≥ target and full "
              "results on tuning questions. Topical fields use the setting of the random field with the same selectivity.\n")
    md.append("| Database | Deployment | " + " | ".join(LABEL[c] for c in CHECKED) + " | Worst p50 (ms) |\n| :--- | :--- |" +
              " :--- |" * len(CHECKED) + " ---: |")
    for db, (meta, cells) in runs.items():
        best = None
        for dep, options in GROUPS[db].items():
            choice = {}
            for c in CHECKED:
                cands = [(cell.metrics(tune)["p50_ms"], o, k) for (o, k, cc), cell in cells.items()
                         if cc == c and o in options and cell.metrics(tune) and ok(cell, tune)]
                choice[c] = min(cands, key=lambda x: x[0]) if cands else None
            feasible = sum(v is not None for v in choice.values())
            worst = max((v[0] for v in choice.values() if v), default=float("inf"))
            if any(o in options for (o, _, _) in cells):  # this deployment was measured
                cand = (feasible, -worst, dep, choice)
                if best is None or cand[:2] > best[:2]:
                    best = cand
        if best is None:
            continue
        feasible, negworst, dep, choice = best
        md.append(f"| {db} | {dep} | " + " | ".join(f"{v[1]} @ {fmt_knob(v[2])} ({v[0]} ms)" if v else "✗ none"
                                                    for v in (choice[c] for c in CHECKED)) +
                  f" | {-negworst if feasible == len(CHECKED) else '—'} |")
        # held out: test questions, all conditions; deploy checks at default and built
        built_rows, checks = {}, {}
        for c in CONDS:
            ch = choice.get(SAME_BAND.get(c, c))
            dflt = cells.get(("default", None, c))
            checks[c] = {"default": bool(dflt and ok(dflt, sample)) if c in CHECKED else None,
                         "default_n": int(len(dflt.qs(sample))) if dflt else 0,
                         "default_seen": seen(dflt, sample) if dflt else None}
            if ch:
                cell = cells[(ch[1], ch[2], c)]
                built_rows[c] = {"option": ch[1], "knob": ch[2], **cell.metrics(stest)}
                checks[c]["built"] = ok(cell, sample) if c in CHECKED else None
                checks[c]["built_n"] = int(len(cell.qs(sample)))
                checks[c]["built_seen"] = seen(cell, sample)
        out["dbs"][db]["built"] = {"deployment": dep, "choice": {c: (v[1], v[2], v[0]) if v else None for c, v in choice.items()},
                                   "test": built_rows, "checks": checks}

    md.append(f"\n**Built settings on the test questions** ({len(stest):,}; recall / short / answer lost / p50 ms; topical "
              f"fields held out)\n")
    md.append("| Database | " + " | ".join(LABEL[c] for c in CONDS) + " |\n| :--- |" + " ---: |" * len(CONDS))
    for db in runs:
        b = out["dbs"][db].get("built")
        if not b:
            continue
        md.append(f"| {db} | " + " | ".join(
            (f"{r['recall']:.3f}{'' if r['recall'] >= target else ' ✗'} / {r['short']:.0%} / {r['lost']} / {r['p50_ms']}"
             if (r := b["test"].get(c)) else "✗") for c in CONDS) + " |")
    md.append(f"\n**Deploy check** ({len(sample)} test questions per field, seed {SEED}: recall ≥ {target} and no short result)\n")
    md.append("| Database | " + " | ".join(f"{LABEL[c]}: default → built" for c in CHECKED) + " |\n| :--- |" + " :---: |" * len(CHECKED))
    for db in runs:
        b = out["dbs"][db].get("built")
        if not b:
            continue
        def mark(v, n, sn):
            s = "pass" if v else ("FAIL" if v is False else "—")
            if v is not None and sn and sn["recall"] is not None:
                s += f" {sn['recall']:.3f}" + (f", {sn['short']} short" if sn["short"] else "")
            return s + (f" (n={n})" if v is not None and n < len(sample) else "")
        md.append(f"| {db} | " + " | ".join(f"{mark(b['checks'][c]['default'], b['checks'][c]['default_n'], b['checks'][c]['default_seen'])} → "
                                           f"{mark(b['checks'][c].get('built'), b['checks'][c].get('built_n', 0), b['checks'][c].get('built_seen'))}"
                                           for c in CHECKED) + " |")
    md.append(f"\n(Recall on the sample, and sample questions with a short result. n=…: a sampled cell; only the sample "
              f"questions it ran are checked.)")

    # Exploratory, decided after seeing the results (not part of the fixed design): the same procedure, choosing with a
    # margin of 0.005 above the target on tuning questions, checked at the target on the same 200 questions.
    margin = 0.005

    def ok_at(cell, q, thr) -> bool:
        q = cell.qs(q)
        return bool(len(q) > 0 and cell.recall[q].mean() >= thr and (cell.got[q] >= cell.expected[q]).all())

    md.append(f"\n**Exploratory, after the results: choose with a margin** (tuning recall ≥ {target + margin:.3f}, same "
              f"deployment; then the same deploy check at {target}). Setting (test p50 ms) → check.\n")
    md.append("| Database | " + " | ".join(LABEL[c] for c in CHECKED) + " |\n| :--- |" + " :--- |" * len(CHECKED))
    out["margin"] = {}
    for db, (meta, cells) in runs.items():
        b = out["dbs"][db].get("built")
        if not b:
            continue
        options = GROUPS[db][b["deployment"]]
        row, res = [], {}
        for c in CHECKED:
            cands = [(cell.metrics(tune)["p50_ms"], o, k) for (o, k, cc), cell in cells.items()
                     if cc == c and o in options and cell.metrics(tune) and ok_at(cell, tune, target + margin)]
            ch = min(cands, key=lambda x: x[0]) if cands else None
            if not ch:
                row.append("✗ none")
                res[c] = None
                continue
            cell = cells[(ch[1], ch[2], c)]
            passed = ok_at(cell, sample, target)
            res[c] = {"option": ch[1], "knob": ch[2], "check": passed, "test_p50_ms": cell.metrics(stest)["p50_ms"],
                      "seen": seen(cell, sample), "test_recall": cell.metrics(stest)["recall"]}
            row.append(f"{ch[1]} @ {fmt_knob(ch[2])} ({res[c]['test_p50_ms']}) → {'pass' if passed else 'FAIL'} "
                       f"{res[c]['seen']['recall']:.3f}")
        out["margin"][db] = res
        md.append(f"| {db} | " + " | ".join(row) + " |")

    (src / "summary.json").write_text(json.dumps(out, indent=2, default=str))
    (src / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    main(ap.parse_args().size)
