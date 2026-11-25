"""Episode 4 summary: the tables in PLAN section 7, from results/ep04/<size>/ and results/ep04/vectors/.

    uv run python -m scripts.ep04_summary --size full

Writes results/ep04/<size>/summary.md and summary.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from scripts.ep02_summary import lost_counts, ndcg_hit, recall
from scripts.ep04_run import CHECK_N, GRID, LADDER, TUNED, check_questions, sweep_questions
from vectors.compressed import ENGINES
from vectors.data import K, Data

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [0.80, 0.85, 0.90, 0.95, 0.97, 0.99, 0.995]  # 0.995: amendment 1
NDCG_SLACK = 0.005
BUDGETS = {"full": [4, 2, 1], "pilot": [2, 1, 0.5]}  # Act 3: GiB (per million vectors in the full run)
SLOWDOWN, SLACK_MS = 2.0, 5.0  # "fits": p50 within 2x, or within 5 ms, of the same setting's p50 at 16 GiB (amendment 3)


def fast_enough(p50: float, base: float) -> bool:
    return p50 <= max(SLOWDOWN * base, base + SLACK_MS)


def load(size: str) -> dict:
    out = {}
    for db, E in ENGINES.items():
        for dep in E.deployments:
            stem = ROOT / "results" / "ep04" / size / f"{db}__{dep}"
            if Path(f"{stem}.json").exists():
                res = json.loads(Path(f"{stem}.json").read_text())
                if "finished" in res:
                    if "tuned" not in res:  # pilot files written before amendment 1: one tuned level
                        c = res.get("ladder", {}).get("tuned_c")
                        res["tuned"] = {"tuned": {"c": c, "level": 0.995,
                                                  "reached": res.get("tuned_rule", "").startswith("smallest")}}
                    out[(db, dep)] = (res, dict(np.load(f"{stem}.npz")))
    return out


def cell_metrics(ids, lat, data: Data, qs) -> dict:
    ran = qs[~np.isnan(lat[qs])]
    if not len(ran):
        return {"n": 0}
    nd, hit = ndcg_hit(ids, data.labels, ran)
    near, lost = lost_counts(ids, data.exact, data.labels, ran)
    return {"n": int(len(ran)), "recall": recall(ids, data.exact, ran), "ndcg": nd, "hit": hit, "lost": lost,
            "nearest_missed": near, "p50_ms": float(np.median(lat[ran]) * 1000),
            "p95_ms": float(np.percentile(lat[ran], 95) * 1000)}


def main(size: str, force_target: float | None = None) -> None:
    data = Data(size)
    runs = load(size)
    test, tune = data.test, data.tune
    sweep_test = np.setdiff1d(sweep_questions(data), tune)
    chk = check_questions(data)
    exact_tune = ndcg_hit(data.exact[:, :K], data.labels, tune)[0]
    exact_test = ndcg_hit(data.exact[:, :K], data.labels, test)
    md, js = [f"# Episode 4 summary ({size}: {len(data.rows):,} passages)\n"], {"deployments": {}}
    md.append(f"Exact float32 search, test questions: nDCG@10 {exact_test[0]:.3f}, hit@10 {exact_test[1]:.3f}.\n")

    # ---- settings read back
    md.append("## Settings read back\n")
    for (db, dep), (res, _) in runs.items():
        md.append(f"- **{db} / {dep}** ({res['what']}): `{json.dumps(res['settings'], default=str)[:600]}`")
    md.append("")

    # ---- Act 1: as shipped
    md.append("## Act 1: compression as shipped (no search parameters, all test questions)\n")
    md.append("| Database | Deployment | Recall | nDCG | Answers lost | Nearest missed | p50 ms | p95 ms | Disk GiB | "
              "Mem after load MiB | Ready min | Fits (GiB, shipped) |")
    md.append("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |")
    for (db, dep), (res, arr) in runs.items():
        m = cell_metrics(arr["shipped_ids"], arr["shipped_lat"], data, test)
        fits = fits_list(res, arr, "shipped", chk)
        ready = (res["load_s"] + res["index_wait_s"] + res["settle_s"]) / 60
        js["deployments"][f"{db}/{dep}"] = {"shipped": m, "fits_shipped": fits, "disk_bytes": res["disk_bytes"],
                                            "mem_mib_after_load": res["mem_mib_after_load"],
                                            "mem_mib_after_queries": res.get("mem_mib_after_queries"),
                                            "ready_min": ready, "tuned": res["tuned"]}
        md.append(f"| {db} | {dep} | {m['recall']:.3f} | {m['ndcg']:.3f} | {m['lost']} | {m['nearest_missed']} | "
                  f"{m['p50_ms']:.1f} | {m['p95_ms']:.1f} | {res['disk_bytes'] / 2**30:.2f} | "
                  f"{res['mem_mib_after_load']:.0f} | {ready:.1f} | {fmt_fits(fits)} |")
    md.append("")

    # ---- Act 2: re-scoring depth
    md.append(f"## Act 2: re-scoring depth (c candidates; recall on the {len(sweep_test):,} seeded test questions, "
              "p50 ms)\n")
    md.append("| Database | Deployment | shipped | " + " | ".join(f"c={c}" for c in GRID) +
              " | smallest c ≥ 0.95 / 0.99 / 0.995 / 0.9975 (tuning) |")
    md.append("| :--- | :--- | " + " | ".join(["---:"] * (len(GRID) + 1)) + " | :--- |")
    for (db, dep), (res, arr) in runs.items():
        row = []
        for cell in ["shipped"] + [f"c{c}" for c in GRID]:
            m = cell_metrics(arr[f"{cell}_ids"], arr[f"{cell}_lat"], data, sweep_test)
            js["deployments"][f"{db}/{dep}"].setdefault("sweep", {})[cell] = m
            s = "" if not res["cells"][cell]["sampled"] else "*"
            row.append(f"{m['recall']:.3f} / {m['p50_ms']:.1f}{s}" if m["n"] else "—")
        need = []
        for thr in (0.95, 0.99, *TUNED.values()):
            ok = [c for c in GRID if not res["cells"][f"c{c}"]["sampled"] and
                  (res["cells"][f"c{c}"]["tune_recall"] or 0) >= thr]
            need.append(str(min(ok)) if ok else "—")
        md.append(f"| {db} | {dep} | " + " | ".join(row) + f" | {' / '.join(need)} |")
    md.append("\n(* sampled: stopped by the speed guard)\n")

    # ---- the memory ladder
    md.append(f"## The memory ladder ({CHECK_N} test questions per step; p50 ms / recall; ✓ fits = runs, answers "
              f"all, p50 within {SLOWDOWN:g}× or {SLACK_MS:g} ms of its 16 GiB p50)\n")
    lad = LADDER[size]
    md.append("| Database | Deployment | Setting | 16 GiB | " + " | ".join(f"{g} GiB" for g in lad) + " |")
    md.append("| :--- | :--- | :--- | ---: | " + " | ".join(["---:"] * len(lad)) + " |")
    for (db, dep), (res, arr) in runs.items():
        for label in ["shipped"] + list(TUNED):
            c = setting_c(res, label)
            if label != "shipped" and (c is None or step_label(res, label) != label):
                continue  # not measured, or the same c as an earlier row
            base = base_p50(res, arr, label, chk)
            if base is None:
                continue
            cells = [fmt_step(res.get("ladder", {}).get("steps", {}).get(str(g), {}).get(label), base) for g in lad]
            reached = "" if label == "shipped" or res["tuned"][label]["reached"] else ", never reaches its level"
            md.append(f"| {db} | {dep} | {label}{f' (c={c}{reached})' if c else ''} | {base:.1f} | " +
                      " | ".join(cells) + " |")
    md.append("")

    # ---- Act 3: target from labels
    md.append("## Act 3: the recall target from the labels (tuning questions, every deployment and setting)\n")
    md.append("| Target | Settings reaching it | Worst nDCG loss (points) | Within 0.5? |")
    md.append("| ---: | ---: | ---: | :--- |")
    points = []
    for (db, dep), (res, arr) in runs.items():
        for cell in ["shipped"] + [f"c{c}" for c in GRID]:
            if res["cells"][cell]["sampled"]:
                continue
            ids = arr[f"{cell}_ids"]
            points.append((recall(ids, data.exact, tune), ndcg_hit(ids, data.labels, tune)[0], f"{db}/{dep}/{cell}"))
    target, ttable = None, []
    for t in TARGETS:
        reach = [exact_tune - n for r, n, _ in points if r >= t]
        worst = max(reach) if reach else None
        ok = worst is not None and worst <= NDCG_SLACK
        ttable.append({"target": t, "settings": len(reach), "worst_loss": worst, "ok": ok})
        if ok and target is None:
            target = t
        md.append(f"| {t:g} | {len(reach)} | {worst * 100 if worst is not None else float('nan'):.2f} | "
                  f"{'yes' if ok else 'no'} |")
    if force_target is not None:  # for checking the code path only; never in the reported summary
        target = force_target
        md.append(f"\n**Target forced to {target} (code check, not a result).**\n")
    elif target is None:  # amendment 1: no level qualifies -> the highest, said so
        target = TARGETS[-1]
        md.append(f"\nNo level keeps every setting within 0.5 points; target: the highest, **{target}**.\n")
    else:
        md.append(f"\nTarget: **{target}**.\n")
    label_for = "tuned_hi" if target >= 0.995 else "tuned"
    if force_target is not None and size == "pilot" and label_for not in TUNED:
        label_for = "tuned"
    md.append(f"Act 3 checks the `{label_for}` setting (tuned to {TUNED[label_for]} on tuning questions).\n")
    js["target_table"], js["target"] = ttable, target

    # ---- Act 3: built, per database and budget
    md.append(f"## Act 3: built: per database and memory budget, the fastest deployment whose tuned setting passes "
              f"the deploy check under that limit (recall ≥ {target}, all answered, p50 within {SLOWDOWN:g}× or {SLACK_MS:g} ms of its 16 GiB "
              f"p50; {CHECK_N} test questions)\n")
    md.append("| Database | Budget GiB | Deployment (c) | Check recall | Check p50 ms | Recall (1,000 test) | nDCG | "
              "Answers lost | Others that pass |")
    md.append("| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |")
    built = {}
    for db in ENGINES:
        for g in BUDGETS[size]:
            passing = []
            for (d2, dep), (res, arr) in runs.items():
                if d2 != db or "ladder" not in res:
                    continue
                if not res["tuned"].get(label_for, {}).get("reached"):
                    continue
                st = res["ladder"]["steps"].get(str(g), {}).get(step_label(res, label_for))
                base = base_p50(res, arr, label_for, chk)
                if st and st.get("ok") and base and fast_enough(st["p50_ms"], base) and st["ran"] == CHECK_N \
                        and (st["recall"] or 0) >= (target or 1):
                    passing.append((st["p50_ms"], dep, res, arr, st))
            if not passing:
                md.append(f"| {db} | {g} | none passes | | | | | | |")
                built[f"{db}/{g}"] = None
                continue
            passing.sort(key=lambda x: x[0])
            p50, dep, res, arr, st = passing[0]
            c = setting_c(res, label_for)
            m = cell_metrics(arr[f"c{c}_ids"], arr[f"c{c}_lat"], data, sweep_test)
            built[f"{db}/{g}"] = {"deployment": dep, "c": c, "check": st, "test": m,
                                  "others": [x[1] for x in passing[1:]]}
            md.append(f"| {db} | {g} | {dep} ({c}) | {st['recall']:.3f} | {p50:.1f} | {m['recall']:.3f} | "
                      f"{m['ndcg']:.3f} | {m['lost']} | {', '.join(x[1] for x in passing[1:]) or '—'} |")
    js["built"] = built
    md.append("")

    # Exploratory, decided after seeing the results (not part of the fixed design): at 0.99 one setting of ~150 lost
    # 0.53 points (rule: 0.5), which pushed the target to 0.995. The same check at 0.99, over every setting the ladder
    # measured (shipped, and the tuned c's, mostly the deepest c=500), ignoring whether tuning reached a level.
    if force_target is None:
        alt = 0.99
        md.append(f"\n**Exploratory, after the results: the same check at a {alt} target**, any setting the ladder "
                  f"measured (as shipped or the tuned c), check recall ≥ {alt}, all answered, the same speed rule. "
                  "p50 in ms at that limit; slower or failing settings are left out.\n")
        md.append("| Database | " + " | ".join(f"{g} GiB" for g in [8] + BUDGETS[size]) + " |")
        md.append("| :--- | " + " | ".join([":---"] * (1 + len(BUDGETS[size]))) + " |")
        js["exploratory_099"] = {}
        for db in ENGINES:
            row = []
            for g in [8] + BUDGETS[size]:
                ok = []
                for (d2, dep), (res, arr) in runs.items():
                    if d2 != db or "ladder" not in res:
                        continue
                    for label in ["shipped"] + list(TUNED):
                        if label != "shipped" and step_label(res, label) != label:
                            continue
                        st = res["ladder"]["steps"].get(str(g), {}).get(label)
                        base = base_p50(res, arr, label, chk)
                        if st and st.get("ok") and base and fast_enough(st["p50_ms"], base) \
                                and st["ran"] == CHECK_N and (st["recall"] or 0) >= alt:
                            ok.append((st["p50_ms"], dep, setting_c(res, label), st["recall"]))
                ok.sort()
                js["exploratory_099"][f"{db}/{g}"] = ok
                row.append(", ".join(f"{d} c={c} {p:.1f} ({r:.3f})" for p, d, c, r in ok) or "—")
            md.append(f"| {db} | " + " | ".join(row) + " |")
        md.append("")

    # ---- the vectors alone
    for part in ("million", "subset"):
        p = ROOT / "results" / "ep04" / "vectors" / f"{part}.json"
        if p.exists():
            md += vectors_tables(part, json.loads(p.read_text()))
            js[f"vectors_{part}"] = json.loads(p.read_text())

    out = ROOT / "results" / "ep04" / size
    (out / "summary.md").write_text("\n".join(md) + "\n")
    (out / "summary.json").write_text(json.dumps(js, indent=2, default=float))
    print("\n".join(md))


def setting_c(res, label) -> int | None:
    return None if label == "shipped" else res["tuned"].get(label, {}).get("c")


def step_label(res, label) -> str:
    """The ladder measures each c once: a tuned level whose c equals an earlier one's is stored under that label."""
    if label == "shipped":
        return label
    c = setting_c(res, label)
    for lab in TUNED:
        if setting_c(res, lab) == c:
            return lab
    return label


