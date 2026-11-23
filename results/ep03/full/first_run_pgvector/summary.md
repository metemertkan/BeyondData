# Episode 3 results (full: 1,000,000 passages, 2,452 test questions)

## Exact search inside the filter (the ceiling)

| Condition | Median filter size | nDCG@10 | hit@10 |
| :--- | ---: | ---: | ---: |
| no filter | 1,000,000 | 0.7386 | 0.9152 |
| region 50% | 500,606 | 0.7758 | 0.9413 |
| dept 10% | 100,000 | 0.8502 | 0.9735 |
| team 1% | 10,004 | 0.9014 | 0.9959 |
| project 0.1% | 1,000 | 0.9185 | 0.9996 |
| topic ~1% | 10,277 | 0.7911 | 0.9466 |
| subtopic ~0.1% | 1,098 | 0.8145 | 0.9625 |

## Act 1: as shipped (fields stored the quickstart way, filter in the query, nothing else)

**Results returned (mean, of 10)**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 10.00 | 10.00 | 4.79 | 1.29 | 10.00 | 8.47 | 10.00 |

**Questions with fewer results than exist**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.0% | 0.0% | 99.2% | 100.0% | 0.0% | 25.5% | 0.0% |

**Questions with no results at all**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.0% | 0.0% | 0.1% | 6.5% | 0.0% | 3.4% | 0.0% |

**Recall@10 inside the filter**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.918 | 0.901 | 0.472 | 0.128 | 1.000 | 0.811 | 1.000 |

**nDCG@10**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.693 | 0.727 | 0.792 | 0.822 | 0.918 | 0.732 | 0.815 |
| exact | 0.739 | 0.776 | 0.850 | 0.901 | 0.918 | 0.791 | 0.815 |

