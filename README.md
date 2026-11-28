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
| 3 | What happens to vector search when you add a filter? | [`vectors/filtered.py`](vectors/filtered.py), [`scripts/ep03_run.py`](scripts/ep03_run.py) |
| 4 | How small can a vector get before search stops finding the answer? | [`vectors/compressed.py`](vectors/compressed.py), [`scripts/ep04_run.py`](scripts/ep04_run.py) |
| 5 | What does a 4-bit model forget about your data? | [`quant/`](quant), [`scripts/ep05_run.py`](scripts/ep05_run.py) |
| 6 | Your data changed. When does your AI find out? | [`sync/`](sync), [`scripts/ep06_run.py`](scripts/ep06_run.py) |

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


## Episode 3: I added a filter and asked for 10 results

Episode 2's million passages and 2,452 test questions, with six metadata fields on every passage (seed 7): four random
and nested like an org chart (`region` 50%, `dept` 10%, `team` 1%, `project` 0.1%) and two that follow the content
(`topic` ~1%, `subtopic` ~0.1%: k-means clusters of the vectors). Each question is filtered to the value on its own
answer's passage, so the answer is always inside the filter; exact search inside the filter finds a labeled answer for
91.5% of questions unfiltered and 99.6% with the 1% filter. Same six databases, images and limits as Episode 2.

Three designs: **as shipped** (fields stored the quickstart way, the filter in the query, nothing else), **tuned**
(each database's documented filter options, with the search knob swept) and **built** (a recall target from the
labels, a setting per filter field, a deploy check per field on 200 questions: recall ≥ target, no short result).

### Results (1,000,000 passages, 2,452 test questions)

As shipped, recall@10 inside the filter (results returned, of 10, where fewer):

| Database | none | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.921 | 0.905 | **0.473** (4.8) | **0.129** (1.3) | 1.000 | 0.814 (8.5) | 1.000 |
| Qdrant | 0.970 | 0.937 | **0.345** | **0.574** (9.96) | 0.998 | 0.990 | 1.000 |
| Milvus | 0.909 | 0.875 | 0.953 | 1.000 | 1.000 | 1.000 | 1.000 |
| Weaviate | 0.978 | 0.984 | 0.957 | 1.000 | 1.000 | 1.000 | 1.000 |
| Elasticsearch | 0.901 | 0.880 | 0.857 | **0.550** | 0.973 | 0.943 | 0.965 |
| Chroma | 0.959 | 0.972* | 0.989* | 0.997* | 1.000* | 0.990 | 0.999 |

\* Chroma: the cell averaged over 250 ms on its first 100 questions and stopped there, as the design fixed.

- **Three failures, no errors.** Too few: pgvector filters after the HNSW scan, so the 1% filter returned 1.3 of 10
  results on average and none for 6.3% of questions. The wrong ten: Qdrant without payload indexes lost the answer for
  62% of questions at 10%, Elasticsearch's ACORN default for 40% at 1%. Too slow: Chroma took 1.6 s at 50% (2.5 ms
  unfiltered). Milvus and Weaviate held up.
- **Random filters fail where topical ones of the same size don't:** team vs topic recall, Qdrant 0.574 vs 0.990,
  Elasticsearch 0.550 vs 0.943. Test with the filters your users send.
- **Every fix is a setting** (1,000 test questions): Qdrant payload indexes created before loading, 0.342 → 0.995 at 10%
  (created after loading: no change at 10%; graph build 531 s instead of 40 s); Elasticsearch's `fanout` heuristic,
  0.542 → 0.960 at 1%, or 512 candidates, 1.000; Weaviate's `sweeping` strategy, 0.958 → 0.994 at 10%. pgvector's
  iterative scans end the short results (0.940 at 1%); exact results come only from sequential scans, and `ef_search`
  is what makes the planner switch (1% at 256: 86 ms; 50% at 512: 1.4 s; back to the index at 1,000).