def base_p50(res, arr, label, chk) -> float | None:
    """p50 at 16 GiB over the check questions, same setting (the as-shipped cell ran every question; the tuned c's
    cell ran the sweep sample, which contains the check sample)."""
    if label == "shipped":
        cell = "shipped"
    else:
        c = setting_c(res, label)
        if c is None:
            return None
        cell = f"c{c}"
    lat = arr[f"{cell}_lat"][chk]
    return float(np.nanmedian(lat) * 1000) if (~np.isnan(lat)).any() else None


def fits_list(res, arr, label, chk) -> list:
    base = base_p50(res, arr, label, chk)
    out = []
    for g, step in res.get("ladder", {}).get("steps", {}).items():
        st = step.get(label)
        if st and st.get("ok") and base and fast_enough(st["p50_ms"], base) and st["ran"] == CHECK_N:
            out.append(float(g))
    return out


def fmt_fits(fits: list) -> str:
    return f"≥ {min(fits):g}" if fits else "none of the ladder"


def fmt_step(st, base) -> str:
    if not st:
        return "·"
    if not st.get("ok"):
        why = "OOM" if st.get("oom_killed") else ("slow" if st.get("sampled") else (st.get("why") or "failed"))
        p = f" {st['p50_ms']:.0f}" if st.get("p50_ms") else ""
        return f"✗ {why}{p}"
    mark = "✓" if fast_enough(st["p50_ms"], base) and st["ran"] == CHECK_N else "slow"
    return f"{mark} {st['p50_ms']:.1f} / {st['recall']:.3f}"


