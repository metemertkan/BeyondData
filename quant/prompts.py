"""Episode 5: the prompts. Wording A is the one every design uses; wording B says the same thing in other
words, and F16 with wording B is the noise floor: what changes when nothing but the phrasing changes.

Both wordings ask for the same reply format and the same refusal phrase, so one scorer reads both.
The records export comes before the question, so every question about one export shares the prompt prefix
and Ollama reuses its cache (the export is read once per context, not once per question).
"""
from __future__ import annotations

NOT_IN_PASSAGES = "not in the passages"
NOT_IN_RECORDS = "not in the records"

WORDING = {
    "A": {
        "closed": "Answer this question with a short answer: a few words, no explanation.\n\nQuestion: {question}",
        "rag": ("Answer the question using only the passages below. Reply with a short answer: a few words, "
                "no explanation. If the passages don't contain the answer, reply exactly: " + NOT_IN_PASSAGES +
                ".\n\n{passages}\n\nQuestion: {question}"),
        "records": ("Below is an export of invoices. Answer the question using only these records. Reply with "
                    "the value only. If the records don't contain it, reply exactly: " + NOT_IN_RECORDS +
                    ".\n\n{records}\n\nQuestion: {question}"),
    },
    "B": {
        "closed": "Give a brief answer to the question below, just a few words and nothing else.\n\nQuestion: {question}",
        "rag": ("Here are some passages. Using nothing but these passages, give a brief answer to the question "
                "that follows, just a few words. If the answer isn't in the passages, reply exactly: " +
                NOT_IN_PASSAGES + ".\n\n{passages}\n\nQuestion: {question}"),
        "records": ("The invoice records are exported below. Using nothing but these records, answer the "
                    "question with just the value. If the value isn't in the records, reply exactly: " +
                    NOT_IN_RECORDS + ".\n\n{records}\n\nQuestion: {question}"),
    },
}


def passages_block(passages: list[dict]) -> str:
    return "\n\n".join(f"Passage {i} (title: {p['title']}): {p['text']}" for i, p in enumerate(passages, 1))


def build(task: str, item: dict, wording: str, contexts: dict | None = None) -> str:
    w = WORDING[wording]
    if task == "closed":
        return w["closed"].format(question=item["question"])
    if task in ("rag", "abstain"):
        return w["rag"].format(passages=passages_block(item[task]), question=item["question"])
    return w["records"].format(records=contexts[item["window"]], question=item["question"])