- **pgvector's plan cache.** After `SET hnsw.ef_search = 256` on a live connection, EXPLAIN showed a sequential scan
  while the prepared statement kept the HNSW plan it had cached: 4.04 of 10 results; 10 after `DEALLOCATE ALL`. The
  first full run's pgvector sweep had this problem; every pgvector setting now runs on its own connection, and
  pgvector was re-run in full (the first run is kept in `results/ep03/full/first_run_pgvector/`).
- **Built:** the labels pick a recall target of 0.99 again. The deploy check (200 test questions per field) fails 23
  of 30 (database, field) as shipped and 12 of 30 built; 8 of those reached 0.99 on the tuning questions and landed at
  0.984–0.989. Exploratory, chosen after the results: with a margin (0.995 when tuning), Qdrant, Milvus, Weaviate and
  Elasticsearch pass every field.

Full tables: [`results/ep03/full/summary.md`](results/ep03/full/summary.md). The 100,000-passage pilot is in
`results/ep03/pilot/` (no short results at that size: pgvector's planner scanned exactly for every filter of 10% or
less). Design amendments: three before the full run (sampled cells stop at 100 questions; knob cells run the tuning
questions plus a seeded 1,000 test questions; pgvector plans recorded at every `ef_search`) and one after it (a
connection per pgvector setting, the plan each statement ran, the plan-cache check, and the pgvector re-run).

**Limits.** Synthetic fields (random, or k-means clusters); each question filtered to its answer's own value; one
machine, one dataset, index builds at their defaults; Chroma's slow filtered cells stopped at 100 questions.

### Run it

```bash
# after Episode 2's data step (bash vectors/download.sh && uv run python -m vectors.data --prepare)
uv run python -m vectors.filters --prepare    # the six fields, exact filtered top 10 per question and filter
uv run pytest tests/test_ep03.py
taskset -c 6-11,18-23 uv run python -m scripts.ep03_run --size pilot --db all   # 100k passages, 600 questions
taskset -c 6-11,18-23 uv run python -m scripts.ep03_run --size full --db all    # ~14 h
uv run python -m scripts.ep03_summary --size full   # results/ep03/full/summary.md
```

`docker-compose.ep03.yml` has its own compose project (`beyonddata-ep03`, containers `bd3-*`), so its `down -v`
never touches Episodes 1 and 2.

### Layout

```text
vectors/
  filters.py     the six fields, exact filtered ground truth
  filtered.py    Episode 2's adapters with fields, filtered search and each database's filter options
docker-compose.ep03.yml   the six databases, Episode 2's images and limits, own compose project
scripts/ep03_run.py       one database at a time: per deployment load, then per option, knob and filter, every question
scripts/ep03_summary.py   the tables, the target, the built settings and the deploy checks
tests/test_ep03.py
```

## Episode 4: I compressed a million vectors to 1 bit

Episode 2's million passages (Cohere embed-english-v3, 1,024 dimensions) and 2,452 test questions. Every compression
level the six databases document, set the way their compression docs show it, everything else at its defaults: 23
deployments, each in a fresh container with its own load and index build.

| Database | float32 | 16-bit | 8-bit | 4-bit | 2-bit | 1-bit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| pgvector 0.8.7 | `vector` | `halfvec` | | | | `binary_quantize` bit index + the README's re-rank |
| Qdrant 1.20.2 | none (default) | | `scalar` | TurboQuant 4 | TurboQuant 2 | `binary`; TurboQuant 1 |
| Milvus 3.0.6 | `HNSW` | | `HNSW_SQ` (SQ8) | AUTOINDEX (SQ4U + FP16 refine) | | `IVF_RABITQ` + SQ8 refine |
| Weaviate 1.40.7 | none (default) | | RQ 8 | RQ 4 | | RQ 1; BQ |
| Elasticsearch 9.5.5 | `hnsw` | | `int8_hnsw` | `int4_hnsw` | | `bbq_hnsw` (the default) |
| Chroma 1.5.9 | the only option | | | | | |