**Answer lost (exact filtered search finds it, the database doesn't)**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 137 | 149 | 186 | 241 | 0 | 173 | 0 |

**p50 latency (ms)**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 4.28 | 4.34 | 4.4 | 4.37 | 39.88 | 4.35 | 42.97 |

\* sampled: the cell averaged over 250 ms on its first 100 questions and stopped there (pilot: at 300).

Results that didn't match the filter: {'pgvector': 0}.

**pgvector plans** (20 tuning questions per condition, default knob):

- default, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- default, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- default, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- default, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Parallel Seq Scan docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Parallel Seq Scan docs ×20; subtopic ~0.1%: Parallel Seq Scan docs ×20
- default, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Parallel Seq Scan docs ×20; dept 10%: Parallel Seq Scan docs ×20; team 1%: Parallel Seq Scan docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Parallel Seq Scan docs ×20; subtopic ~0.1%: Parallel Seq Scan docs ×20
- default, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×13, Parallel Seq Scan docs ×7; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Parallel Seq Scan docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Parallel Seq Scan docs ×20; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Parallel Seq Scan docs ×20; dept 10%: Parallel Seq Scan docs ×20; team 1%: Parallel Seq Scan docs ×20; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Parallel Seq Scan docs ×20; subtopic ~0.1%: Parallel Seq Scan docs ×20
- iterative, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1; project 0.1%: Parallel Seq Scan docs ×20; topic ~1%: Index Scan docs_embedding_idx docs ×13, Parallel Seq Scan docs ×7; subtopic ~0.1%: Parallel Seq Scan docs ×20
- btree, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Index Scan docs_embedding_idx docs ×16, Bitmap Index Scan docs_topic_idx ×4; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20
- btree, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Index Scan docs_embedding_idx docs ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Index Scan docs_embedding_idx docs ×13, Bitmap Index Scan docs_topic_idx ×7; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20
- btree, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Bitmap Index Scan docs_team_idx ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Bitmap Index Scan docs_topic_idx ×20; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20
- btree, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Bitmap Index Scan docs_dept_idx ×20; team 1%: Bitmap Index Scan docs_team_idx ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Bitmap Index Scan docs_topic_idx ×20; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20
- btree, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Parallel Seq Scan docs ×20; dept 10%: Bitmap Index Scan docs_dept_idx ×20; team 1%: Bitmap Index Scan docs_team_idx ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Bitmap Index Scan docs_topic_idx ×20; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20
- btree, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20; region 50%: Index Scan docs_embedding_idx docs ×20; dept 10%: Index Scan docs_embedding_idx docs ×20; team 1%: Bitmap Index Scan docs_team_idx ×20; project 0.1%: Bitmap Index Scan docs_project_idx ×20; topic ~1%: Bitmap Index Scan docs_topic_idx ×20; subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20

## Load, by deployment

| Database | Deployment | Load (s) | Index wait (s) | Settle (s) | Option applied (s) | Disk after load (GB) | Disk at end (GB) |
| :--- | :--- | ---: | ---: | ---: | :--- | ---: | ---: |
| pgvector | base | 32 | 3023 | 0 | btree: 2.1 | 14.92 | 14.96 |

## Act 2: the options (1,000 test questions every setting ran on; recall inside the filter / short results / p50 ms)

**pgvector**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.912 / 0% / 4.3 | 0.896 / 0% / 4.36 | 0.468 / 99% / 4.4 | 0.128 / 100% / 4.36 | 1.000 / 0% / 39.92 | 0.815 / 25% / 4.36 | 1.000 / 0% / 42.88 |
| default | 64 | 0.936 / 0% / 6.15 | 0.926 / 0% / 6.26 | 0.677 / 83% / 6.32 | 0.154 / 100% / 6.13 | 1.000 / 0% / 39.51 | 0.867 / 18% / 6.14 | 1.000 / 0% / 42.99 |
| default | 128 | 0.956 / 0% / 10.44 | 0.953 / 0% / 10.41 | 0.907 / 11% / 10.74 | 0.217 / 100% / 10.77 | 1.000 / 0% / 39.53 | 0.915 / 10% / 10.57 | 1.000 / 0% / 43.05 |
| default | 256 | 0.975 / 0% / 18.51 | 0.972 / 0% / 18.48 | 0.956 / 0% / 18.77 | 0.347 / 100% / 19.46 | 1.000 / 0% / 39.77 | 0.946 / 6% / 18.6 | 1.000 / 0% / 42.84 |
| default | 512 | 0.981 / 0% / 33.89 | 0.981 / 0% / 33.87 | 0.975 / 0% / 34.34 | 0.593 / 94% / 35.62 | 1.000 / 0% / 39.92 | 0.967 / 4% / 33.81 | 1.000 / 0% / 43.07 |
| default | 1000 | 0.987 / 0% / 60.39 | 0.988 / 0% / 60.7 | 0.986 / 0% / 60.9 | 0.891 / 33% / 63.76 | 1.000 / 0% / 40.03 | 0.979 / 2% / 60.45 | 1.000 / 0% / 43.16 |
| iterative | default | 0.912 / 0% / 4.4 | 0.896 / 0% / 4.5 | 0.904 / 0% / 9.45 | 0.939 / 0% / 57.64 | 1.000 / 0% / 39.6 | 0.927 / 0% / 4.77 | 1.000 / 0% / 42.6 |
| iterative | 64 | 0.936 / 0% / 6.28 | 0.926 / 0% / 6.28 | 0.913 / 0% / 10.67 | 0.940 / 0% / 57.7 | 1.000 / 0% / 39.61 | 0.943 / 0% / 6.54 | 1.000 / 0% / 42.61 |
| iterative | 128 | 0.956 / 0% / 10.67 | 0.953 / 0% / 10.77 | 0.923 / 0% / 11.45 | 0.942 / 0% / 59.73 | 1.000 / 0% / 39.48 | 0.958 / 0% / 10.99 | 1.000 / 0% / 42.91 |
| iterative | 256 | 0.975 / 0% / 19.05 | 0.972 / 0% / 18.85 | 0.956 / 0% / 19.14 | 0.947 / 0% / 62.68 | 1.000 / 0% / 39.51 | 0.968 / 0% / 19.39 | 1.000 / 0% / 42.52 |
| iterative | 512 | 0.981 / 0% / 34.43 | 0.981 / 0% / 34.55 | 0.975 / 0% / 34.65 | 0.954 / 0% / 71.2 | 1.000 / 0% / 39.6 | 0.978 / 0% / 34.6 | 1.000 / 0% / 42.55 |
| iterative | 1000 | 0.987 / 0% / 61.65 | 0.988 / 0% / 61.44 | 0.986 / 0% / 62.02 | 0.956 / 0% / 73.5 | 1.000 / 0% / 39.75 | 0.984 / 0% / 62.17 | 1.000 / 0% / 42.58 |
| btree | default | 0.912 / 0% / 4.37 | 0.896 / 0% / 4.44 | 0.904 / 0% / 9.55 | 0.939 / 0% / 57.13 | 1.000 / 0% / 15.6 | 0.927 / 0% / 4.82 | 1.000 / 0% / 16.86 |
| btree | 64 | 0.936 / 0% / 6.2 | 0.926 / 0% / 6.28 | 0.913 / 0% / 10.58 | 0.940 / 0% / 57.73 | 1.000 / 0% / 15.59 | 0.943 / 0% / 6.53 | 1.000 / 0% / 17.12 |
| btree | 128 | 0.956 / 0% / 10.69 | 0.953 / 0% / 10.73 | 0.923 / 0% / 11.41 | 0.942 / 0% / 59.55 | 1.000 / 0% / 15.76 | 0.958 / 0% / 10.98 | 1.000 / 0% / 17.19 |
| btree | 256 | 0.975 / 0% / 18.63 | 0.972 / 0% / 17.9 | 0.956 / 0% / 18.29 | 0.947 / 0% / 60.11 | 1.000 / 0% / 14.65 | 0.968 / 0% / 18.21 | 1.000 / 0% / 16.07 |
| btree | 512 | 0.981 / 0% / 32.44 | 0.981 / 0% / 32.48 | 0.975 / 0% / 32.9 | 0.954 / 0% / 67.03 | 1.000 / 0% / 14.74 | 0.978 / 0% / 32.92 | 1.000 / 0% / 16.03 |
| btree | 1000 | 0.987 / 0% / 60.13 | 0.988 / 0% / 61.44 | 0.986 / 0% / 62.15 | 0.956 / 0% / 74.01 | 1.000 / 0% / 15.79 | 0.984 / 0% / 62.21 | 1.000 / 0% / 17.17 |


## Act 3: built (target recall 0.99: the lowest target at which no setting on a random filter loses more than 0.5 nDCG points against exact filtered search, tuning questions)

Per database: the deployment, and per field the cheapest setting (tuning p50) with recall ≥ target and full results on tuning questions. Topical fields use the setting of the random field with the same selectivity.

| Database | Deployment | no filter | region 50% | dept 10% | team 1% | project 0.1% | Worst p50 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | ---: |
| pgvector | B-tree indexes | ✗ none | ✗ none | ✗ none | ✗ none | btree @ 256 (14.63 ms) | — |

**Built settings on the test questions** (1,000; recall / short / answer lost / p50 ms; topical fields held out)

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | ✗ | ✗ | ✗ | ✗ | 1.000 / 0% / 0 / 14.65 | ✗ | 1.000 / 0% / 0 / 16.07 |

**Deploy check** (200 test questions per field, seed 7: recall ≥ 0.99 and no short result)

| Database | no filter: default → built | region 50%: default → built | dept 10%: default → built | team 1%: default → built | project 0.1%: default → built |
| :--- | :---: | :---: | :---: | :---: | :---: |
| pgvector | FAIL → — | FAIL → — | FAIL → — | FAIL → — | pass → pass |
