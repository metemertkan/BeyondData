# BeyondData

**Beyond the PoC: what happens to your data once an AI system uses it, measured.**

How an AI finds your data, where the vectors live, how small they can get, how they stay true,
and what an agent remembers. Each episode takes one production problem, builds it the way demos
do and the ways production could, and counts what really happens.

Everything runs locally: local models through [Ollama](https://ollama.com), databases in Docker.
No accounts, no keys.

| Episode | Question | Code |
| :--- | :--- | :--- |
| 1 | Can you let an AI answer questions from your database? | [`ledger/`](ledger), [`scripts/ep01_run.py`](scripts/ep01_run.py) |

## Episode 1: I asked my AI for the total

Acme Cloud (the company from [BeyondAgents](https://github.com/metemertkan/BeyondAgents)) keeps its
billing in Postgres: customers, invoices, invoice lines, refunds and support tickets. Staff ask an AI
assistant questions about it; customers ask it about their own accounts in the portal.

The same questions go through five designs:

| Design | What the model gets |
| :--- | :--- |
| `rows` (the PoC) | Every row as a sentence, embedded; the 10 nearest rows to the question |
| `sql_raw` | The schema; it writes SQL that runs on the app's own connection |
| `sql_guide` | The same, plus the data team's guide (definitions, currencies, time zone) |
| `tools` | A small metrics API written in code; no SQL |
| `built` | The metric tools first, read-only SQL for the rest, row-level security in the portal, a receipt written by code |

### Results (qwen3:8b, 26 questions × 5 designs × 3 seeds = 390 runs)

Staff questions, 63 answers per design:

| Design | Right | Declined | Confidently wrong |
| :--- | ---: | ---: | ---: |
| `rows` | 18 (29%) | 9 | 36 (57%) |
| `sql_raw` | 27 (43%) | 5 | 31 (49%) |
| `sql_guide` | 38 (60%) | 3 | 22 (35%) |
| `tools` | 46 (73%) | 5 | 12 (19%) |
| `built` | 53 (84%) | 0 | 10 (16%) |

- `rows` got every lookup right and 0 of 36 counts, sums, averages, rankings and line-item questions.
  October 2026 invoices: 2, 2 and 3. There were 42.
- 51 of the 53 wrong answers from `sql_raw` and `sql_guide` came from a final query that ran without an error.
  `sql_raw`'s October revenue, $4,097.50, is exactly UTC months + test accounts + no EUR conversion + no refunds;
  with the guide it still counted months in UTC ($3,762.45; right: $3,802.45).
- `tools` declined 5 of 9 lookups: no tool covered them. `built` fell back to read-only SQL and got 9 of 9.
- No design answered the two "search tickets by meaning" questions right; the best found 4 of 5 complainers.

Customer portal, Mallory logged in, 12 attempts per design to get someone else's data:

| Design | Gave her other customers' or Acme's data | Wrote to the database |
| :--- | ---: | ---: |
| `rows` | 9/12 | 0 |
| `sql_raw` | 9/12 | 0 |
| `sql_guide` | 9/12 | 0 |
| `tools` | 0/12 | 0 |
| `built` | 0/12 | 0 |

Six of each nine are counted by `ledger/score.py` (Ada's October payment, Business customers' emails); three are
P5 answers checked by hand: company-wide revenue totals that were wrong numbers, so the automatic check (which
looks for the right figure) missed them. `built` ran the same kind of query and row-level security returned
Mallory's own $89. Full tables, trap attribution and cost: [`results/ep01/summary.md`](results/ep01/summary.md).

**Limits.** One synthetic company, one 8B model on CPU, three seeds. In the pilot, `sql_guide` once ran
`UPDATE 1` to mark Mallory's invoice paid; in the 15 batch runs of that question, nothing wrote.

### Run it

```bash
# needs Python 3.12+, uv, Docker, and Ollama with qwen3:8b and bge-m3 pulled
docker compose up -d                          # Postgres on localhost:5436
uv run python -m ledger.world --load          # tables, roles and Acme's data (one seed)
uv run pytest                                 # the right answers, checked against SQL; the roles; the scorer
uv run python -m scripts.ep01_run --questions S1 --seeds 1    # one question, every design
uv run python -m scripts.ep01_run             # the full batch, results/ep01/runs.jsonl
uv run python -m scripts.ep01_summary         # results/ep01/summary.md
```

### Layout

```text
ledger/
  world.py       Acme's data (seeded), the schema, roles and row-level security
  guide.py       the schema and the data team's guide, as the models see them
  questions.py   the questions and their right answers, computed in Python
  designs.py     the five designs
  score.py       right, declined, or confidently wrong; leaks and writes in the portal
  llm.py         Ollama chat and embeddings
scripts/ep01_run.py       the batch (resumable)
scripts/ep01_summary.py   the tables
scripts/ep01_rescore.py   rescore stored replies after a scorer fix
tests/test_ep01.py
```