One knob, c: how many candidates to look at (re-scored with the original vectors for a compressed index, the graph's
candidate list for float32), swept over 20 to 500. A **memory ladder** runs every deployment under 8, 4, 2, 1 and
0.5 GiB with no swap, after dropping its files from the host's page cache; it **runs at full speed** under a limit if
it answers 200 test questions with a median within 2× or 5 ms of its median at 16 GiB. **The vectors alone**: exact
search over each compressed representation in numpy, no index. **Matryoshka**: the 100,000-passage subset embedded
again with nomic-embed-text-v1.5, a model trained to be shortened.

Three designs: **as shipped** (no search parameters), **options** (the c sweep, the ladder at the tuned setting, the
vectors alone) and **built** (a recall target from the labels, a memory budget of 4, 2 or 1 GiB per million vectors,
and per database the fastest deployment whose tuned setting passes a check under that limit).

### Results (1,000,000 passages, 2,452 test questions)

1-bit as shipped, against the same database's float32 index:

| Database | 1-bit index | Recall | Answers lost | float32: recall / lost | Full speed down to: float32 → best compressed |
| :--- | :--- | ---: | ---: | :--- | :--- |
| Weaviate | RQ 1 | **0.972** | 37 | 0.978 / 22 | 8 GiB → 2 GiB |
| Qdrant | TurboQuant 1 | 0.951 | 44 | 0.971 / 28 | 4 GiB → **0.5 GiB** |
| Weaviate | BQ | 0.950 | 49 | 0.978 / 22 | 8 GiB → 2 GiB |
| Elasticsearch | BBQ (the default) | 0.901 | 106 | 0.912 / 121 | more than 8 GiB → 2 GiB |
| Qdrant | binary | 0.900 | 55 | 0.971 / 28 | 4 GiB → **0.5 GiB** |
| Milvus | IVF_RABITQ + SQ8 refine | 0.886 | 146 | 0.940 / 66 | 8 GiB → 2 GiB (89 ms a question) |
| pgvector | bit + README re-rank | **0.841** | **216** | 0.916 / 134 | more than 8 GiB → 2 GiB |
| Chroma | no compression setting | | | 0.957 / 65 | 8 GiB |

- **The defaults decided more than the bits.** Whether an index re-scores with the originals, and how many, is a
  default: Qdrant re-scores 1- and 2-bit but not int8 or 4-bit, so as shipped 2-bit (0.970) beat 4-bit (0.941);
  Elasticsearch re-scores only BBQ, which lost fewer answers than its own float32 index (106 against 121);
  Weaviate's RQ 1 is documented to re-score 512 but its graph hands it 100.
- **Memory: 4–8× saved, not 32×.** The graph, the heap, pgvector's float32 column and Milvus's refine copies stay.
  `docker stats` misleads both ways: Qdrant float32 read 439 MiB and needed 4 GiB; Elasticsearch read ~9 GiB, its heap.
- **Re-scoring deep nearly matches float32, and reads the originals.** At c = 500 the compressed indexes came within
  0.005 of their own float32 index in Qdrant, Weaviate and Elasticsearch. Those 500 originals are 2 MB a question,
  and under a limit they come off the disk: Qdrant TurboQuant 1 at 0.5 GiB took 4.6 ms as shipped (0.945) and 69 ms
  at c = 500 (0.985); 3.7 ms with 8 GiB. Milvus HNSW_SQ8, with nothing to re-score, held 0.992 at c = 500 from 16
  GiB down to 2 at ~11 ms.
- **The vectors alone:** int8 lost no answers; int4 none once the top 20 were re-scored; 1 bit scored against a
  float question lost 58 and none with the top 100 re-scored. Cohere's first 512 dimensions lost 89.
- **Matryoshka only on a model trained for it** (100,000 subset): at 256 dimensions nomic v1.5 lost 33 answers and
  Cohere v3 128; at 1 bit, Cohere lost 41 and nomic 85.
