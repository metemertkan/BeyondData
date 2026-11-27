"""Episode 5: the questions, in four places your data can be when a model answers.

    uv run python -m quant.tasks --prepare      # -> data/ep05/tasks.json

closed  What the model knows: Episode 2's Natural Questions with the short answers from NQ-open
        (google-research-datasets/nq_open, validation: the NQ dev questions with answers of five tokens
        or fewer). No passages. 2,255 of Episode 2's 3,452 questions have one (660 tuning, 1,595 test).
rag     What it reads: the same question with the 3 nearest passages from exact search over Episode 2's
        million (Cohere embed-english-v3). Episode 2's retrieval, so the passages are what a good vector
        database returns.
abstain Whether it sticks to your data: the same question with the 3 nearest passages that contain none of
        its answer strings and are not labeled relevant. The right reply is "not in the passages".
records What it copies: Acme Cloud's invoices from Episode 1 (ledger/world.py, seed 7) as a plain export in
        the prompt, and lookups of one field. S: 80 invoices (3,400 tokens: fits Ollama's default 4,096-token
        context); L: 320 invoices (about 13,000 tokens, run with a 16,384-token context). All 680 are 28,000
        tokens, which takes 20 minutes to read once on this CPU at 4 bits. Four kinds: amount, issue date,
        email by invoice number, and the invoice number by customer and date (only where that pair is unique).

Questions are drawn once with seed 7. The pilot uses Episode 2's tuning questions and a tuning window of
invoices only; the full run uses test questions and a test window, first seen there. Nothing is tuned on
the full run's questions: Act 3's choice is a rule fixed in advance, checked on them. For records, S has a
tuning window and a test window, and L asks pilot and full-run questions about different rows of one export.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "ep05"
NQ_OPEN = DIR / "raw" / "nq_open_validation.parquet"
SEED = 7
K_PASSAGES = 3
SIZES = {"pilot": {"tune": 60, "test": 0, "abstain": 30, "records_per_kind": {"S": 3, "L": 3}, "split": "tune"},
         "full": {"tune": 0, "test": 250, "abstain": 100, "records_per_kind": {"S": 10, "L": 15}, "split": "test"}}
RECORD_KINDS = ("amount", "date", "email", "number")
S_ROWS = 80
L_ROWS = 320


def normalize(s: str) -> str:
    """SQuAD-style: lowercase, drop punctuation and articles, squeeze spaces."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def contains(text: str, answer: str) -> bool:
    """The normalized answer appears in the normalized text as whole tokens ("4" is not in "category 14")."""
    a = normalize(answer)
    return bool(a) and f" {a} " in f" {normalize(text)} "


