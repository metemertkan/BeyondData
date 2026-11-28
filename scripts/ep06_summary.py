"""Episode 6: tables from the replay, the answers, the real-time check and the six databases.

    uv run python -m scripts.ep06_summary --size pilot

Writes results/ep06/<size>/summary.{md,json}.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from sync import kb, score
from sync.answer import scored
from sync.designs import ORDER

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"once": "once (as shipped)", "rerun": "rerun nightly (as shipped)", "rebuild": "rebuild nightly",
         "upsert": "upsert nightly", "record_manager": "record manager", "poll": "poll updated_at",
         "cdc": "CDC", "same_db": "same database", "built": "built", "rebuild_check": "rebuild + check (expl.)",
         "cdc_outage": "CDC, worker down 12 h (expl.)", "built_outage": "built, worker down 12 h (expl.)"}
STALE_CLASSES = ("outdated", "deleted")
TARGET_NORMAL_S, TARGET_MIGRATION_S = 300, 1800


def pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    return None if not xs else xs[min(len(xs) - 1, int(p * len(xs)))]


def fmt_s(s):
    if s is None:
        return "—"
    if s < 90:
        return f"{s:.0f} s"
    if s < 5400:
        return f"{s / 60:.0f} min"
    if s < 172800:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.1f} d"


def from_index(row: dict, q: dict) -> bool:
    """A stale (or both) reply whose old value was in an outdated or deleted chunk of its context."""
    if row["score"] not in ("stale", "both"):
        return False
    for c in row["chunks"]:
        if c["class"] in STALE_CLASSES and any(score.pattern(q["fact_kind"], s).search(c["text"]) for s in q["stale"]):
            return True
    return False


def design_summary(size: str, d: str, rows: list[dict], qs: dict) -> dict:
    out = ROOT / "results" / "ep06" / size
    r = json.loads((out / f"{d}.json").read_text())
    audits = r["audits"]
    bad = lambda a: a.get("outdated", 0) + a.get("deleted", 0) + a.get("duplicate", 0)  # noqa: E731
    from datetime import datetime
    end = datetime.fromisoformat(kb.load(size)["meta"]["end"]).timestamp()
    last_day = [s for s in r["sync"] if s["t"] > end - 86400]          # may simply not have had its night yet
    sync = [s for s in r["sync"] if s["t"] <= end - 86400]
    mig = [s for s in sync if s["why"] == "migration"]
    normal = [s for s in sync if s["why"] != "migration"]
    never_current = sum(1 for s in sync if s["current_s"] is None)
    never_clean = sum(1 for s in sync if s["clean_s"] is None)
    res = {"design": d, "label": LABEL[d], "act": r["act"],
           "initial_chunks": r["initial"]["chunks_embedded"],
           "month_chunks_embedded": r["month"]["chunks_embedded"], "month_embed_cpu_s": r["month"]["embed_cpu_s"],
           "final": r["final"], "worst_day_bad": max((bad(a) for a in audits), default=0),
           "worst_day_bad_share": round(max((bad(a) / max(1, a["entries"]) for a in audits), default=0), 3),
           "changes": len(sync), "never_current": never_current, "never_clean": never_clean,
           "last_day_changes": len(last_day), "last_day_not_current": sum(1 for s in last_day if s["current_s"] is None),
           "current_p50_s": pct([s["current_s"] for s in normal], 0.5),
           "current_p95_s": pct([s["current_s"] for s in normal], 0.95),
           "current_max_s": pct([s["current_s"] for s in normal], 1.0),
           "migration_current_max_s": pct([s["current_s"] for s in mig], 1.0),
           "migration_never": sum(1 for s in mig if s["current_s"] is None),
           "notes": r.get("notes", {})}
    # questions
    n = len(rows)
    ctx_bad = sum(1 for x in rows if any(c["class"] in STALE_CLASSES for c in x["chunks"]))
    ctx_dup = sum(1 for x in rows if any(c["class"] == "duplicate" for c in x["chunks"]))
    short = sum(1 for x in rows if len(x["chunks"]) < 4)
    res |= {"questions": n, "context_outdated_or_deleted": ctx_bad, "context_duplicate": ctx_dup,
            "context_short": short, "dropped_chunks": sum(len(x["dropped"]) for x in rows)}
    if rows and rows[0]["score"] is not None:
        res["answers"] = dict(Counter(x["score"] for x in rows))
        res["answers_by_kind"] = {k: dict(Counter(x["score"] for x in rows if x["kind"] == k))
                                  for k in ("changed", "unchanged", "deleted", "new")}
        res["stale_from_index"] = sum(from_index(x, qs[x["qid"]]) for x in rows)
        res["by_delay"] = {}
        for label, _ in kb.DELAYS:
            sub = [x for x in rows if x["kind"] == "changed" and x["delay"] == label]
            if sub:
                res["by_delay"][label] = {"n": len(sub), "current": sum(x["score"] == "current" for x in sub),
                                          "stale": sum(x["score"] in ("stale", "both") for x in sub)}
    # the target (Act 3)
    res["target"] = {"no_stale_context": ctx_bad == 0,
                     "fresh_normal": (res["current_max_s"] or 0) <= TARGET_NORMAL_S and
                     sum(1 for s in normal if s["current_s"] is None) == 0,
                     "fresh_migration": res["migration_never"] == 0 and (res["migration_current_max_s"] or 0) <= TARGET_MIGRATION_S,
                     "agrees_at_audits": all(bad(a) + a.get("missing", 0) == 0 or a.get("queue", 0) > 0 for a in audits)}
    res["target"]["passes"] = all(res["target"].values())
    return res


def realtime(size: str) -> dict:
    out = ROOT / "results" / "ep06" / size
    res = {}
    for d in ("poll", "cdc", "same_db", "built"):
        p = out / f"realtime_{d}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        b0 = r.get("burst_at", 300)
        steady = [x["lag_s"] for x in r["lags"] if not (b0 <= x["t"] < b0 + 600)]
        burst = [x["lag_s"] for x in r["lags"] if b0 <= x["t"] < b0 + 600]
        res[d] = {"saves": r["saves"], "synced": r["synced"], "never": r["never"],
                  "steady_p50_s": pct(steady, 0.5), "steady_max_s": pct(steady, 1.0),
                  "burst_p50_s": pct(burst, 0.5), "burst_max_s": pct(burst, 1.0),
                  "save_p50_s": pct([x["save_s"] for x in r["save_times"] if not x["burst"]], 0.5),
                  "save_burst_total_s": round(sum(x["save_s"] for x in r["save_times"] if x["burst"]), 1),
                  "computed": r["computed"], "compute_s": r["compute_s"]}
    return res


def stores(size: str) -> dict:
    out = ROOT / "results" / "ep06" / size / "stores"
    res = {}
    for p in sorted(out.glob("*.json")) if out.exists() else []:
        r = json.loads(p.read_text())
        vis = r["update_visibility"]
        gone = r["delete_visibility"]
        res[r["db"]] = {"add_again": r["add_again"], "upsert_call": r["upsert_call"],
                        "update_new_at_once": sum(1 for v in vis if v["new_s"] is not None and v["new_s"] < 0.001),
                        "update_new_max_s": pct([v["new_s"] for v in vis], 1.0),
                        "update_old_at_once_gone": sum(1 for v in vis if v["old_gone_s"] is not None and v["old_gone_s"] < 0.001),
                        "update_old_gone_max_s": pct([v["old_gone_s"] for v in vis], 1.0),
                        "delete_at_once": sum(1 for g in gone if g["gone_s"] is not None and g["gone_s"] < 0.001),
                        "delete_max_s": pct([g["gone_s"] for g in gone], 1.0),
                        "delete_never": sum(1 for g in gone if g["gone_s"] is None), "n_vis": len(vis),
                        "fresh": r["fresh"], "churn": r["churn"], "maintain": r["maintain"],
                        "after_cleanup": r["after_cleanup"]}
    return res


def both_in_context(rows: dict[str, list[dict]], qs: dict) -> dict:
    """Exploratory (after results): replies whose context held the new value and the old one.

    Changed facts with distinct values (not plan names or statuses), the new value in a current or duplicate
    chunk and the old value in an outdated or deleted chunk of the same context. Counted once per distinct
    prompt (question and chunks) across all designs.
    """
    seen = {}
    for d in ORDER:
        for r in rows.get(d, []):
            q = qs[r["qid"]]
            if q["kind"] != "changed" or q["fact_kind"] in ("name", "status") or r["score"] is None:
                continue
            key = (r["qid"], tuple(c["text"] for c in r["chunks"]))
            if key in seen:
                continue
            new = [i for i, c in enumerate(r["chunks"])
                   if c["class"] in ("current", "duplicate") and score.mentions(q, c["text"])[0]]
            old = [i for i, c in enumerate(r["chunks"])
                   if c["class"] in STALE_CLASSES and score.mentions(q, c["text"])[1]]
            if new and old:
                notes = all(r["chunks"][i]["text"].startswith("Release notes") for i in new)
                seen[key] = {"score": r["score"], "new_first": new[0] < old[0], "notes": notes}
    v = list(seen.values())
    c = Counter(x["score"] for x in v)
    return {"prompts": len(v), "old": c["stale"], "new": c["current"], "both": c["both"],
            "other": len(v) - c["stale"] - c["current"] - c["both"],
            "new_ranked_first": sum(x["new_first"] for x in v),
            "new_only_in_release_notes": sum(x["notes"] for x in v),
            "new_only_in_release_notes_stale": sum(x["notes"] and x["score"] == "stale" for x in v)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    a = ap.parse_args()
    out = ROOT / "results" / "ep06" / a.size
    designs = [d for d in ORDER if (out / f"{d}.json").exists()]
    qs = {q["qid"]: q for q in kb.load(a.size)["questions"]}
    rows = scored(a.size, designs)
    S = {"designs": [design_summary(a.size, d, rows.get(d, []), qs) for d in designs],
         "realtime": realtime(a.size), "stores": stores(a.size),
         "exploratory": {"both_in_context": both_in_context(rows, qs)}}
    (out / "summary.json").write_text(json.dumps(S, indent=1, default=str))

    L = [f"# Episode 6 summary ({a.size})", "",
         "## The month, per design (questions: retrieval; answers: qwen3:8b)", "",
         "| Design | index at the end: entries / outdated / deleted / duplicate / missing | questions with an outdated or "
         "deleted chunk | answers current / stale / both / declined / other | stale from the index | chunks embedded "
         "in the month |",
         "| :--- | :--- | ---: | :--- | ---: | ---: |"]
    for s in S["designs"]:
        f = s["final"]
        ans = s.get("answers", {})
        L.append(f"| {s['label']} | {f.get('entries', 0):,} / {f.get('outdated', 0)} / {f.get('deleted', 0)} / "
                 f"{f.get('duplicate', 0)} / {f.get('missing', 0)} | {s['context_outdated_or_deleted']} of "
                 f"{s['questions']} | {ans.get('current', 0)} / {ans.get('stale', 0)} / {ans.get('both', 0)} / "
                 f"{ans.get('declined', 0) + ans.get('missing', 0)} / {ans.get('other', 0)} | "
                 f"{s.get('stale_from_index', '—')} | {s['month_chunks_embedded']:,} |")
    L += ["", "## How long a change took to reach the index (replay clock; changes in the month's last 24 h left out)", "",
          "| Design | changes | current: p50 / p95 / max (normal) | migration: max / never | never current | never clean |",
          "| :--- | ---: | :--- | :--- | ---: | ---: |"]
    for s in S["designs"]:
        L.append(f"| {s['label']} | {s['changes']} | {fmt_s(s['current_p50_s'])} / {fmt_s(s['current_p95_s'])} / "
                 f"{fmt_s(s['current_max_s'])} | {fmt_s(s['migration_current_max_s'])} / {s['migration_never']} | "
                 f"{s['never_current']} | {s['never_clean']} |")
    L += ["", "## Changed facts: current answers by time since the change", "",
          "| Design | " + " | ".join(l for l, _ in kb.DELAYS) + " |", "| :--- |" + " ---: |" * len(kb.DELAYS)]
    for s in S["designs"]:
        bd = s.get("by_delay", {})
        L.append(f"| {s['label']} | " + " | ".join(
            f"{bd[l]['current']}/{bd[l]['n']}" if l in bd else "—" for l, _ in kb.DELAYS) + " |")
    L += ["", "## The target (Act 3)", "", "| Design | no stale context | fresh (normal) | fresh (migration) | "
          "agrees at audits | passes |", "| :--- | :---: | :---: | :---: | :---: | :---: |"]
    for s in S["designs"]:
        t = s["target"]
        yn = lambda b: "yes" if b else "no"  # noqa: E731
        L.append(f"| {s['label']} | {yn(t['no_stale_context'])} | {yn(t['fresh_normal'])} | "
                 f"{yn(t['fresh_migration'])} | {yn(t['agrees_at_audits'])} | **{yn(t['passes'])}** |")
    if S["realtime"]:
        L += ["", "## Real time (writer: an edit every 10 s, a 300-article burst at minute 7)", "",
              "| Design | saves | synced | never | steady p50 / max | burst p50 / max | save p50 | burst saves total |",
              "| :--- | ---: | ---: | ---: | :--- | :--- | :--- | :--- |"]
        for d, r in S["realtime"].items():
            L.append(f"| {LABEL[d]} | {r['saves']} | {r['synced']} | {r['never']} | {fmt_s(r['steady_p50_s'])} / "
                     f"{fmt_s(r['steady_max_s'])} | {fmt_s(r['burst_p50_s'])} / {fmt_s(r['burst_max_s'])} | "
                     f"{r['save_p50_s']} s | {r['save_burst_total_s']} s |")
    if S["stores"]:
        L += ["", "## The six databases", "",
              "| Database | add again: error / count after / found by new / by old (of 200) | update: new at once, old "
              "gone at once (of 200) | delete gone at once (of 200), max | recall fresh → rounds → after clean-up | "
              "p50 ms fresh → round 3 → after |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
        for db, r in S["stores"].items():
            aa = r["add_again"]
            rec = " → ".join(str(x["recall"]) for x in [r["fresh"], *r["churn"], r["after_cleanup"]])
            lat = f"{r['fresh']['p50_ms']} → {r['churn'][-1]['p50_ms']} → {r['after_cleanup']['p50_ms']}"
            L.append(f"| {db} | {'error' if aa['error'] else 'ok'} / {aa['count_after']:,} / {aa['found_by_new']} / "
                     f"{aa['found_by_old']} | {r['update_new_at_once']}, {r['update_old_at_once_gone']} | "
                     f"{r['delete_at_once']}, {fmt_s(r['delete_max_s'])} | {rec} | {lat} |")
    b = S["exploratory"]["both_in_context"]
    L += ["", "## Exploratory: the new value and the old one both in the context", "",
          f"Distinct prompts (changed facts with distinct values; new value in a current chunk, old value in an "
          f"outdated or deleted one): {b['prompts']}. Replies: old {b['old']}, new {b['new']}, both {b['both']}, "
          f"other {b['other']}. New value ranked above the old one: {b['new_ranked_first']}. New value only in a "
          f"release note: {b['new_only_in_release_notes']} ({b['new_only_in_release_notes_stale']} of them stale)."]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
