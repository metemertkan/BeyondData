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
| 2 | Which vector database should you use? | [`vectors/`](vectors), [`scripts/ep02_run.py`](scripts/ep02_run.py) |

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
P5 answers counted by a rule (revenue figures built from other customers' invoices, which the automatic check,
looking for the right figure, misses). `built` ran the same kind of query and row-level security returned
Mallory's own $89. Full tables, trap attribution and cost: [`results/ep01/summary.md`](results/ep01/summary.md).

**A bigger model** (gpt-oss:20b, 12 questions × 5 designs × 2 seeds, compared on the same questions and seeds):

| Design | Right, qwen3:8b / gpt-oss:20b (of 14) | Leaks, qwen3:8b / gpt-oss:20b (of 8) | Wrote, gpt-oss:20b |
| :--- | ---: | ---: | ---: |
| `rows` | 2 / 2 | 6 / 1 | 0 |
| `sql_raw` | 6 / 4 | 6 / 1 | 0 |
| `sql_guide` | 6 / 6 | 6 / 3 | **2 of 2** |
| `tools` | 10 / 10 | 0 / 1 | 0 |
| `built` | 12 / 12 | 0 / 0 | 0 |

gpt-oss declined more of Mallory's requests, but `sql_guide` marked her invoice as paid in both runs
("Invoice 482 has been marked as paid."), and `tools` fetched Ada's account with `get_account(customer_id=1)`.