def _key(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def nq_items() -> dict:
    """Every Episode 2 question with an NQ-open answer, its split, its RAG passages and its answer-free ones."""
    import pyarrow.parquet as pq
    from vectors.data import Data, RAW
    d = Data("full")
    answers = {_key(r["question"]): r["answer"] for r in pq.read_table(NQ_OPEN).to_pylist()}
    qtext = {r["_id"]: r["text"] for r in pq.read_table(RAW / "queries" / "test.parquet").select(["_id", "text"]).to_pylist()}
    p = pq.read_table(ROOT / "data" / "ep02" / "passages.parquet", columns=["title", "text"])
    titles, texts = p.column("title").to_pylist(), p.column("text").to_pylist()
    tune = set(d.meta["tune"])
    out = {}
    for i, qid in enumerate(d.meta["query_ids"]):
        a = answers.get(_key(qtext[qid]))
        if not a:
            continue
        has = lambda r: any(contains(titles[r] + " " + texts[r], x) for x in a)
        rag = [int(r) for r in d.exact[i][:K_PASSAGES]]
        free = [int(r) for r in d.exact[i] if int(r) not in d.labels[i] and not has(int(r))][:K_PASSAGES]
        out[i] = {"q": i, "question": qtext[qid], "answers": a, "split": "tune" if i in tune else "test",
                  "rag": [{"title": titles[r], "text": texts[r]} for r in rag],
                  "answer_in_passages": any(has(r) for r in rag),
                  "abstain": [{"title": titles[r], "text": texts[r]} for r in free] if len(free) == K_PASSAGES else None}
    return out


def record_rows() -> list[dict]:
    from ledger.world import build
    w = build()
    cust = {c.id: c for c in w.customers}
    rows = []
    for inv in sorted(w.invoices, key=lambda i: i.number):
        c = cust[inv.customer_id]
        rows.append({"number": inv.number, "date": inv.issued_at.date().isoformat(), "customer": c.name,
                     "email": c.email, "currency": inv.currency, "amount": f"{inv.amount_cents / 100:.2f}",
                     "status": inv.status})
    return rows


def render_records(rows: list[dict]) -> str:
    head = "number | issued | customer | email | amount | status"
    return "\n".join([head] + [f"{r['number']} | {r['date']} | {r['customer']} | {r['email']} | "
                               f"{r['currency']} {r['amount']} | {r['status']}" for r in rows])


def record_question(kind: str, r: dict) -> tuple[str, str]:
    if kind == "amount":
        return f"What is the amount of invoice {r['number']}?", r["amount"]
    if kind == "date":
        return f"On what date was invoice {r['number']} issued?", r["date"]
    if kind == "email":
        return f"What is the customer's email address on invoice {r['number']}?", r["email"]
    # amendment 2: "Which invoice was issued to ...?" got the invoice's amount back (the value, as asked)
    return f"What is the number of the invoice issued to {r['customer']} on {r['date']}?", r["number"]


def records_items(per_kind: dict, split: str, rng: random.Random) -> tuple[list[dict], dict]:
    rows = record_rows()
    window = {"tune": rows[100:100 + S_ROWS], "test": rows[400:400 + S_ROWS]}[split]
    contexts = {f"S-{split}": window, "L": rows[:L_ROWS]}
    # L's rows are split by position parity, so pilot and full-run questions never ask about the same invoice
    l_pool = [r for i, r in enumerate(rows[:L_ROWS]) if i % 2 == (0 if split == "tune" else 1)]
    out = []
    for name, ctx_rows in contexts.items():
        pair = {}
        for r in ctx_rows:
            pair.setdefault((r["customer"], r["date"]), []).append(r["number"])
        base = l_pool if name == "L" else ctx_rows
        n = per_kind[name[0]]
        for kind in RECORD_KINDS:
            pool = [r for r in base if kind != "number" or len(pair[(r["customer"], r["date"])]) == 1]
            for s in range(n):   # one row from each of n equal slices of the export, so every position is asked
                r = rng.choice(pool[s * len(pool) // n:(s + 1) * len(pool) // n])
                q, gold = record_question(kind, r)
                out.append({"context": name[0], "window": name, "split": split, "kind": kind, "question": q,
                            "gold": gold, "currency": r["currency"], "row": r["number"],
                            "position": round(ctx_rows.index(r) / max(1, len(ctx_rows) - 1), 3)})
    return out, {k: render_records(v) for k, v in contexts.items()}


def prepare(size: str) -> dict:
    rng = random.Random(SEED)
    nq = nq_items()
    n = SIZES[size]
    pool = sorted(k for k, v in nq.items() if v["split"] == n["split"])
    picks = sorted(rng.sample(pool, n[n["split"]]))
    qs = [nq[i] for i in picks]
    with_free = [q["q"] for q in qs if q["abstain"]]
    run_abstain = set(rng.sample(with_free, n["abstain"]))
    for q in qs:
        q["run_abstain"] = q["q"] in run_abstain
    recs, contexts = records_items(n["records_per_kind"], n["split"], rng)
    return {"size": size, "seed": SEED, "k_passages": K_PASSAGES, "nq": qs, "records": recs, "contexts": contexts,
            "counts": {"nq_with_answer": len(nq), "nq_in_split": len(pool), "nq": len(qs),
                       "abstain": len(run_abstain), "records": len(recs)}}


def load(size: str) -> dict:
    return json.loads((DIR / f"tasks_{size}.json").read_text())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        for size in SIZES:
            t = prepare(size)
            (DIR / f"tasks_{size}.json").write_text(json.dumps(t))
            print(size, len(t["nq"]), "NQ questions,", len(t["records"]), "record questions,", t["counts"])
