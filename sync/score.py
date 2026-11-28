"""Episode 6: scoring replies and classifying what an index holds.

Replies: **current** (the right value and no earlier one), **stale** (an earlier value and not the right one),
**both**, **declined** ("I don't know"), or **other**. Values are matched by kind: amounts with their currency,
numbers as whole numbers, menu paths as their labels in order, URLs exactly. For plan names and statuses, which a
reply often mentions more than one of ("Pro and above", "generally available, not in beta"), the first one
mentioned counts. For a question about a deleted article, any reply without the deleted detail is current, and a
decline counts as current too (the record no longer has an answer). For a new article, a decline is "missing".

Index entries: **current** (one of its article's chunks as the article is now), **outdated** (its article exists
but no longer has this chunk), **deleted** (its article is gone), **duplicate** (the same text of the same article
already counted).
"""
from __future__ import annotations

import re

from sync.record import chunk_texts

DECLINE = re.compile(r"\b(i )?(do not|don't|does not|doesn't|cannot|can't|couldn't|could not) (know|find|say|"
                     r"determine|provide|answer)|\bnot (mentioned|provided|specified|stated|included|available|listed|"
                     r"found|given|clear)\b|\bno (information|mention|details?)\b|\bunknown\b|\bnot sure\b|"
                     r"\bunable to\b|\bnot in the (context|provided)", re.I)
PLANS = ["Starter", "Pro", "Business", "Enterprise"]
STATUS = {"generally available": r"generally available|\bGA\b", "in beta": r"\bbeta\b", "in preview": r"\bpreview\b"}


def _num(s: str) -> str:
    return re.search(r"\d[\d,]*(?:\.\d+)?", s).group(0).replace(",", "")


def _num_re(n: str) -> str:
    """A whole number, with or without a thousands separator (1200 or 1,200), not part of a longer number."""
    whole, _, frac = n.partition(".")
    w = re.sub(r"\B(?=(\d{3})+$)", ",?", whole) if len(whole) > 3 else whole
    return rf"(?<![\d.,]){w}{(r'\.' + frac) if frac else ''}(?![\d]|[.,]\d)"


def pattern(kind: str, value: str) -> re.Pattern:
    v = value
    if kind == "usd":
        n = _num_re(_num(v))
        return re.compile(rf"(?:\$|US\$|USD ?){n}(?:\.00)?(?!\d)|{n}(?:\.00)? ?(?:USD|US dollars|dollars)", re.I)
    if kind == "eur":
        n = _num_re(_num(v))
        return re.compile(rf"(?:€|EUR ?){n}(?:[.,]00)?(?!\d)|{n}(?:[.,]00)? ?(?:€|EUR|euros?)", re.I)
    if kind in ("count", "gb", "rate", "days", "hours", "minutes", "percent"):
        return re.compile(_num_re(_num(v)))
    if kind == "path":
        labels = [re.escape(x.strip()) for x in v.split("→")]
        # Labels are joined by an arrow, ">", "/" or "|", not by any punctuation: "team members, go to
        # Settings → Members" must not read as the path "Team → Members" (amendment 10).
        return re.compile(r"\s*(?:→|->|=>|>|›|»|/|\|)\s*".join(labels), re.I)
    if kind == "url":
        return re.compile(re.escape(v), re.I)
    if kind == "status":
        return re.compile(STATUS[v], re.I)
    times = re.findall(r"\d\d:\d\d", v)
    if times:   # support hours, maintenance window: the times, in order
        return re.compile(r".{0,40}".join(re.escape(t) for t in times), re.I | re.S)
    return re.compile(re.escape(v), re.I)


def first_of(kind: str, reply: str, values: list[str]) -> str | None:
    """For plan names and statuses: the value mentioned first in the reply."""
    best = None
    for v in values:
        p = re.compile(rf"\b{re.escape(v)}\b", re.I) if kind == "name" else pattern(kind, v)
        m = p.search(reply)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), v)
    return best[1] if best else None


def mentions(q: dict, text: str) -> tuple[bool, bool]:
    """(the right value is in the text, an earlier value is in the text)"""
    kind = q["fact_kind"]
    right = bool(q["right"]) and bool(pattern(kind, q["right"]).search(text))
    stale = any(pattern(kind, s).search(text) for s in q["stale"])
    return right, stale


def score(q: dict, reply: str) -> str:
    kind = q["fact_kind"]
    first_wins = kind == "status" or (kind == "name" and q["fact"].endswith(".plan"))
    if first_wins and q["right"]:
        values = list(STATUS) if kind == "status" else PLANS
        first = first_of(kind, reply, values)
        if first == q["right"]:
            return "current"
        if first in q["stale"]:
            return "stale"
        return "declined" if DECLINE.search(reply) else "other"
    right, stale = mentions(q, reply)
    if q["kind"] == "deleted":
        return "stale" if stale else "current"
    if right and stale:
        return "both"
    if right:
        return "current"
    if stale:
        return "stale"
    if DECLINE.search(reply):
        return "missing" if q["kind"] == "new" else "declined"
    return "other"


# --------------------------------------------------------------------------------------------- the index
def classify(entries: list[dict], live: dict[int, dict]) -> list[str]:
    """One class per entry, in order. `live`: article id -> its row as the record holds it now."""
    seen = set()
    out = []
    for e in entries:
        aid = int(e["article_id"])
        k = (aid, e["text"])
        if aid not in live:
            c = "deleted"
        elif e["text"] not in chunk_texts(live[aid]):
            c = "outdated"
        elif k in seen:
            c = "duplicate"
        else:
            c = "current"
        seen.add(k)
        out.append(c)
    return out


def audit(entries: list[dict], live: dict[int, dict]) -> dict:
    from collections import Counter
    classes = classify(entries, live)
    have = {(int(e["article_id"]), e["text"]) for e, c in zip(entries, classes) if c == "current"}
    want = {(aid, t) for aid, r in live.items() for t in chunk_texts(r)}
    return {"entries": len(entries), **Counter(classes), "record_chunks": len(want), "missing": len(want - have)}


def in_sync(entries: list[dict], row: dict | None) -> tuple[bool, bool]:
    """For one article: (every current chunk is in the index, and nothing else of it is)."""
    if row is None:
        return True, not entries
    want = chunk_texts(row)
    texts = [e["text"] for e in entries]
    has_all = all(t in texts for t in want)
    clean = has_all and len(texts) == len(want) and sorted(texts) == sorted(want)
    return has_all, clean