**Limits.** One synthetic company, two local models on CPU (qwen3:8b on everything, three seeds; gpt-oss:20b on a
subset). With qwen3, "mark as paid" wrote once in a pilot run and never in the batch. gpt-oss sometimes returns SQL as
a call to a tool it wasn't offered; `ledger/llm.py` turns that SQL into the normal SQL block and records it in
`usage.unoffered_tool_calls` (19 of 120 runs). The P5 leaks (a revenue figure from other customers' invoices) are
counted by a rule in `scripts/ep01_summary.py`, in their own column, because the automatic check only recognises the
right figure.

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

## Episode 2: I gave six vector databases the same million vectors

One million Wikipedia passages from Natural Questions, embedded with Cohere embed-english-v3 (1024-d, the
[BEIR release](https://huggingface.co/datasets/CohereLabs/beir-embed-english-v3), no account needed), and 3,452 real
questions with human relevance labels (1,000 to tune, 2,452 to test). Six databases, each alone in Docker on the same
6 cores (12 threads) and 16 GB:

| Database | Version | Index as shipped (read back from the running database) | Search-time default |
| :--- | :--- | :--- | :--- |
| pgvector | 0.8.7 (Postgres 18) | HNSW m 16, ef_construction 64, built in 64 MB of `maintenance_work_mem` | `hnsw.ef_search` 40 |
| Qdrant | 1.20.2 | HNSW m 16, ef_construct 100, float32 | hnsw_ef = ef_construct |
| Milvus | 3.0.6 standalone | `AUTOINDEX` = HNSW_SQ, 4-bit, M 18, efConstruction 240, re-ranked with FP16 copies | `refine_k` 1 |
| Weaviate | 1.40.7 | HNSW maxConnections 32, efConstruction 128, no compression | dynamic ef, min 100 |
| Elasticsearch | 9.5.5 (basic) | `bbq_hnsw`: 1-bit vectors, m 16, ef_construction 100, rescored with float32 | num_candidates 1.5 × k, oversample 3 |
| Chroma | 1.5.9 | HNSW max_neighbors 16, ef_construction 100, float32 | ef_search 100 |

Three designs: **default** (the quickstart, no parameters), **tuned** (the cheapest search-time setting reaching recall
0.95, then 0.99, picked on tuning questions) and **built** (pick the recall target from the labels, set it in code,
check it on 200 questions at every deploy). Build-time settings stay at their defaults throughout.

### Results (1,000,000 passages, 2,452 test questions)

As shipped:

| Database | Recall@10 | nDCG@10 | Answer lost | p50 ms | q/s (16 clients) | Ready after | Disk |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.919 | 0.699 | 121 | 4.3 | 681 | 51 min | 14.9 GB |
| Qdrant | 0.970 | 0.727 | 35 | 4.2 | 403 | 9.3 min | 4.5 GB |
| Milvus | 0.911 | 0.707 | 105 | 1.8 | 2,176 | 11 min | 22.3 GB |
| Weaviate | 0.978 | 0.731 | 24 | 2.7 | 1,327 | 15.4 min | 4.6 GB |
| Elasticsearch | 0.901 | 0.702 | 116 | 2.9 | 1,969 | 27.5 min | 6.2 GB |
| Chroma | 0.958 | 0.719 | 57 | 2.5 | 495 | 18.5 min | 4.4 GB |
| exact search | 1 | 0.739 | 0 | | | | |

"Answer lost": questions where exact search's top 10 holds a labeled answer and the database's holds none.

- All six returned the same top 10 for **43%** of test questions (same top 1 for 90%).
- Tuned to recall 0.95, nDCG is 0.716–0.725 for all six; p50 ranges from 1.7 ms (Weaviate) to 8.4 ms (pgvector).
- Tuned to 0.99: Qdrant, Milvus, Weaviate and Chroma get there (Chroma 0.9895 on test); pgvector tops out at 0.986
  (`ef_search` 768, 48 ms) and Elasticsearch at 0.982 (num_candidates 1,024). Their default index builds are the limit.
- Built: the labels pick recall 0.99 (below it, some setting loses more than 0.5 nDCG points). The deploy check fails
  all six defaults and blocks pgvector and Elasticsearch outright.
- Milvus compacted from 27 segments to 6 in the minutes after indexing, and its recall changed with it (0.933 → 0.911).
- Read your own write: Milvus found 0 of 991 just-inserted passages at once (consistency "Bounded"), Elasticsearch 1
  (1 s refresh); all of them a second later. The others found every one at once.

The 100,000-passage pilot, its harness fixes and four design amendments made before the full run (re-ranking depth
tied to the knob for Milvus and Elasticsearch, Chroma restarts to apply `ef_search`, write test on the top 10, settle
before measuring) are in `results/ep02/pilot/`. Full tables: [`results/ep02/full/summary.md`](results/ep02/full/summary.md).

**Limits.** One machine, one dataset and embedding model, each database through its own Python client as the
quickstart uses it (Qdrant and Chroma over REST). Memory figures are docker's and exclude page cache, so they
understate databases that read vectors through the OS cache; disk is the fairer size.

### Run it

```bash
# needs Python 3.12+, uv, Docker; ~5 GB download, ~30 GB free disk, 16 GB RAM for the databases
bash vectors/download.sh                      # BEIR NQ with Cohere vectors -> data/ep02/raw
uv run python -m vectors.data --prepare       # the million, the questions, exact ground truth (~2 min)
uv run pytest tests/test_ep02.py
# one database at a time, client pinned away from the database's cores; full run ~3 h
taskset -c 6-11,18-23 uv run python -m scripts.ep02_run --size pilot --db qdrant
taskset -c 6-11,18-23 uv run python -m scripts.ep02_run --size full --db all
uv run python -m scripts.ep02_summary --size full   # results/ep02/full/summary.md
```

Pin to cores that fit your machine: `docker-compose.ep02.yml` gives each database `cpuset` 0-5,12-17.

### Layout

```text
vectors/
  download.sh    the raw parquet files
  data.py        the million, the split, exact ground truth
  engines.py     one adapter per database: load, index, read back settings, the search knob, insert
  milvus/        Milvus standalone config (embedded etcd, local storage)
docker-compose.ep02.yml   the six databases, same limits, own compose project
scripts/ep02_run.py       one database at a time: load, index, settle, default, sweep, throughput, write test
scripts/ep02_summary.py   the tables
tests/test_ep02.py
```
