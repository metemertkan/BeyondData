"""Episode 5: scoring a reply.

closed, rag  right if any NQ-open answer, normalized SQuAD-style, appears in the normalized reply as whole
             tokens (the "has answer" rule of open-domain QA: "4" is not in "category 14"). A reply that is
             the refusal phrase is scored "declined".
abstain      right if the reply declines ("not in the passages") and contains none of the answer strings;
             any other reply is "answered" (from the model's memory, not from your data), right or not.
records      amount: a number in the reply equals the amount (59, 59.00, USD 59.00, 1,234.50);
             date: a date in the reply equals the issue date (2025-08-01, August 1, 2025, Aug. 1, 2025,
             1 August 2025, 08/01/2025);
             email: the address appears in the reply; number: the invoice number appears and no other one does.
"""
from __future__ import annotations

import re
from datetime import date

from quant.prompts import NOT_IN_PASSAGES, NOT_IN_RECORDS
from quant.tasks import contains, normalize

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())} | {"sept": 9})
NUM = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")


def declined(reply: str, phrase: str) -> bool:
    return normalize(phrase) in normalize(reply)


def numbers(reply: str) -> list[float]:
    out = []
    text = re.sub(r"INV[- ]?\d{5}|\b\d{4}-\d{1,2}-\d{1,2}\b", " ", reply, flags=re.I)  # ids and dates aren't amounts
    for m in NUM.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def dates(reply: str) -> set[date]:
    t = reply.lower()
    out = set()
    for y, m, d in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        out.add((int(y), int(m), int(d)))
    for mon, d, y in re.findall(r"\b([a-z]+)\.? (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})\b", t):
        if mon in MONTHS:
            out.add((int(y), MONTHS[mon], int(d)))
    for d, mon, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)? ([a-z]+),? (\d{4})\b", t):
        if mon in MONTHS:
            out.add((int(y), MONTHS[mon], int(d)))
    for m, d, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t):
        out.add((int(y), int(m), int(d)))
    res = set()
    for y, m, d in out:
        try:
            res.add(date(y, m, d))
        except ValueError:
            pass
    return res


def score(task: str, item: dict, reply: str) -> str:
    """'right', 'wrong' or 'declined' (abstain: 'right' = declined correctly, 'answered' otherwise)."""
    if task in ("closed", "rag", "abstain"):
        has = any(contains(reply, a) for a in item["answers"])
        if task == "abstain":
            return "right" if declined(reply, NOT_IN_PASSAGES) and not has else "answered"
        if has:
            return "right"
        return "declined" if declined(reply, NOT_IN_PASSAGES) else "wrong"
    kind, gold = item["kind"], item["gold"]
    if kind == "amount":
        ok = float(gold) in numbers(reply)
    elif kind == "date":
        ok = date.fromisoformat(gold) in dates(reply)
    elif kind == "email":
        ok = gold.lower() in reply.lower()
    else:
        found = {f"INV-{n}" for n in re.findall(r"INV[- ]?(\d{5})", reply.upper())}
        ok = found == {gold}
    if ok:
        return "right"
    return "declined" if declined(reply, NOT_IN_RECORDS) else "wrong"