def vectors_tables(part: str, v: dict) -> list[str]:
    md = []
    if part == "million":
        md.append("## The vectors alone: Cohere v3, the million, exact search over each representation "
                  "(test questions)\n")
        md.append("| Representation | Bytes/vector | Recall (own top 10) | nDCG | Answers lost | Re-scored c=20 | "
                  "c=50 | c=100 (recall / lost) |")
        md.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for r, x in v.items():
            res = [f"{x[c]['recall']:.3f} / {x[c]['lost']}" if c in x else "" for c in ("c20", "c50", "c100")]
            md.append(f"| {r} | {x['bytes']} | {x['c10']['recall']:.3f} | {x['c10']['ndcg']:.3f} | "
                      f"{x['c10']['lost']} | " + " | ".join(res) + " |")
    else:
        md.append("## The vectors alone: Matryoshka on the 100,000 subset (test questions; each model against its "
                  "own exact search)\n")
        md.append("| Model | Dims | Precision | Bytes | Recall | nDCG | Answers lost | Re-scored c=50 | c=100 "
                  "(recall / nDCG) |")
        md.append("| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for m, reps in v.items():
            for x in reps.values():
                res = [f"{x[c]['recall']:.3f} / {x[c]['ndcg']:.3f}" for c in ("c50", "c100")]
                md.append(f"| {m} | {x['dims']} | {x['precision']} | {x['bytes']} | {x['c10']['recall']:.3f} | "
                          f"{x['c10']['ndcg']:.3f} | {x['c10']['lost']} | " + " | ".join(res) + " |")
    md.append("")
    return md


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    ap.add_argument("--force-target", type=float, default=None, help="code check only")
    a = ap.parse_args()
    main(a.size, a.force_target)
