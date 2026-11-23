"""Episode 2 summary: results/ep02/<size>/*.json|npz -> summary.json and summary.md.

    uv run python -m scripts.ep02_summary --size full

Every number is on the 2,452 test questions; the tuning questions only choose settings.
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from vectors.data import K, Data
from vectors.engines import ENGINES

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [0.80, 0.85, 0.90, 0.95, 0.97, 0.99]
NDCG_SLACK = 0.005   # "within 0.5 points of exact search"
CHECK_N = 200        # questions in the deploy-time recall check
SEED = 7


def recall(ids: np.ndarray, exact: np.ndarray, qs) -> float:
    return float(np.mean([len(set(ids[i]) & set(exact[i, :K])) / K for i in qs]))


def ndcg_hit(ids: np.ndarray, labels: list[set[int]], qs) -> tuple[float, float]:
    disc = 1 / np.log2(np.arange(2, K + 2))
    nd, hit = [], []
    for i in qs:
        rel = labels[i]
        gains = np.array([1.0 if d in rel else 0.0 for d in ids[i, :K]])
        ideal = disc[: min(len(rel), K)].sum()
        nd.append(float((gains * disc).sum() / ideal) if ideal else 0.0)
        hit.append(float(gains.any()))
    return float(np.mean(nd)), float(np.mean(hit))


def lost_counts(ids: np.ndarray, exact: np.ndarray, labels: list[set[int]], qs) -> tuple[int, int]:
    """(questions whose true nearest passage is missing, questions whose answer exact search finds and this doesn't)"""
    near = sum(exact[i, 0] not in set(ids[i, :K]) for i in qs)
    lost = sum(bool(labels[i] & set(exact[i, :K])) and not (labels[i] & set(ids[i, :K])) for i in qs)
    return int(near), int(lost)


def ms(lat: np.ndarray, qs, p: float) -> float:
    return round(float(np.percentile(lat[qs], p)) * 1000, 2)


def main(size: str) -> None:
    d = Data(size)
    src = ROOT / "results" / "ep02" / size
    exact = d.exact
    test, tune = d.test, d.tune
    ex_ndcg, ex_hit = ndcg_hit(exact, d.labels, test)
    ex_ndcg_tune, _ = ndcg_hit(exact, d.labels, tune)
    out: dict = {"size": size, "passages": int(len(d.rows)), "test_questions": int(len(test)),
                 "exact": {"ndcg10": ex_ndcg, "hit10": ex_hit}, "dbs": {}}
    md = [f"# Episode 2 results ({size}: {len(d.rows):,} passages, {len(test):,} test questions)\n",
          f"Exact search (brute force): nDCG@10 {ex_ndcg:.4f}, hit@10 {ex_hit:.4f}.\n"]
    runs = {}
    for name in ENGINES:
        if (src / f"{name}.json").exists():
            runs[name] = (json.loads((src / f"{name}.json").read_text()), np.load(src / f"{name}.npz"))

    # every (db, setting) point: recall and nDCG on tuning questions, for choosing the recall target
    points = []
    for name, (meta, arr) in runs.items():
        for key in [k for k in arr.files if k.endswith("_ids")]:
            points.append((recall(arr[key], exact, tune), ndcg_hit(arr[key], d.labels, tune)[0]))
    target = next((t for t in TARGETS if all(n >= ex_ndcg_tune - NDCG_SLACK for r, n in points if r >= t)),
                  TARGETS[-1])
    out["built_target_recall"] = target

    md.append("## Load and size\n\n| Database | Load (s) | Index wait (s) | Total (min) | Recall just indexed | "
              "Settle (s) | Memory after load (MiB) | after queries | Disk (GB) |\n"
              "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name, (m, arr) in runs.items():
        tot = (m["load_s"] + m["index_wait_s"]) / 60
        md.append(f"| {name} | {m['load_s']:.0f} | {m['index_wait_s']:.0f} | {tot:.1f} | {m['recall_just_indexed']:.3f} | "
                  f"{m['settle_s']:.0f} | {m['mem_after_load_mib']:.0f} | {m['mem_after_queries_mib']:.0f} | "
                  f"{m['disk_bytes'] / 1e9:.2f} |")
    for name, (m, arr) in runs.items():
        hist = (m.get("settle") or {}).get("segment_history")
        if hist:
            md.append(f"\n{name} segments while settling: " + "; ".join(
                f"{h['t_s']} s: {h['segments']} ({', '.join(f'{r:,}' for r in h['rows'])})" for h in hist))
    if "pgvector" in runs:
        st = runs["pgvector"][0]["settings"]
        md.append(f"\npgvector plans: top 1 = {st.get('plan_limit_1')} ({st.get('limit_1_ms')} ms), "
                  f"top 10 = {st.get('plan_limit_10')} ({st.get('limit_10_ms')} ms); TOAST {st.get('toast_bytes', 0) / 1e9:.2f} GB.")

    md.append("\n## Act 1: as shipped (no search parameters)\n\n| Database | Recall@10 | nDCG@10 | hit@10 | "
              "Nearest missed | Answer lost | p50 ms | p99 ms | Throughput (q/s, 16 clients) |\n"
              "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name, (m, arr) in runs.items():
        ids, lat = arr["default_ids"], arr["default_lat"]
        r = recall(ids, exact, test)
        nd, hit = ndcg_hit(ids, d.labels, test)
        near, lost = lost_counts(ids, exact, d.labels, test)
        row = {"recall10": r, "ndcg10": nd, "hit10": hit, "nearest_missed": near, "answer_lost": lost,
               "p50_ms": ms(lat, test, 50), "p95_ms": ms(lat, test, 95),
               "p99_ms": ms(lat, test, 99), "qps": m["qps"]["default"]["qps"]}
        out["dbs"].setdefault(name, {})["default"] = row
        md.append(f"| {name} | {r:.4f} | {nd:.4f} | {hit:.4f} | {near} | {lost} | {row['p50_ms']} | {row['p99_ms']} | "
                  f"{row['qps']} |")
    md.append(f"| exact search | 1.0000 | {ex_ndcg:.4f} | {ex_hit:.4f} | 0 | 0 | | | |")
    md.append("\nNearest missed: test questions whose true nearest passage is not in the top 10. Answer lost: test "
              "questions where exact search's top 10 holds a labeled answer and the database's top 10 holds none.")

    # agreement between databases at their defaults
    names = list(runs)
    if len(names) > 1:
        sets = {n: [set(runs[n][1]["default_ids"][i]) for i in test] for n in names}
        same_all = np.mean([all(sets[n][j] == sets[names[0]][j] for n in names) for j in range(len(test))])
        pair = {f"{a}|{b}": float(np.mean([len(sets[a][j] & sets[b][j]) / K for j in range(len(test))]))
                for a, b in combinations(names, 2)}
        top1 = np.mean([len({runs[n][1]["default_ids"][i][0] for n in names}) == 1 for i in test])
        out["agreement"] = {"same_top10_all": float(same_all), "same_top1_all": float(top1), "pairwise_overlap": pair}
        md.append(f"\nAll {len(names)} databases returned the same top 10 (as a set) for {same_all:.1%} of test questions, "
                  f"and the same top 1 for {top1:.1%}. Lowest pairwise overlap: "
                  f"{min(pair.items(), key=lambda x: x[1])[0]} {min(pair.values()):.1%}.\n")

    md.append("\n## Act 2: the search-time sweep (test questions)\n")
    for name, (m, arr) in runs.items():
        e = ENGINES[name]
        rows = []
        for key in sorted([k for k in arr.files if k.startswith("k") and k.endswith("_ids")],
                          key=lambda k: int(k[1:-4])):
            v = int(key[1:-4])
            ids, lat = arr[key], arr[f"k{v}_lat"]
            nd, hit = ndcg_hit(ids, d.labels, test)
            rows.append({"knob": v, "tune_recall": m["tune_recall"][str(v)], "recall10": recall(ids, exact, test),
                         "ndcg10": nd, "hit10": hit, "p50_ms": ms(lat, test, 50), "p99_ms": ms(lat, test, 99)})
        out["dbs"][name]["sweep"] = rows
        out["dbs"][name]["knob"] = e.knob
        md.append(f"\n**{name}** (`{e.knob}`): " + "; ".join(
            f"{x['knob']}: {x['recall10']:.3f} / {x['p50_ms']} ms" for x in rows))

    md.append("\n\n## Act 2: tuned to the same recall (cheapest sweep value reaching the target on tuning questions)\n")
    md.append("| Database | Target | Setting | Test recall@10 | nDCG@10 | p50 ms | p99 ms | Throughput (q/s) |\n"
              "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for target_label, t in (("r95", 0.95), ("r99", 0.99)):
        for name, (m, arr) in runs.items():
            sw = out["dbs"][name]["sweep"]
            pick = next((x for x in sw if x["tune_recall"] >= t), None)
            q = m["qps"].get(target_label, {})
            out["dbs"][name][target_label] = {**(pick or {}), "qps": q.get("qps")}
            if pick is None:
                best = max(sw, key=lambda x: x["recall10"]) if sw else None
                md.append(f"| {name} | {t} | not reached (best {best['recall10']:.3f} at {best['knob']}) | | | | | |")
            else:
                md.append(f"| {name} | {t} | {pick['knob']} | {pick['recall10']:.4f} | {pick['ndcg10']:.4f} | "
                          f"{pick['p50_ms']} | {pick['p99_ms']} | {q.get('qps', '')} |")

    md.append(f"\n## Act 3: built (target recall {target}: the lowest target at which no tuning point loses more "
              f"than {NDCG_SLACK * 100:.1f} nDCG points against exact search)\n")
    md.append("| Database | Setting | Test recall@10 | Holds target | nDCG@10 | p50 ms | Deploy check at default | "
              "Deploy check at built |\n| :--- | ---: | ---: | :---: | ---: | ---: | :---: | :---: |")
    rng = np.random.default_rng(SEED)
    sample = rng.choice(test, CHECK_N, replace=False)
    for name, (m, arr) in runs.items():
        sw = out["dbs"][name]["sweep"]
        pick = next((x for x in sw if x["tune_recall"] >= target), None)
        chk_default = recall(arr["default_ids"], exact, sample)
        chk_built = recall(arr[f"k{pick['knob']}_ids"], exact, sample) if pick else None
        out["dbs"][name]["built"] = {**(pick or {}), "check_default": chk_default, "check_built": chk_built}
        if pick:
            md.append(f"| {name} | {pick['knob']} | {pick['recall10']:.4f} | {'yes' if pick['recall10'] >= target else 'no'} | "
                      f"{pick['ndcg10']:.4f} | {pick['p50_ms']} | {'pass' if chk_default >= target else 'FAIL'} "
                      f"({chk_default:.3f}) | {'pass' if chk_built >= target else 'FAIL'} ({chk_built:.3f}) |")
        else:
            md.append(f"| {name} | not reachable | | | | | {chk_default:.3f} | |")

    md.append("\n## Read your own write (insert one passage, search for it at once: in the top 10?)\n\n| Database | "
              "Found at once | Found after 1 s | Insert p50 ms | Insert p99 ms |\n| :--- | ---: | ---: | ---: | ---: |")
    for name, (m, arr) in runs.items():
        w = m["write_test"]
        out["dbs"][name]["write_test"] = w
        md.append(f"| {name} | {w['found_immediately']}/{w['passages']} | {w['found_after_1s']}/{w['passages']} | "
                  f"{w['insert_p50_ms']} | {w['insert_p99_ms']} |")
        out["dbs"][name]["load"] = {k: m.get(k) for k in ("load_s", "index_wait_s", "recall_just_indexed", "settle_s",
                                                           "settle", "mem_after_load_mib", "mem_after_queries_mib",
                                                           "disk_bytes", "disk_bytes_end", "startup_s")}
        out["dbs"][name]["settings"] = m["settings"]
        out["dbs"][name]["indexed"] = m["indexed"]
    (src / "summary.json").write_text(json.dumps(out, indent=2, default=str))
    (src / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["pilot", "full"], required=True)
    main(ap.parse_args().size)