- **Built:** the labels pick a target of 0.995 (at 0.99, Qdrant int8 at c = 500 lost 0.53 nDCG points). At 4, 2 and
  1 GiB no database passes. Only Milvus HNSW reached the 0.9975 tuning margin; it passed at 8 GiB and didn't load
  at 4. Closest miss: Milvus AUTOINDEX at c = 500, 0.9955 at 4 GiB, which reached 0.997 on tuning, short of the
  margin. Exploratory, chosen after the results: at 0.99, Milvus HNSW_SQ8 alone passes at 2 GiB, none at 1.

Full tables: [`results/ep04/full/summary.md`](results/ep04/full/summary.md); the vectors alone in
[`results/ep04/vectors/`](results/ep04/vectors). The 100,000-passage pilot is in `results/ep04/pilot/` (float32 was
0.4 GB there, so the ladder separated nothing). Design amendments: four after the pilot, before the full run (0.995
added to the target levels with a margin of half the distance to 1; Weaviate RQ's knob sets `ef` with
`rescoreLimit`; "full speed" as 2× or 5 ms; a 600 s start limit) and one after it: Milvus builds indexes for merged
segments in the background while serving the old ones, so its settle now also waits for no pending index rows, and
Milvus HNSW and HNSW_SQ8 were re-run (the first run is kept in `results/ep04/full/first_run_milvus/`).

**Limits.** One machine (Ryzen 9 3900X, no AVX-512, NVMe); one dataset, with a model trained for int8 and binary;
Matryoshka only on the 100,000 subset; the ladder measures right after a restart; graph parameters at defaults.

### Run it

```bash
# after Episode 2's data step (bash vectors/download.sh && uv run python -m vectors.data --prepare)
uv run --with onnxruntime --with tokenizers --with huggingface_hub \
    python -m vectors.nomic --prepare                # nomic v1.5 on the 100k subset, ~3 hours on CPU
uv run python -m scripts.ep04_vectors --part million  # the vectors alone
uv run python -m scripts.ep04_vectors --part subset   # Matryoshka
uv run pytest tests/test_ep04.py
taskset -c 6-11,18-23 uv run python -m scripts.ep04_run --size pilot --db all   # 100k passages
taskset -c 6-11,18-23 uv run python -m scripts.ep04_run --size full --db all    # ~8.5 h
uv run python -m scripts.ep04_summary --size full    # results/ep04/full/summary.md
```

`docker-compose.ep04.yml` has its own compose project (`beyonddata-ep04`, containers `bd4-*`), so its `down -v`
never touches Episodes 1–3.

### Layout

```text
vectors/
  compressed.py   Episode 2's adapters with each database's documented compression, the knob c, settings read back
  nomic.py        nomic-embed-text-v1.5 on the 100k subset (ONNX on CPU), checked against Ollama
docker-compose.ep04.yml   the six databases, Episode 2's images, 16 GiB each (the ladder lowers it)
scripts/ep04_vectors.py   the vectors alone and Matryoshka: exact search over each representation
scripts/ep04_run.py       one database at a time: per deployment load, as shipped, the c sweep, the memory ladder
scripts/ep04_summary.py   the tables, the target, the built settings and the deploy checks
tests/test_ep04.py
```

## Episode 5: what does a 4-bit model forget about your data?

qwen3:8b (thinking off) on Ollama 0.40.11 in Docker, on the CPU (Ryzen 9 3900X, 12 threads), one request at a time.
700 test questions about four places your data can be when a model answers:

