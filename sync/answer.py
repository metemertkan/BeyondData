"""Episode 6: the model's answer to every question, from the chunks each design retrieved.

qwen3:8b (thinking off), greedy, num_ctx 8,192 (set, not Ollama's default: Episode 5), num_predict 128, on the CPU,
one request at a time, through Ollama 0.40.11 in Docker (bd6-ollama). The prompt is LangChain's classic RAG prompt
with the 4 chunks in retrieved order. Each distinct prompt is answered once, in a fixed order (by question time,
then design order), and designs that retrieved the same chunks for a question share that reply.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from sync import kb, score
from sync.designs import ORDER

ROOT = Path(__file__).resolve().parent.parent
OLLAMA = os.environ.get("BD6_OLLAMA", "http://127.0.0.1:11436")
MODEL = "qwen3:8b"
OPTIONS = {"temperature": 0, "top_k": 1, "seed": 1, "num_ctx": 8192, "num_predict": 128}
PROMPT = ("You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer "
          "the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and "
          "keep the answer concise.\nQuestion: {question} \nContext: {context} \nAnswer:")


def prompt(question: str, chunks: list[str]) -> str:
    return PROMPT.format(question=question, context="\n\n".join(chunks))


def pkey(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def ask(client: httpx.Client, p: str) -> dict:
    t = time.time()
    r = client.post(f"{OLLAMA}/api/chat", json={"model": MODEL, "messages": [{"role": "user", "content": p}],
                                                 "stream": False, "think": False, "keep_alive": -1,
                                                 "options": OPTIONS})
    r.raise_for_status()
    d = r.json()
    return {"reply": d["message"]["content"].strip(), "prompt_tokens": d.get("prompt_eval_count"),
            "reply_tokens": d.get("eval_count"), "done_reason": d.get("done_reason"), "s": round(time.time() - t, 2)}


def answer_all(size: str, designs: list[str], log=print) -> None:
    out = ROOT / "results" / "ep06" / size
    qs = {q["qid"]: q for q in kb.load(size)["questions"]}
    todo: dict[str, str] = {}
    order = []
    logs = {d: [json.loads(x) for x in (out / f"{d}.questions.jsonl").read_text().splitlines()]
            for d in designs if (out / f"{d}.questions.jsonl").exists()}
    for qid in sorted(qs, key=lambda k: qs[k]["t"]):
        for d in [x for x in ORDER if x in logs]:
            row = next(x for x in logs[d] if x["qid"] == qid)
            p = prompt(qs[qid]["question"], [c["text"] for c in row["chunks"]])
            k = pkey(p)
            if k not in todo:
                todo[k] = p
                order.append(k)
    path = out / "answers.jsonl"
    done = {}
    if path.exists():
        done = {x["key"]: x for x in map(json.loads, path.read_text().splitlines())}
    left = [k for k in order if k not in done]
    log(f"answers: {len(order)} distinct prompts, {len(left)} to go")
    client = httpx.Client(timeout=900)
    t0 = time.time()
    with path.open("a") as f:
        for i, k in enumerate(left, 1):
            r = ask(client, todo[k])
            f.write(json.dumps({"key": k, **r}, ensure_ascii=False) + "\n")
            f.flush()
            if i % 25 == 0:
                rate = (time.time() - t0) / i
                log(f"answers: {i}/{len(left)}, {rate:.1f} s each, about {rate * (len(left) - i) / 3600:.1f} h left")
    log("answers: done")


def scored(size: str, designs: list[str]) -> dict[str, list[dict]]:
    """Per design: every question with its chunks, reply and score."""
    out = ROOT / "results" / "ep06" / size
    qs = {q["qid"]: q for q in kb.load(size)["questions"]}
    answers = {x["key"]: x for x in map(json.loads, (out / "answers.jsonl").read_text().splitlines())} \
        if (out / "answers.jsonl").exists() else {}
    res = {}
    for d in designs:
        p = out / f"{d}.questions.jsonl"
        if not p.exists():
            continue
        rows = []
        for x in map(json.loads, p.read_text().splitlines()):
            q = qs[x["qid"]]
            a = answers.get(pkey(prompt(q["question"], [c["text"] for c in x["chunks"]])))
            rows.append(x | {"question": q["question"], "right": q["right"], "stale": q["stale"], "fact": q["fact"],
                             "reply": a["reply"] if a else None, "score": score.score(q, a["reply"]) if a else None})
        res[d] = rows
    return res