| Task | What it measures | Questions |
| :--- | :--- | ---: |
| closed | what the model knows: Episode 2's Natural Questions alone, NQ-open's short answers | 250 |
| rag | what it reads: the same questions with the 3 nearest passages (exact search over Episode 2's million) | 250 |
| abstain | whether it sticks to your data: 3 near passages without the answer; right is "not in the passages" | 100 |
| records | what it copies: Episode 1's invoices as an export in the prompt (80 invoices, or 320 = 13,329 tokens), one field looked up | 100 |

The weights: Ollama's `qwen3:8b-fp16` (the reference), `qwen3:8b-q8_0` and `qwen3:8b` (Q4_K_M, the default), and
Q6_K, Q5_K_M, Q3_K_M and Q2_K made here from Ollama's fp16 with llama.cpp's `llama-quantize` (static, no importance
matrix). **Answers lost** = right at fp16, wrong here. The **noise floor** is fp16 with every prompt reworded. Designs:
**as shipped** (`qwen3:8b` with no settings: 4,096-token context, temperature 0.6), the **ladder** (context set to
hold the data, greedy), as shipped with the context set, a KV cache at q8_0 and q4_0, qwen3:4b at Q8_0, and **built**
(per memory budget of 6, 8 or 12 GiB, the most weight bits that fit with the KV cache that fits, checked against the
noise floor).

### Results (700 test questions; data tasks = rag + abstain + records, 450)

| qwen3:8b | Loaded at 16,384 tokens (GiB) | Data right, of 450 | Data answers lost | Closed-book lost (of fp16's 65) | Writing, tokens/s |
| :--- | ---: | ---: | ---: | ---: | ---: |
| fp16 | 17.76 | 265 | — | — | 1.5 |
| fp16, prompt reworded (noise floor) | 17.76 | 278 | **5** | 4 | 1.5 |
| Q8_0 | 10.74 | 263 | 3 | 0 | 2.8 |
| Q6_K | 8.76 | 264 | 6 | 2 | 3.6 |
| Q5_K_M | 7.94 | 274 | 5 | 4 | 4.1 |
| Q4_K_M (Ollama's default) | 7.36 | 269 | **13** | 8 | 4.4 |
| Q3_K_M | 6.34 | 264 | **36** | 22 | 5.5 |
| Q2_K | 5.55 | 206 | 100 | 43 | 6.4 |
| **as shipped** (Q4_K_M, default context, sampled) | 5.54 (at 4,096) | 231 | **51** | 18 | 4.5 |
| qwen3:4b Q8_0 | 6.51 | 263 | 33 | 32 | 4.8 |

- **The default context forgot more than the bits.** As shipped, every lookup in the 13,329-token export was read
  as 2,050 tokens: the end of the prompt (invoices 272–320), without the instructions. 9 of 60 right, against 45 with
  the context set; 33 of the 60 replies gave another invoice's value (asked for INV-00018's amount, 74.00, it answered
  USD 244.00, INV-00272's). No error. Taken apart: the default context cost 32 answers, sampling 6, the 4 bits 13.
- **Accuracy hides which answers moved.** Q3_K_M scored 264 against fp16's 265 and lost 36 (gained 35). Q4_K_M scored
  269 and lost 13. Below 4 bits the model says "not in the passages" more: with the answer in the passages, fp16 17
  times, Q3_K_M 34, Q2_K 51.
- **Same label, different file.** Ollama's Q4_K_M and Q8_0 keep `attn_v` in F16 in every layer; llama-quantize's
  don't. The two Q4_K_M files lost 13 and 10 and differed on 134 of 700 replies.
- **KV cache (Q4_K_M):** q8_0 lost 12, q4_0 17 (f16: 13), saving 1.05 and 1.62 GiB at 16,384 tokens. On this CPU
  both halved reading speed (the 13,329-token export: 5.8 → 13 minutes). Exploratory: in the middle third of the long export, the three
  designs with a compressed KV cache got 15 of 20 right, every f16-cache design 8 to 11.
- **Built:** 12 GiB, Q8_0, lost 3: passes. 8 GiB, Q6_K with KV q8_0, lost 6: misses the noise floor (5) by one answer
  (Q6_K with an f16 cache also lost 6). 6 GiB, Q4_K_M with KV q4_0, lost 17: fails. Exploratory: Q5_K_M with an f16
  cache (7.94 GiB) lost 5.
- **The number on the box** (KL divergence against fp16 on the test passages, `llama-perplexity`): mean KLD Q8_0
  0.001, Q6_K 0.011, Q5_K_M 0.019, Q4_K_M 0.043 (llama-quantize's 0.049), Q3_K_M 0.162, Q2_K 0.722; same top token
  98.6% down to 68.2%. It ranks the big steps as the answers lost do; perplexity doesn't (Q6_K 8.04, below Q8_0's
  8.07; fp16 8.01).

Full tables: [`results/ep05/full/summary.md`](results/ep05/full/summary.md); KL divergence in
[`results/ep05/kld.json`](results/ep05/kld.json); the pilot (tuning questions) in `results/ep05/pilot/`. Design
amendments, all before the full run: Q4_K_M made with llama-quantize added as its own design (Ollama's files keep
`attn_v` in F16); the invoice-number question reworded ("Which invoice was issued to …" got the amount back); and one
task order for every design, data tasks first, because llama-server's prompt cache makes a reply depend on what ran
before it (a rerun in the same order repeats exactly: 0 of 168 replies differ).

**Limits.** One machine, CPU only (GPU kernels differ, especially for a compressed KV cache); one model, thinking
off; static quantization; short answers and at most 16,384 tokens; one noise floor (one rewording); one run per
design.

### Run it

```bash
# after Episode 2's data step (bash vectors/download.sh && uv run python -m vectors.data --prepare)
curl -L -o data/ep05/raw/nq_open_validation.parquet \
  https://huggingface.co/datasets/google-research-datasets/nq_open/resolve/main/nq_open/validation-00000-of-00001.parquet
uv run python -m quant.tasks --prepare               # data/ep05/tasks_{pilot,full}.json
docker compose -f docker-compose.ep05.yml up -d ollama
for m in qwen3:8b qwen3:8b-fp16 qwen3:8b-q8_0 qwen3:4b-q8_0; do docker exec bd5-ollama ollama pull $m; done
uv run python -m scripts.ep05_models --ladder --readback --tensors   # Q6_K..Q2_K from Ollama's fp16
uv run python -m scripts.ep05_budget                 # Act 3's picks from loaded sizes (results/ep05/budget.json)
uv run pytest tests/test_ep05.py
uv run python -m scripts.ep05_run --size pilot --designs all
uv run python -m scripts.ep05_run --size full --designs all     # ~23 h on this CPU
uv run python -m scripts.ep05_summary --size full    # results/ep05/full/summary.md
uv run python -m scripts.ep05_models --kld           # results/ep05/kld.json
```

`docker-compose.ep05.yml` has its own compose project (`beyonddata-ep05`, containers `bd5-*`), so its `down -v`
never touches Episodes 1–4.

### Layout

```text
quant/
  tasks.py        the four tasks: NQ questions with passages from Episode 2, Episode 1's invoices as an export
  prompts.py      wording A (every design) and wording B (the noise floor)
  score.py        the NQ rule, the refusal phrase, exact values for the records
  llm.py          one Ollama chat call: thinking off, 64-token cap, timings and token counts
docker-compose.ep05.yml   Ollama as shipped, Ollama with a KV cache type, llama.cpp tools (b12282)
scripts/ep05_models.py    the ladder (llama-quantize), read-back, tensor types, KL divergence
scripts/ep05_budget.py    loaded sizes per level and KV cache type, and Act 3's picks
scripts/ep05_run.py       every design over its tasks, one request at a time
scripts/ep05_summary.py   lost and gained against fp16, declines, records by position, speed, memory, built
tests/test_ep05.py
```

## Episode 6: your data changed. When does your AI find out?

Acme Cloud's help center (Episode 1's company) in Postgres: 1,140 generated articles, 1,649 chunks with LangChain's
`RecursiveCharacterTextSplitter(1000, 200)`. One month of changes is replayed into eight ways of keeping a vector
index in step with it, and the one I'd build. The month holds 721 saves through the app: 44 facts changed (168 saves), 400 wording edits,
110 new articles, 15 renames and 20 rewrites. It also holds 32 hard deletes and one SQL `UPDATE` that renames the
console in 560 articles without touching `updated_at`.

500 questions are asked at set moments, each with the right value at that moment:

- 300 about a changed fact, 2 minutes to 7 days after the change;
- 100 about unchanged facts;
- 50 about a deleted article;
- 50 about a new one.

The stack:

- **Index:** Weaviate 1.40.7 (flat, exact), the 4 nearest chunks.
- **Embeddings:** bge-small-en-v1.5 (fastembed, 28.9 chunks/s on the CPU).
- **Answers:** qwen3:8b (thinking off, greedy) with LangChain's classic RAG prompt.
- **Clock:** the month runs on a simulated clock with real database operations; a sync job takes its chunks times
  the measured time per chunk.

A reply is **stale** if it gives the old value and not the new one. **Stale from the index** means an outdated or
deleted chunk in its context gave it that value.

### Results (one month, 500 questions)

| Design | Questions with an outdated or deleted chunk | Stale replies | Stale from the index | A change reached the index | Chunks embedded |
| :--- | ---: | ---: | ---: | :--- | ---: |
| **indexed once** (the tutorial, as shipped) | 428 | 297 | 297 | never | 0 |
| **re-run nightly** (as the tutorial says) | 261 | 208 | 181 | 12.8 h (p50); old copies never left | 48,771 |
| rebuild nightly | 178 | 173 | 168 | 12.9 h | 48,771 |
| upsert nightly, ids from URL | 223 | 197 | 192 | 12.8 h; deletes never | 48,771 |
| LangChain record manager, every 5 min | 48 | 51 | 47 | 3 min; deletes at night | 5,469 |
| poll `updated_at`, every 5 min | 148 | 75 | 71 | 3 min; the migration and deletes never | 1,209 |
| same database (pgvector, in the save) | 87 | 11 | 7 | at the save; the migration never | 1,209 |
| change data capture (logical decoding) | **0** | 4 | **0** | under 1 s; 15 s for 300 saves at once | 2,280 |
| **built** (CDC, changed chunks only, a check, nightly reconciliation) | **0** | 4 | **0** | under 1 s; 16 s for 300 saves at once | **1,455** |

- **Re-running the tutorial's script adds, it doesn't replace.** After 30 nights the collection held 50,420 entries
  for 1,720 chunks: 97% outdated, deleted or duplicate. 3 days after the Business plan's API rate limit went from
  6,000 to 12,000 per minute, the context held the release note saying 12,000 (three times) and the old plan page
  saying 6,000; the reply was 6,000.
- **Nightly means the next day.** Rebuild, upsert and rerun took 12.8–12.9 h (median) to reflect a change; a fact
  asked about 1 hour after its change came back current at most 3 times in 38.
- **What a design never sees:** poll and same database never saw the migration (420 and 412 of 560 articles never
  reached the index; the rest only through later app edits). Once, rerun, upsert and poll never removed a deleted
  article: 44 of 50 deleted-article questions gave the retired detail (rerun: 35).
- **CDC and built pass the target** (no stale context, fresh within 5 minutes, record and index agree at every
  daily check). Built embedded 36% fewer chunks and got the migration in within 22 s, against CDC's 37 s.
- **In real time** (20 minutes per design, an edit every 10 s and 300 saves at once): CDC and built under 1.5 s
  steady and 16 s for the burst. Same database at the save, but saves took 34 ms instead of 12 (12.7 s for the 300).
  Poll lost one save outright: an article stamped before the poll's cut-off but committed after its query.
- **The model doesn't notice an out-of-date context** (exploratory): in 24 prompts with the new value in a current
  chunk and the old value in an outdated one, the reply gave the old value 17 times, the new one 4, both 3.
- **A check alone isn't enough** (exploratory): nightly rebuild plus the query-time check had no stale context and
  its stale replies fell from 173 to 21, but 177 replies missed the answer (rebuild alone: 84) and only 22 said they
  didn't know. With the "in beta" line dropped, qwen3:8b guessed "generally available", the old value.
- **Six vector databases at one million, the same 1,000 ids sent again** through each quickstart's insert call:
  Qdrant, Weaviate and Elasticsearch replaced the vectors; pgvector refused the batch (duplicate key); Chroma kept the
  old vectors with no error; Milvus kept both (1,001,000 vectors). Each database's upsert call replaced them in all
  six. Updates and deletes showed in the next search, Milvus's within 0.24 s and Elasticsearch's within 1.04 s. After
  three rounds of 100,000 updates, recall held in four of six; pgvector lost 0.0125 until a 92-minute `VACUUM`;
  Milvus lost 0.0156, and more after its compaction. Qdrant's searches were up to 18 times slower until its optimizer
  finished.

Full tables: [`results/ep06/full/summary.md`](results/ep06/full/summary.md); raw replies and audits in
`results/ep06/full/`. Design amendments before the full run (pilot week, 100 questions) include: changes limited to
values nothing else in the help center states; the record manager uses LangChain's default SHA-1 key (SHA-256 ids
aren't UUIDs for Weaviate); the check compares the chunk's text against the article rather than a stored hash;
worker-down designs added as exploratory. Recorded after the run started: the six-database test uses 200 ids for
visibility, polled every 50 ms, and the real-time check runs 20 minutes per design. After the results, one scoring
fix: a menu-path pattern read "team members" as the old path "Team → Members" (the same question's 8 replies in
every design).

**Limits.** One generated help center (1,140 articles), whose release notes quote the question they answer; a
simulated clock for the month; one embedding model, one vector store for the split designs, one answering model; one
run.

### Run it

```bash
uv run python -m sync.kb --prepare                  # data/ep06/{pilot,full}/: the help center, the month, the questions
docker compose -f docker-compose.ep06.yml up -d record weaviate ollama
docker exec bd6-ollama ollama pull qwen3:8b
uv run pytest tests/test_ep06.py
uv run python -m scripts.ep06_run --calibrate       # embedding speed on the help center's chunks
uv run python -m scripts.ep06_run --size pilot      # the pilot week into every design
uv run python -m scripts.ep06_run --size pilot --answers
uv run python -m scripts.ep06_stores --prepare      # after Episode 2's data step: vectors from outside the million
sh scripts/ep06_full.sh > results/ep06/full.log 2>&1    # replay, answers, real time, the six databases (~13 h here)
uv run python -m scripts.ep06_summary --size full   # results/ep06/full/summary.md
```

`docker-compose.ep06.yml` (project `beyonddata-ep06`, containers `bd6-*`) holds the record, its index and the model;
`docker-compose.ep06-stores.yml` (project `beyonddata-ep06s`, containers `bd6s-*`) holds Act 2's six databases, so
the stores harness's `down -v` never touches the record or Episodes 1–5.

### Layout

```text
sync/
  kb.py         Acme Cloud's help center (1,140 articles), one month of changes, questions with the right value
  record.py     the record in Postgres (logical decoding on), the application's save, the tutorial's splitter
  index.py      Weaviate collections (flat, exact) and the same-database chunks table (pgvector)
  designs.py    the eight designs, the built one, and the exploratory ones
  replay.py     the month on a simulated clock: jobs take chunks x seconds per chunk; questions, audits, sync times
  embed.py      bge-small-en-v1.5 (fastembed) as LangChain Embeddings, with a cache and a charge per chunk
  answer.py     qwen3:8b on every distinct prompt (LangChain's classic RAG prompt, 4 chunks)
  realtime.py   poll, CDC, same database and built in real time: an edit every 10 s and a 300-save burst
  score.py      replies (current, stale, both, declined, other) and index entries (current, outdated, deleted, duplicate)
vectors/churn.py          Episode 2's adapters with upsert, delete and each database's clean-up
docker-compose.ep06.yml           the record (pgvector pg18, wal_level=logical), Weaviate 1.40.7, Ollama 0.40.11
docker-compose.ep06-stores.yml    Episode 2's six databases, images and limits
scripts/ep06_run.py       calibration, the replay of every design, the answers
scripts/ep06_stores.py    the six databases at one million: add again, update and delete visibility, churn, clean-up
scripts/ep06_summary.py   the tables
scripts/ep06_full.sh      the full run, one step after another
tests/test_ep06.py
```
