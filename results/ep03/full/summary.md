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
| pgvector | 10.00 | 10.00 | 4.80 | 1.29 | 10.00 | 8.49 | 10.00 |
| qdrant | 10.00 | 10.00 | 10.00 | 9.96 | 10.00 | 10.00 | 10.00 |
| milvus | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| weaviate | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| elasticsearch | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| chroma | 10.00 | 10.00* | 10.00* | 10.00* | 10.00* | 10.00 | 10.00 |

**Questions with fewer results than exist**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.0% | 0.0% | 99.1% | 100.0% | 0.0% | 25.4% | 0.0% |
| qdrant | 0.0% | 0.0% | 0.0% | 0.9% | 0.0% | 0.0% | 0.0% |
| milvus | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| weaviate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| elasticsearch | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| chroma | 0.0% | 0.0%* | 0.0%* | 0.0%* | 0.0%* | 0.0% | 0.0% |

**Questions with no results at all**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.0% | 0.0% | 0.1% | 6.3% | 0.0% | 3.6% | 0.0% |
| qdrant | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| milvus | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| weaviate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| elasticsearch | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| chroma | 0.0% | 0.0%* | 0.0%* | 0.0%* | 0.0%* | 0.0% | 0.0% |

**Recall@10 inside the filter**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.921 | 0.905 | 0.473 | 0.129 | 1.000 | 0.814 | 1.000 |
| qdrant | 0.970 | 0.937 | 0.345 | 0.574 | 0.998 | 0.990 | 1.000 |
| milvus | 0.909 | 0.875 | 0.953 | 1.000 | 1.000 | 1.000 | 1.000 |
| weaviate | 0.978 | 0.984 | 0.957 | 1.000 | 1.000 | 1.000 | 1.000 |
| elasticsearch | 0.901 | 0.880 | 0.857 | 0.550 | 0.973 | 0.943 | 0.965 |
| chroma | 0.959 | 0.972* | 0.989* | 0.997* | 1.000* | 0.990 | 0.999 |

**nDCG@10**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.697 | 0.731 | 0.796 | 0.827 | 0.918 | 0.735 | 0.815 |
| qdrant | 0.727 | 0.753 | 0.314 | 0.524 | 0.916 | 0.784 | 0.815 |
| milvus | 0.704 | 0.724 | 0.834 | 0.901 | 0.918 | 0.791 | 0.815 |
| weaviate | 0.731 | 0.770 | 0.833 | 0.901 | 0.918 | 0.791 | 0.815 |
| elasticsearch | 0.703 | 0.727 | 0.777 | 0.542 | 0.918 | 0.780 | 0.814 |
| chroma | 0.721 | 0.758* | 0.848* | 0.887* | 0.904* | 0.787 | 0.814 |
| exact | 0.739 | 0.776 | 0.850 | 0.901 | 0.918 | 0.791 | 0.815 |

**Answer lost (exact filtered search finds it, the database doesn't)**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 125 | 136 | 174 | 229 | 0 | 162 | 0 |
| qdrant | 38 | 77 | 1525 | 1037 | 6 | 19 | 0 |
| milvus | 107 | 170 | 54 | 0 | 0 | 0 | 0 |
| weaviate | 23 | 19 | 54 | 0 | 0 | 0 | 0 |
| elasticsearch | 109 | 150 | 216 | 970 | 0 | 33 | 3 |
| chroma | 51 | 2* | 0* | 0* | 0* | 10 | 2 |

**p50 latency (ms)**

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 4.35 | 4.37 | 4.39 | 4.31 | 39.32 | 4.34 | 42.14 |
| qdrant | 4.52 | 6.29 | 7.5 | 174.78 | 199.83 | 166.49 | 195.39 |
| milvus | 1.95 | 3.35 | 4.0 | 4.7 | 3.57 | 4.77 | 3.54 |
| weaviate | 2.7 | 4.38 | 6.72 | 9.87 | 1.55 | 10.23 | 1.66 |
| elasticsearch | 3.02 | 2.91 | 2.85 | 3.07 | 2.94 | 2.85 | 2.85 |
| chroma | 2.51 | 1628.78* | 505.36* | 275.77* | 570.38* | 227.5 | 166.26 |

\* sampled: the cell averaged over 250 ms on its first 100 questions and stopped there (pilot: at 300).

Results that didn't match the filter: {'pgvector': 0, 'qdrant': 0, 'milvus': 0, 'weaviate': 0, 'elasticsearch': 0, 'chroma': 0}.

**pgvector plans**: EXPLAIN (planned afresh, 20 tuning questions per condition) → the plan the cell's prepared statement ran with (EXPLAIN EXECUTE, first tuning question; amendment 4), generic/custom plans:

- default, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (3493/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (3493/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/3498)
- default, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- default, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- default, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- default, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (141/5); dept 10%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (141/5); team 1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- default, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×18, Parallel Seq Scan docs ×2 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×12, Parallel Seq Scan docs ×8 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- iterative, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (3493/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (3493/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/3498)
- iterative, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- iterative, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×19, Parallel Seq Scan docs ×1 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- iterative, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- iterative, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (141/5); dept 10%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (141/5); team 1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- iterative, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×18, Parallel Seq Scan docs ×2 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×12, Parallel Seq Scan docs ×8 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (0/2046)
- btree, ef_search default: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); team 1%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (3493/5); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (3493/5); topic ~1%: Index Scan docs_embedding_idx docs ×18, Bitmap Index Scan docs_topic_idx ×2 → ran Index Scan docs_embedding_idx docs (3493/5); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (3492/6)
- btree, ef_search 64: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Index Scan docs_embedding_idx docs ×19, Bitmap Index Scan docs_team_idx ×1 → ran Index Scan docs_embedding_idx docs (2041/5); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (2041/5); topic ~1%: Index Scan docs_embedding_idx docs ×13, Bitmap Index Scan docs_topic_idx ×7 → ran Index Scan docs_embedding_idx docs (2041/5); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (2040/6)
- btree, ef_search 128: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Bitmap Index Scan docs_team_idx ×20 → ran Bitmap Index Scan docs_team_idx (2038/8); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (2041/5); topic ~1%: Bitmap Index Scan docs_topic_idx ×20 → ran Bitmap Index Scan docs_topic_idx (0/2046); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (2040/6)
- btree, ef_search 256: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Bitmap Index Scan docs_dept_idx ×20 → ran Bitmap Index Scan docs_dept_idx (141/5); team 1%: Bitmap Index Scan docs_team_idx ×20 → ran Bitmap Index Scan docs_team_idx (2038/8); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (2041/5); topic ~1%: Bitmap Index Scan docs_topic_idx ×20 → ran Bitmap Index Scan docs_topic_idx (0/2046); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (2040/6)
- btree, ef_search 512: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Parallel Seq Scan docs ×20 → ran Parallel Seq Scan docs (141/5); dept 10%: Bitmap Index Scan docs_dept_idx ×20 → ran Bitmap Index Scan docs_dept_idx (141/5); team 1%: Bitmap Index Scan docs_team_idx ×20 → ran Bitmap Index Scan docs_team_idx (2038/8); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (2041/5); topic ~1%: Bitmap Index Scan docs_topic_idx ×20 → ran Bitmap Index Scan docs_topic_idx (0/2046); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (2040/6)
- btree, ef_search 1000: no filter: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); region 50%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); dept 10%: Index Scan docs_embedding_idx docs ×20 → ran Index Scan docs_embedding_idx docs (2041/5); team 1%: Bitmap Index Scan docs_team_idx ×20 → ran Bitmap Index Scan docs_team_idx (2038/8); project 0.1%: Bitmap Index Scan docs_project_idx ×20 → ran Bitmap Index Scan docs_project_idx (2041/5); topic ~1%: Bitmap Index Scan docs_topic_idx ×20 → ran Bitmap Index Scan docs_topic_idx (0/2046); subtopic ~0.1%: Bitmap Index Scan docs_subtopic_idx ×20 → ran Bitmap Index Scan docs_subtopic_idx (2040/6)

**pgvector plan-cache check** (amendment 4: the same 100 tuning questions filtered on team, one connection)

| Step | ef_search | EXPLAIN shows | Statement ran with | Generic / custom plans | Returned (mean) | Short | Recall | p50 ms |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| a_shipped  | 40 | Index Scan docs_embedding_idx docs | Index Scan docs_embedding_idx docs | 91 / 5 | 1.41 | 100% | 0.141 | 4.65 |
| b_set (SET hnsw.ef_search = 256) | 256 | Parallel Seq Scan docs | Index Scan docs_embedding_idx docs | 192 / 5 | 4.04 | 100% | 0.404 | 19.23 |
| c_deallocate (DEALLOCATE ALL) | 256 | Parallel Seq Scan docs | Parallel Seq Scan docs | 91 / 5 | 10.00 | 0% | 0.999 | 85.89 |

**pgvector, same setting, two plans** (recall / short / p50 ms on 1,000 test questions): first run (statements kept the plan made at ef_search 40) → re-run (a connection per setting)

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| default | 64 | 0.936 / 0% / 6.15 → 0.941 / 0% / 6.07 | 0.926 / 0% / 6.26 → 0.931 / 0% / 6.12 | 0.677 / 83% / 6.32 → 0.677 / 83% / 6.32 | 0.154 / 100% / 6.13 → 0.155 / 100% / 6.24 | 1.000 / 0% / 39.51 → 1.000 / 0% / 39.46 | 0.867 / 18% / 6.14 → 0.873 / 18% / 6.17 | 1.000 / 0% / 42.99 → 1.000 / 0% / 42.37 |
| default | 128 | 0.956 / 0% / 10.44 → 0.959 / 0% / 10.52 | 0.953 / 0% / 10.41 → 0.954 / 0% / 10.47 | 0.907 / 11% / 10.74 → 0.907 / 11% / 10.76 | 0.217 / 100% / 10.77 → 0.219 / 100% / 10.85 | 1.000 / 0% / 39.53 → 1.000 / 0% / 39.34 | 0.915 / 10% / 10.57 → 0.919 / 10% / 10.64 | 1.000 / 0% / 43.05 → 1.000 / 0% / 42.06 |
| default | 256 | 0.975 / 0% / 18.51 → 0.975 / 0% / 18.33 | 0.972 / 0% / 18.48 → 0.972 / 0% / 18.46 | 0.956 / 0% / 18.77 → 0.956 / 0% / 18.69 | 0.347 / 100% / 19.46 → 1.000 / 0% / 85.73 | 1.000 / 0% / 39.77 → 1.000 / 0% / 39.2 | 0.946 / 6% / 18.6 → 1.000 / 0% / 88.47 | 1.000 / 0% / 42.84 → 1.000 / 0% / 42.35 |
| default | 512 | 0.981 / 0% / 33.89 → 0.981 / 0% / 33.95 | 0.981 / 0% / 33.87 → 1.000 / 0% / 1427.64* | 0.975 / 0% / 34.34 → 1.000 / 0% / 402.05* | 0.593 / 94% / 35.62 → 1.000 / 0% / 86.11 | 1.000 / 0% / 39.92 → 1.000 / 0% / 39.11 | 0.967 / 4% / 33.81 → 1.000 / 0% / 88.38 | 1.000 / 0% / 43.07 → 1.000 / 0% / 42.44 |
| default | 1000 | 0.987 / 0% / 60.39 → 0.988 / 0% / 60.8 | 0.988 / 0% / 60.7 → 0.988 / 0% / 60.89 | 0.986 / 0% / 60.9 → 0.985 / 0% / 61.18 | 0.891 / 33% / 63.76 → 0.891 / 34% / 63.61 | 1.000 / 0% / 40.03 → 1.000 / 0% / 39.85 | 0.979 / 2% / 60.45 → 0.979 / 2% / 61.06 | 1.000 / 0% / 43.16 → 1.000 / 0% / 42.48 |
| iterative | 64 | 0.936 / 0% / 6.28 → 0.941 / 0% / 6.37 | 0.926 / 0% / 6.28 → 0.931 / 0% / 6.42 | 0.913 / 0% / 10.67 → 0.915 / 0% / 11.08 | 0.940 / 0% / 57.7 → 0.940 / 0% / 59.33 | 1.000 / 0% / 39.61 → 1.000 / 0% / 39.64 | 0.943 / 0% / 6.54 → 0.944 / 0% / 6.6 | 1.000 / 0% / 42.61 → 1.000 / 0% / 42.47 |
| iterative | 128 | 0.956 / 0% / 10.67 → 0.959 / 0% / 10.99 | 0.953 / 0% / 10.77 → 0.954 / 0% / 10.94 | 0.923 / 0% / 11.45 → 0.925 / 0% / 11.8 | 0.942 / 0% / 59.73 → 0.943 / 0% / 61.15 | 1.000 / 0% / 39.48 → 1.000 / 0% / 39.75 | 0.958 / 0% / 10.99 → 0.958 / 0% / 11.26 | 1.000 / 0% / 42.91 → 1.000 / 0% / 42.6 |
| iterative | 256 | 0.975 / 0% / 19.05 → 0.975 / 0% / 19.31 | 0.972 / 0% / 18.85 → 0.972 / 0% / 19.48 | 0.956 / 0% / 19.14 → 0.956 / 0% / 19.78 | 0.947 / 0% / 62.68 → 1.000 / 0% / 85.95 | 1.000 / 0% / 39.51 → 1.000 / 0% / 39.39 | 0.968 / 0% / 19.39 → 1.000 / 0% / 88.54 | 1.000 / 0% / 42.52 → 1.000 / 0% / 42.33 |
| iterative | 512 | 0.981 / 0% / 34.43 → 0.981 / 0% / 35.3 | 0.981 / 0% / 34.55 → 1.000 / 0% / 1440.57* | 0.975 / 0% / 34.65 → 1.000 / 0% / 403.48* | 0.954 / 0% / 71.2 → 1.000 / 0% / 85.62 | 1.000 / 0% / 39.6 → 1.000 / 0% / 39.41 | 0.978 / 0% / 34.6 → 1.000 / 0% / 87.99 | 1.000 / 0% / 42.55 → 1.000 / 0% / 42.37 |
| iterative | 1000 | 0.987 / 0% / 61.65 → 0.988 / 0% / 63.1 | 0.988 / 0% / 61.44 → 0.988 / 0% / 63.4 | 0.986 / 0% / 62.02 → 0.985 / 0% / 64.33 | 0.956 / 0% / 73.5 → 0.957 / 0% / 75.52 | 1.000 / 0% / 39.75 → 1.000 / 0% / 39.83 | 0.984 / 0% / 62.17 → 0.984 / 0% / 63.89 | 1.000 / 0% / 42.58 → 1.000 / 0% / 42.3 |
| btree | 64 | 0.936 / 0% / 6.2 → 0.941 / 0% / 6.35 | 0.926 / 0% / 6.28 → 0.931 / 0% / 6.36 | 0.913 / 0% / 10.58 → 0.915 / 0% / 11.01 | 0.940 / 0% / 57.73 → 0.940 / 0% / 59.04 | 1.000 / 0% / 15.59 → 1.000 / 0% / 15.63 | 0.943 / 0% / 6.53 → 0.944 / 0% / 6.64 | 1.000 / 0% / 17.12 → 1.000 / 0% / 17.2 |
| btree | 128 | 0.956 / 0% / 10.69 → 0.959 / 0% / 10.96 | 0.953 / 0% / 10.73 → 0.954 / 0% / 10.98 | 0.923 / 0% / 11.41 → 0.925 / 0% / 11.81 | 0.942 / 0% / 59.55 → 1.000 / 0% / 131.17 | 1.000 / 0% / 15.76 → 1.000 / 0% / 15.74 | 0.958 / 0% / 10.98 → 1.000 / 0% / 135.64 | 1.000 / 0% / 17.19 → 1.000 / 0% / 16.86 |
| btree | 256 | 0.975 / 0% / 18.63 → 0.975 / 0% / 19.36 | 0.972 / 0% / 17.9 → 0.972 / 0% / 19.48 | 0.956 / 0% / 18.29 → 1.000 / 0% / 383.11* | 0.947 / 0% / 60.11 → 1.000 / 0% / 132.27 | 1.000 / 0% / 14.65 → 1.000 / 0% / 15.86 | 0.968 / 0% / 18.21 → 1.000 / 0% / 134.0 | 1.000 / 0% / 16.07 → 1.000 / 0% / 16.99 |
| btree | 512 | 0.981 / 0% / 32.44 → 0.981 / 0% / 35.57 | 0.981 / 0% / 32.48 → 1.000 / 0% / 1433.82* | 0.975 / 0% / 32.9 → 1.000 / 0% / 391.67* | 0.954 / 0% / 67.03 → 1.000 / 0% / 131.93 | 1.000 / 0% / 14.74 → 1.000 / 0% / 15.91 | 0.978 / 0% / 32.92 → 1.000 / 0% / 135.4 | 1.000 / 0% / 16.03 → 1.000 / 0% / 17.04 |
| btree | 1000 | 0.987 / 0% / 60.13 → 0.988 / 0% / 64.42 | 0.988 / 0% / 61.44 → 0.988 / 0% / 63.88 | 0.986 / 0% / 62.15 → 0.985 / 0% / 61.93 | 0.956 / 0% / 74.01 → 1.000 / 0% / 131.66 | 1.000 / 0% / 15.79 → 1.000 / 0% / 15.61 | 0.984 / 0% / 62.21 → 1.000 / 0% / 135.97 | 1.000 / 0% / 17.17 → 1.000 / 0% / 17.2 |

Default-knob cells, first run vs re-run (21 cells, all test questions): largest recall difference +0.004 (default__region); largest difference in results returned 0.01.

## Load, by deployment

| Database | Deployment | Load (s) | Index wait (s) | Settle (s) | Option applied (s) | Disk after load (GB) | Disk at end (GB) |
| :--- | :--- | ---: | ---: | ---: | :--- | ---: | ---: |
| pgvector | base | 32 | 3002 | 0 | btree: 2.2 | 14.92 | 14.96 |
| qdrant | noindex | 547 | 40 | 0 | index_later: 27.2 | 4.50 | 5.02 |
| qdrant | index_first | 586 | 531 | 0 |  | 5.24 | 5.24 |
| milvus | dynamic | 142 | 310 | 230 |  | 22.98 | 22.98 |
| milvus | schema | 145 | 298 | 230 | schema_index: 7.6 | 22.35 | 22.43 |
| weaviate | base | 992 | 0 | 0 | sweeping: 2.0; pathseer: 2.0 | 4.70 | 4.69 |
| elasticsearch | base | 1560 | 128 | 0 |  | 5.90 | 4.35 |
| chroma | base | 1282 | 0 | 0 |  | 4.80 | 4.80 |

## Act 2: the options (1,000 test questions every setting ran on; recall inside the filter / short results / p50 ms)

**pgvector**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.920 / 0% / 4.36 | 0.904 / 0% / 4.38 | 0.471 / 99% / 4.45 | 0.130 / 100% / 4.31 | 1.000 / 0% / 39.32 | 0.826 / 24% / 4.38 | 1.000 / 0% / 42.11 |
| default | 64 | 0.941 / 0% / 6.07 | 0.931 / 0% / 6.12 | 0.677 / 83% / 6.32 | 0.155 / 100% / 6.24 | 1.000 / 0% / 39.46 | 0.873 / 18% / 6.17 | 1.000 / 0% / 42.37 |
| default | 128 | 0.959 / 0% / 10.52 | 0.954 / 0% / 10.47 | 0.907 / 11% / 10.76 | 0.219 / 100% / 10.85 | 1.000 / 0% / 39.34 | 0.919 / 10% / 10.64 | 1.000 / 0% / 42.06 |
| default | 256 | 0.975 / 0% / 18.33 | 0.972 / 0% / 18.46 | 0.956 / 0% / 18.69 | 1.000 / 0% / 85.73 | 1.000 / 0% / 39.2 | 1.000 / 0% / 88.47 | 1.000 / 0% / 42.35 |
| default | 512 | 0.981 / 0% / 33.95 | 1.000 / 0% / 1427.64* | 1.000 / 0% / 402.05* | 1.000 / 0% / 86.11 | 1.000 / 0% / 39.11 | 1.000 / 0% / 88.38 | 1.000 / 0% / 42.44 |
| default | 1000 | 0.988 / 0% / 60.8 | 0.988 / 0% / 60.89 | 0.985 / 0% / 61.18 | 0.891 / 34% / 63.61 | 1.000 / 0% / 39.85 | 0.979 / 2% / 61.06 | 1.000 / 0% / 42.48 |
| iterative | default | 0.920 / 0% / 4.41 | 0.905 / 0% / 4.54 | 0.906 / 0% / 9.85 | 0.940 / 0% / 58.25 | 1.000 / 0% / 39.77 | 0.931 / 0% / 4.94 | 1.000 / 0% / 42.63 |
| iterative | 64 | 0.941 / 0% / 6.37 | 0.931 / 0% / 6.42 | 0.915 / 0% / 11.08 | 0.940 / 0% / 59.33 | 1.000 / 0% / 39.64 | 0.944 / 0% / 6.6 | 1.000 / 0% / 42.47 |
| iterative | 128 | 0.959 / 0% / 10.99 | 0.954 / 0% / 10.94 | 0.925 / 0% / 11.8 | 0.943 / 0% / 61.15 | 1.000 / 0% / 39.75 | 0.958 / 0% / 11.26 | 1.000 / 0% / 42.6 |
| iterative | 256 | 0.975 / 0% / 19.31 | 0.972 / 0% / 19.48 | 0.956 / 0% / 19.78 | 1.000 / 0% / 85.95 | 1.000 / 0% / 39.39 | 1.000 / 0% / 88.54 | 1.000 / 0% / 42.33 |
| iterative | 512 | 0.981 / 0% / 35.3 | 1.000 / 0% / 1440.57* | 1.000 / 0% / 403.48* | 1.000 / 0% / 85.62 | 1.000 / 0% / 39.41 | 1.000 / 0% / 87.99 | 1.000 / 0% / 42.37 |
| iterative | 1000 | 0.988 / 0% / 63.1 | 0.988 / 0% / 63.4 | 0.985 / 0% / 64.33 | 0.957 / 0% / 75.52 | 1.000 / 0% / 39.83 | 0.984 / 0% / 63.89 | 1.000 / 0% / 42.3 |
| btree | default | 0.920 / 0% / 4.4 | 0.905 / 0% / 4.43 | 0.906 / 0% / 9.79 | 0.940 / 0% / 58.61 | 1.000 / 0% / 15.71 | 0.931 / 0% / 4.89 | 1.000 / 0% / 16.92 |
| btree | 64 | 0.941 / 0% / 6.35 | 0.931 / 0% / 6.36 | 0.915 / 0% / 11.01 | 0.940 / 0% / 59.04 | 1.000 / 0% / 15.63 | 0.944 / 0% / 6.64 | 1.000 / 0% / 17.2 |
| btree | 128 | 0.959 / 0% / 10.96 | 0.954 / 0% / 10.98 | 0.925 / 0% / 11.81 | 1.000 / 0% / 131.17 | 1.000 / 0% / 15.74 | 1.000 / 0% / 135.64 | 1.000 / 0% / 16.86 |
| btree | 256 | 0.975 / 0% / 19.36 | 0.972 / 0% / 19.48 | 1.000 / 0% / 383.11* | 1.000 / 0% / 132.27 | 1.000 / 0% / 15.86 | 1.000 / 0% / 134.0 | 1.000 / 0% / 16.99 |
| btree | 512 | 0.981 / 0% / 35.57 | 1.000 / 0% / 1433.82* | 1.000 / 0% / 391.67* | 1.000 / 0% / 131.93 | 1.000 / 0% / 15.91 | 1.000 / 0% / 135.4 | 1.000 / 0% / 17.04 |
| btree | 1000 | 0.988 / 0% / 64.42 | 0.988 / 0% / 63.88 | 0.985 / 0% / 61.93 | 1.000 / 0% / 131.66 | 1.000 / 0% / 15.61 | 1.000 / 0% / 135.97 | 1.000 / 0% / 17.2 |

**qdrant**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.967 / 0% / 4.5 | 0.934 / 0% / 6.29 | 0.342 / 0% / 7.48 | 0.583 / 1% / 175.28 | 0.998 / 0% / 200.92 | 0.990 / 0% / 166.44 | 1.000 / 0% / 194.16 |
| default | 64 | 0.953 / 0% / 3.35 | 0.907 / 0% / 5.06 | 0.271 / 0% / 5.94 | 0.583 / 1% / 175.57 | 0.998 / 0% / 197.42 | 0.984 / 0% / 171.82 | 1.000 / 0% / 196.3 |
| default | 128 | 0.972 / 0% / 4.77 | 0.944 / 0% / 7.44 | 0.383 / 0% / 8.35 | 0.583 / 1% / 174.96 | 0.999 / 0% / 196.24 | 0.992 / 0% / 171.86 | 1.000 / 0% / 198.88 |
| default | 256 | 0.984 / 0% / 7.0 | 0.969 / 0% / 11.0 | 0.482 / 0% / 12.48 | 0.583 / 1% / 175.39 | 0.999 / 0% / 196.25 | 0.996 / 0% / 171.84 | 1.000 / 0% / 194.27 |
| default | 512 | 0.991 / 0% / 10.85 | 0.982 / 0% / 18.6 | 0.563 / 0% / 19.91 | 0.583 / 1% / 175.19 | 0.999 / 0% / 196.95 | 0.998 / 0% / 173.22 | 1.000 / 0% / 195.05 |
| default | 1024 | 0.995 / 0% / 17.62 | 0.991 / 0% / 32.31 | 0.616 / 0% / 34.58 | 0.583 / 1% / 175.4 | 0.999 / 0% / 198.03 | 0.999 / 0% / 173.78 | 1.000 / 0% / 194.53 |
| index_later | default | 0.967 / 0% / 4.22 | 0.934 / 0% / 3.06 | 0.342 / 0% / 1.92 | 1.000 / 0% / 4.5 | 1.000 / 0% / 1.45 | 0.995 / 0% / 4.2 | 1.000 / 0% / 1.52 |
| index_later | 64 | 0.953 / 0% / 3.32 | 0.907 / 0% / 2.52 | 0.271 / 0% / 1.76 | 1.000 / 0% / 4.57 | 1.000 / 0% / 1.46 | 0.992 / 0% / 4.23 | 1.000 / 0% / 1.51 |
| index_later | 128 | 0.972 / 0% / 4.75 | 0.944 / 0% / 3.67 | 0.383 / 0% / 2.22 | 1.000 / 0% / 4.5 | 1.000 / 0% / 1.48 | 0.996 / 0% / 4.26 | 1.000 / 0% / 1.51 |
| index_later | 256 | 0.984 / 0% / 7.07 | 0.969 / 0% / 5.08 | 0.482 / 0% / 2.94 | 1.000 / 0% / 4.56 | 1.000 / 0% / 1.49 | 0.998 / 0% / 4.4 | 1.000 / 0% / 1.53 |
| index_later | 512 | 0.991 / 0% / 10.7 | 0.982 / 0% / 7.55 | 0.563 / 0% / 4.11 | 1.000 / 0% / 4.56 | 1.000 / 0% / 1.49 | 0.999 / 0% / 4.72 | 1.000 / 0% / 1.54 |
| index_later | 1024 | 0.995 / 0% / 17.35 | 0.991 / 0% / 12.02 | 0.616 / 0% / 6.14 | 1.000 / 0% / 4.52 | 1.000 / 0% / 1.51 | 1.000 / 0% / 4.73 | 1.000 / 0% / 1.54 |
| index_first | default | 0.978 / 0% / 6.71 | 0.980 / 0% / 6.78 | 0.995 / 0% / 6.4 | 1.000 / 0% / 4.44 | 1.000 / 0% / 1.51 | 0.999 / 0% / 4.57 | 1.000 / 0% / 1.55 |
| index_first | 64 | 0.968 / 0% / 4.75 | 0.967 / 0% / 5.16 | 0.987 / 0% / 4.81 | 0.999 / 0% / 4.03 | 1.000 / 0% / 1.5 | 0.997 / 0% / 4.14 | 1.000 / 0% / 1.58 |
| index_first | 128 | 0.983 / 0% / 7.58 | 0.984 / 0% / 7.96 | 0.997 / 0% / 7.28 | 1.000 / 0% / 4.7 | 1.000 / 0% / 1.49 | 0.999 / 0% / 4.84 | 1.000 / 0% / 1.57 |
| index_first | 256 | 0.991 / 0% / 12.87 | 0.993 / 0% / 13.32 | 0.999 / 0% / 11.35 | 1.000 / 0% / 5.72 | 1.000 / 0% / 1.51 | 1.000 / 0% / 5.9 | 1.000 / 0% / 1.55 |
| index_first | 512 | 0.996 / 0% / 23.15 | 0.997 / 0% / 23.67 | 1.000 / 0% / 17.06 | 1.000 / 0% / 7.21 | 1.000 / 0% / 1.5 | 1.000 / 0% / 7.32 | 1.000 / 0% / 1.53 |
| index_first | 1024 | 0.999 / 0% / 42.72 | 0.999 / 0% / 41.38 | 1.000 / 0% / 24.37 | 1.000 / 0% / 9.28 | 1.000 / 0% / 1.51 | 1.000 / 0% / 9.31 | 1.000 / 0% / 1.57 |
| acorn | default | 0.978 / 0% / 6.33 | 0.980 / 0% / 6.71 | 1.000 / 0% / 27.51 | 1.000 / 0% / 21.89 | 1.000 / 0% / 1.52 | 1.000 / 0% / 20.33 | 1.000 / 0% / 1.55 |
| acorn | 64 | 0.968 / 0% / 4.78 | 0.967 / 0% / 5.16 | 0.999 / 0% / 20.6 | 1.000 / 0% / 18.12 | 1.000 / 0% / 1.51 | 1.000 / 0% / 17.2 | 1.000 / 0% / 1.59 |
| acorn | 128 | 0.983 / 0% / 7.51 | 0.984 / 0% / 7.94 | 1.000 / 0% / 32.22 | 1.000 / 0% / 24.32 | 1.000 / 0% / 1.52 | 1.000 / 0% / 22.48 | 1.000 / 0% / 1.57 |
| acorn | 256 | 0.991 / 0% / 12.91 | 0.993 / 0% / 13.63 | 1.000 / 0% / 47.89 | 1.000 / 0% / 35.03 | 1.000 / 0% / 1.51 | 1.000 / 0% / 29.75 | 1.000 / 0% / 1.55 |
| acorn | 512 | 0.996 / 0% / 23.02 | 0.997 / 0% / 23.43 | 1.000 / 0% / 67.99 | 1.000 / 0% / 52.41 | 1.000 / 0% / 1.52 | 1.000 / 0% / 41.74 | 1.000 / 0% / 1.53 |
| acorn | 1024 | 0.999 / 0% / 42.66 | 0.999 / 0% / 41.4 | 1.000 / 0% / 92.74 | 1.000 / 0% / 78.59 | 1.000 / 0% / 1.51 | 1.000 / 0% / 62.01 | 1.000 / 0% / 1.55 |

**milvus**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.905 / 0% / 1.96 | 0.870 / 0% / 3.37 | 0.953 / 0% / 3.99 | 1.000 / 0% / 4.7 | 1.000 / 0% / 3.58 | 1.000 / 0% / 4.75 | 1.000 / 0% / 3.52 |
| default | 64 | 0.975 / 0% / 2.9 | 0.966 / 0% / 4.12 | 0.993 / 0% / 5.76 | 1.000 / 0% / 4.83 | 1.000 / 0% / 3.67 | 1.000 / 0% / 4.9 | 1.000 / 0% / 3.6 |
| default | 128 | 0.986 / 0% / 3.91 | 0.983 / 0% / 4.95 | 0.997 / 0% / 7.34 | 1.000 / 0% / 4.97 | 1.000 / 0% / 3.78 | 1.000 / 0% / 5.1 | 1.000 / 0% / 3.79 |
| default | 256 | 0.993 / 0% / 5.38 | 0.992 / 0% / 6.19 | 0.999 / 0% / 10.02 | 1.000 / 0% / 5.27 | 1.000 / 0% / 3.91 | 1.000 / 0% / 5.28 | 1.000 / 0% / 3.95 |
| default | 512 | 0.996 / 0% / 7.48 | 0.996 / 0% / 8.1 | 1.000 / 0% / 14.2 | 1.000 / 0% / 5.63 | 1.000 / 0% / 3.9 | 1.000 / 0% / 5.73 | 1.000 / 0% / 3.93 |
| default | 1024 | 0.998 / 0% / 10.69 | 0.998 / 0% / 11.37 | 1.000 / 0% / 22.0 | 1.000 / 0% / 6.31 | 1.000 / 0% / 3.92 | 1.000 / 0% / 6.34 | 1.000 / 0% / 3.9 |
| schema | default | 0.903 / 0% / 1.84 | 0.863 / 0% / 2.65 | 0.947 / 0% / 3.23 | 1.000 / 0% / 4.12 | 1.000 / 0% / 2.85 | 1.000 / 0% / 4.3 | 1.000 / 0% / 2.86 |
| schema | 64 | 0.973 / 0% / 2.62 | 0.960 / 0% / 3.5 | 0.989 / 0% / 5.12 | 1.000 / 0% / 4.34 | 1.000 / 0% / 3.0 | 1.000 / 0% / 4.36 | 1.000 / 0% / 3.01 |
| schema | 128 | 0.984 / 0% / 3.52 | 0.979 / 0% / 4.34 | 0.995 / 0% / 6.71 | 1.000 / 0% / 4.43 | 1.000 / 0% / 3.07 | 1.000 / 0% / 4.49 | 1.000 / 0% / 3.03 |
| schema | 256 | 0.992 / 0% / 5.01 | 0.990 / 0% / 5.56 | 0.998 / 0% / 9.04 | 1.000 / 0% / 4.72 | 1.000 / 0% / 3.08 | 1.000 / 0% / 4.7 | 1.000 / 0% / 3.18 |
| schema | 512 | 0.997 / 0% / 6.87 | 0.995 / 0% / 7.39 | 0.999 / 0% / 12.91 | 1.000 / 0% / 4.94 | 1.000 / 0% / 3.27 | 1.000 / 0% / 5.07 | 1.000 / 0% / 3.24 |
| schema | 1024 | 0.998 / 0% / 9.8 | 0.997 / 0% / 10.29 | 1.000 / 0% / 19.92 | 1.000 / 0% / 5.57 | 1.000 / 0% / 3.28 | 1.000 / 0% / 5.65 | 1.000 / 0% / 3.24 |
| schema_index | default | 0.903 / 0% / 1.82 | 0.863 / 0% / 1.91 | 0.947 / 0% / 2.5 | 1.000 / 0% / 3.33 | 1.000 / 0% / 2.1 | 1.000 / 0% / 3.42 | 1.000 / 0% / 2.13 |
| schema_index | 64 | 0.973 / 0% / 2.69 | 0.960 / 0% / 2.78 | 0.989 / 0% / 4.53 | 1.000 / 0% / 3.46 | 1.000 / 0% / 2.19 | 1.000 / 0% / 3.53 | 1.000 / 0% / 2.28 |
| schema_index | 128 | 0.984 / 0% / 3.57 | 0.979 / 0% / 3.58 | 0.995 / 0% / 6.25 | 1.000 / 0% / 3.61 | 1.000 / 0% / 2.37 | 1.000 / 0% / 3.73 | 1.000 / 0% / 2.28 |
| schema_index | 256 | 0.992 / 0% / 5.0 | 0.990 / 0% / 5.06 | 0.998 / 0% / 8.64 | 1.000 / 0% / 3.81 | 1.000 / 0% / 2.45 | 1.000 / 0% / 3.92 | 1.000 / 0% / 2.45 |
| schema_index | 512 | 0.997 / 0% / 6.86 | 0.995 / 0% / 6.92 | 0.999 / 0% / 12.5 | 1.000 / 0% / 4.24 | 1.000 / 0% / 2.42 | 1.000 / 0% / 4.36 | 1.000 / 0% / 2.49 |
| schema_index | 1024 | 0.998 / 0% / 9.91 | 0.997 / 0% / 9.85 | 1.000 / 0% / 19.49 | 1.000 / 0% / 4.95 | 1.000 / 0% / 2.45 | 1.000 / 0% / 5.08 | 1.000 / 0% / 2.53 |

**weaviate**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.977 / 0% / 2.71 | 0.984 / 0% / 4.36 | 0.958 / 0% / 6.69 | 1.000 / 0% / 9.86 | 1.000 / 0% / 1.55 | 1.000 / 0% / 10.2 | 1.000 / 0% / 1.64 |
| default | 64 | 0.968 / 0% / 2.03 | 0.976 / 0% / 3.19 | 0.942 / 0% / 4.93 | 1.000 / 0% / 9.85 | 1.000 / 0% / 1.54 | 1.000 / 0% / 10.19 | 1.000 / 0% / 1.64 |
| default | 128 | 0.982 / 0% / 3.16 | 0.986 / 0% / 5.23 | 0.965 / 0% / 7.61 | 1.000 / 0% / 9.87 | 1.000 / 0% / 1.54 | 1.000 / 0% / 10.22 | 1.000 / 0% / 1.64 |
| default | 256 | 0.988 / 0% / 5.02 | 0.991 / 0% / 8.37 | 0.979 / 0% / 11.9 | 1.000 / 0% / 9.86 | 1.000 / 0% / 1.54 | 1.000 / 0% / 10.19 | 1.000 / 0% / 1.71 |
| default | 512 | 0.992 / 0% / 8.39 | 0.994 / 0% / 14.28 | 0.987 / 0% / 19.11 | 1.000 / 0% / 9.89 | 1.000 / 0% / 1.53 | 1.000 / 0% / 10.27 | 1.000 / 0% / 1.64 |
| default | 1024 | 0.995 / 0% / 14.26 | 0.996 / 0% / 24.16 | 0.992 / 0% / 31.55 | 1.000 / 0% / 9.91 | 1.000 / 0% / 1.57 | 1.000 / 0% / 10.26 | 1.000 / 0% / 1.66 |
| sweeping | default | 0.977 / 0% / 2.7 | 0.984 / 0% / 4.41 | 0.994 / 0% / 13.69 | 1.000 / 0% / 9.86 | 1.000 / 0% / 1.54 | 1.000 / 0% / 10.29 | 1.000 / 0% / 1.64 |
| sweeping | 64 | 0.968 / 0% / 2.07 | 0.976 / 0% / 3.46 | 0.990 / 0% / 10.05 | 1.000 / 0% / 10.17 | 1.000 / 0% / 1.6 | 1.000 / 0% / 10.44 | 1.000 / 0% / 1.65 |
| sweeping | 128 | 0.982 / 0% / 3.15 | 0.986 / 0% / 5.17 | 0.995 / 0% / 16.68 | 1.000 / 0% / 10.07 | 1.000 / 0% / 1.58 | 1.000 / 0% / 10.47 | 1.000 / 0% / 1.66 |
| sweeping | 256 | 0.988 / 0% / 5.31 | 0.991 / 0% / 8.89 | 0.998 / 0% / 28.8 | 1.000 / 0% / 9.92 | 1.000 / 0% / 1.54 | 1.000 / 0% / 10.31 | 1.000 / 0% / 1.85 |
| sweeping | 512 | 0.992 / 0% / 8.52 | 0.994 / 0% / 14.21 | 0.999 / 0% / 49.38 | 1.000 / 0% / 9.88 | 1.000 / 0% / 1.61 | 1.000 / 0% / 10.57 | 1.000 / 0% / 1.69 |
| sweeping | 1024 | 0.995 / 0% / 14.37 | 0.996 / 0% / 24.24 | 0.999 / 0% / 88.86 | 1.000 / 0% / 9.92 | 1.000 / 0% / 1.53 | 1.000 / 0% / 10.2 | 1.000 / 0% / 1.69 |
| pathseer | default | 0.977 / 0% / 2.73 | 0.980 / 0% / 3.89 | 0.981 / 0% / 5.07 | 1.000 / 0% / 9.86 | 1.000 / 0% / 1.55 | 1.000 / 0% / 9.87 | 1.000 / 0% / 1.61 |
| pathseer | 64 | 0.968 / 0% / 1.97 | 0.972 / 0% / 2.71 | 0.971 / 0% / 3.49 | 1.000 / 0% / 9.51 | 1.000 / 0% / 1.49 | 1.000 / 0% / 9.78 | 1.000 / 0% / 1.59 |
| pathseer | 128 | 0.982 / 0% / 3.01 | 0.983 / 0% / 4.35 | 0.984 / 0% / 5.9 | 1.000 / 0% / 9.49 | 1.000 / 0% / 1.49 | 1.000 / 0% / 9.79 | 1.000 / 0% / 1.62 |
| pathseer | 256 | 0.988 / 0% / 4.85 | 0.990 / 0% / 7.11 | 0.993 / 0% / 10.36 | 1.000 / 0% / 9.51 | 1.000 / 0% / 1.49 | 1.000 / 0% / 9.77 | 1.000 / 0% / 1.63 |
| pathseer | 512 | 0.992 / 0% / 8.38 | 0.993 / 0% / 12.54 | 0.997 / 0% / 19.81 | 1.000 / 0% / 9.87 | 1.000 / 0% / 1.56 | 1.000 / 0% / 10.28 | 1.000 / 0% / 1.65 |
| pathseer | 1024 | 0.995 / 0% / 14.27 | 0.996 / 0% / 21.79 | 0.998 / 0% / 37.37 | 1.000 / 0% / 9.92 | 1.000 / 0% / 1.55 | 1.000 / 0% / 10.19 | 1.000 / 0% / 1.67 |

**elasticsearch**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.900 / 0% / 2.98 | 0.876 / 0% / 2.89 | 0.854 / 0% / 2.85 | 0.542 / 0% / 3.08 | 0.974 / 0% / 2.94 | 0.943 / 0% / 2.85 | 0.963 / 0% / 2.85 |
| default | 64 | 0.938 / 0% / 2.58 | 0.921 / 0% / 3.07 | 0.908 / 0% / 3.22 | 0.628 / 0% / 3.39 | 0.998 / 0% / 2.87 | 0.978 / 0% / 3.03 | 0.993 / 0% / 2.88 |
| default | 128 | 0.957 / 0% / 2.77 | 0.945 / 0% / 3.28 | 0.930 / 0% / 3.66 | 0.704 / 0% / 4.0 | 1.000 / 0% / 2.95 | 0.989 / 0% / 3.29 | 0.999 / 0% / 2.98 |
| default | 256 | 0.968 / 0% / 3.07 | 0.961 / 0% / 3.79 | 0.948 / 0% / 4.33 | 0.760 / 0% / 5.0 | 1.000 / 0% / 3.1 | 0.994 / 0% / 3.7 | 1.000 / 0% / 3.07 |
| default | 512 | 0.976 / 0% / 3.57 | 0.972 / 0% / 4.47 | 0.958 / 0% / 5.37 | 1.000 / 0% / 3.59 | 1.000 / 0% / 2.79 | 0.999 / 0% / 3.71 | 1.000 / 0% / 3.12 |
| default | 1024 | 0.981 / 0% / 4.48 | 0.980 / 0% / 5.63 | 0.966 / 0% / 6.78 | 1.000 / 0% / 4.05 | 1.000 / 0% / 3.42 | 1.000 / 0% / 4.1 | 1.000 / 0% / 3.32 |
| fanout | default | 0.900 / 0% / 2.4 | 0.910 / 0% / 2.66 | 0.914 / 0% / 2.88 | 0.960 / 0% / 3.01 | 0.974 / 0% / 2.83 | 0.935 / 0% / 2.67 | 0.963 / 0% / 2.85 |
| fanout | 64 | 0.938 / 0% / 2.55 | 0.945 / 0% / 2.83 | 0.954 / 0% / 3.15 | 0.994 / 0% / 3.04 | 0.998 / 0% / 2.9 | 0.972 / 0% / 2.79 | 0.993 / 0% / 2.92 |
| fanout | 128 | 0.957 / 0% / 2.76 | 0.963 / 0% / 3.06 | 0.968 / 0% / 3.49 | 0.999 / 0% / 3.09 | 1.000 / 0% / 2.98 | 0.984 / 0% / 2.99 | 0.999 / 0% / 2.94 |
| fanout | 256 | 0.968 / 0% / 3.06 | 0.973 / 0% / 3.38 | 0.978 / 0% / 4.01 | 1.000 / 0% / 3.23 | 1.000 / 0% / 3.12 | 0.993 / 0% / 3.29 | 1.000 / 0% / 3.08 |
| fanout | 512 | 0.976 / 0% / 3.58 | 0.980 / 0% / 3.96 | 0.985 / 0% / 4.83 | 1.000 / 0% / 3.58 | 1.000 / 0% / 2.81 | 0.999 / 0% / 3.66 | 1.000 / 0% / 3.12 |
| fanout | 1024 | 0.981 / 0% / 4.48 | 0.984 / 0% / 4.91 | 0.990 / 0% / 6.39 | 1.000 / 0% / 4.1 | 1.000 / 0% / 3.42 | 1.000 / 0% / 4.08 | 1.000 / 0% / 3.28 |
| exact | default | 1.000 / 0% / 244.5 | 1.000 / 0% / 126.2 | 1.000 / 0% / 29.93 | 1.000 / 0% / 5.51 | 1.000 / 0% / 2.03 | 1.000 / 0% / 5.7 | 1.000 / 0% / 2.09 |

**chroma**

| Option | Knob | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | default | 0.959 / 0% / 2.51 | 0.964 / 0% / 1627.39* | 0.992 / 0% / 501.4* | 0.996 / 0% / 276.08* | 1.000 / 0% / 575.7* | 0.989 / 0% / 227.31 | 0.999 / 0% / 166.11 |
| default | 64 | 0.942 / 0% / 2.05 | 0.959 / 0% / 1655.47* | 0.978 / 0% / 494.16* | 0.991 / 0% / 256.2* | 1.000 / 0% / 445.29* | 0.981 / 0% / 225.12 | 0.996 / 0% / 165.15 |
| default | 128 | 0.964 / 0% / 2.85 | 0.970 / 0% / 1618.36* | 0.991 / 0% / 513.17* | 0.998 / 0% / 294.02* | 1.000 / 0% / 654.7* | 0.992 / 0% / 227.01 | 0.999 / 0% / 168.19 |
| default | 256 | 0.977 / 0% / 4.21 | 0.983 / 0% / 1648.88* | 0.993 / 0% / 514.1* | 0.998 / 0% / 360.56* | 1.000 / 0% / 1009.91* | 0.997 / 0% / 232.13 | 1.000 / 0% / 172.82 |
| default | 512 | 0.983 / 0% / 6.27 | 0.987 / 0% / 1630.0* | 0.998 / 0% / 535.33* | 0.998 / 0% / 473.58* | 1.000 / 0% / 1501.26* | 0.999 / 0% / 238.65 | 1.000 / 0% / 194.25* |
| default | 1024 | 0.988 / 0% / 9.9 | 0.989 / 0% / 1659.55* | 0.998 / 0% / 557.02* | 0.998 / 0% / 661.5* | 1.000 / 0% / 2190.81* | 1.000 / 0% / 240.87* | 1.000 / 0% / 695.63* |


## Act 3: built (target recall 0.99: the lowest target at which no setting on a random filter loses more than 0.5 nDCG points against exact filtered search, tuning questions)

| Target recall | Settings at or above it (all databases, random filters) | Worst nDCG loss among them (points) |
| ---: | ---: | ---: |
| 0.8 | 361 | 6.87 |
| 0.85 | 361 | 6.87 |
| 0.9 | 355 | 5.33 |
| 0.95 | 322 | 2.03 |
| 0.97 | 300 | 1.29 |
| 0.99 | 252 | 0.50 |

Per database: the deployment, and per field the cheapest setting (tuning p50) with recall ≥ target and full results on tuning questions. Topical fields use the setting of the random field with the same selectivity.

| Database | Deployment | no filter | region 50% | dept 10% | team 1% | project 0.1% | Worst p50 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | ---: |
| pgvector | as shipped | ✗ none | default @ 512 (1421.62 ms) | default @ 512 (401.44 ms) | iterative @ 512 (85.55 ms) | default @ 256 (39.14 ms) | — |
| qdrant | payload index first | index_first @ 256 (12.76 ms) | index_first @ 256 (13.35 ms) | index_first @ 64 (4.84 ms) | index_first @ 64 (4.02 ms) | index_first @ 128 (1.49 ms) | 13.35 |
| milvus | declared + scalar index | schema_index @ 256 (4.97 ms) | schema_index @ 256 (5.06 ms) | schema_index @ 64 (4.49 ms) | schema_index @ default (3.34 ms) | schema_index @ default (2.09 ms) | 5.06 |
| weaviate | sweeping | sweeping @ 512 (8.56 ms) | sweeping @ 256 (9.03 ms) | sweeping @ 64 (10.07 ms) | sweeping @ default (9.87 ms) | sweeping @ 1024 (1.53 ms) | 10.07 |
| elasticsearch | acorn (as shipped) | exact @ default (244.7 ms) | exact @ default (125.84 ms) | exact @ default (29.98 ms) | default @ 512 (3.61 ms) | exact @ default (2.03 ms) | 244.7 |
| chroma | as shipped | default @ 1024 (10.01 ms) | default @ 1024 (1623.75 ms) | default @ default (502.13 ms) | default @ 64 (258.66 ms) | default @ 64 (449.27 ms) | 1623.75 |

**Built settings on the test questions** (1,000; recall / short / answer lost / p50 ms; topical fields held out)

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% | topic ~1% | subtopic ~0.1% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | ✗ | 1.000 / 0% / 0 / 1427.64 | 1.000 / 0% / 0 / 402.05 | 1.000 / 0% / 0 / 85.62 | 1.000 / 0% / 0 / 39.2 | 1.000 / 0% / 0 / 87.99 | 1.000 / 0% / 0 / 42.35 |
| qdrant | 0.991 / 0% / 5 / 12.87 | 0.993 / 0% / 6 / 13.32 | 0.987 ✗ / 0% / 12 / 4.81 | 0.999 / 0% / 1 / 4.03 | 1.000 / 0% / 0 / 1.49 | 0.997 / 0% / 1 / 4.14 | 1.000 / 0% / 0 / 1.57 |
| milvus | 0.992 / 0% / 3 / 5.0 | 0.990 ✗ / 0% / 4 / 5.06 | 0.989 ✗ / 0% / 6 / 4.53 | 1.000 / 0% / 0 / 3.33 | 1.000 / 0% / 0 / 2.1 | 1.000 / 0% / 0 / 3.42 | 1.000 / 0% / 0 / 2.13 |
| weaviate | 0.992 / 0% / 3 / 8.52 | 0.991 / 0% / 4 / 8.89 | 0.990 ✗ / 0% / 5 / 10.05 | 1.000 / 0% / 0 / 9.86 | 1.000 / 0% / 0 / 1.53 | 1.000 / 0% / 0 / 10.29 | 1.000 / 0% / 0 / 1.69 |
| elasticsearch | 1.000 / 0% / 0 / 244.5 | 1.000 / 0% / 0 / 126.2 | 1.000 / 0% / 0 / 29.93 | 1.000 / 0% / 0 / 3.59 | 1.000 / 0% / 0 / 2.03 | 0.999 / 0% / 0 / 3.71 | 1.000 / 0% / 0 / 2.09 |
| chroma | 0.988 ✗ / 0% / 7 / 9.9 | 0.989 ✗ / 0% / 0 / 1659.55 | 0.992 / 0% / 0 / 501.4 | 0.991 / 0% / 0 / 256.2 | 1.000 / 0% / 0 / 445.29 | 0.981 ✗ / 0% / 11 / 225.12 | 0.996 / 0% / 2 / 165.15 |

**Deploy check** (200 test questions per field, seed 7: recall ≥ 0.99 and no short result)

| Database | no filter: default → built | region 50%: default → built | dept 10%: default → built | team 1%: default → built | project 0.1%: default → built |
| :--- | :---: | :---: | :---: | :---: | :---: |
| pgvector | FAIL 0.901 → — | FAIL 0.883 → pass 1.000 (n=9) | FAIL 0.476, 200 short → pass 1.000 (n=9) | FAIL 0.129, 200 short → pass 1.000 | pass 1.000 → pass 1.000 |
| qdrant | FAIL 0.959 → FAIL 0.989 | FAIL 0.916 → pass 0.993 | FAIL 0.331 → FAIL 0.984 | FAIL 0.593, 3 short → pass 0.998 | pass 0.999 → pass 1.000 |
| milvus | FAIL 0.867 → FAIL 0.986 | FAIL 0.856 → pass 0.990 | FAIL 0.948 → FAIL 0.985 | pass 1.000 → pass 1.000 | pass 1.000 → pass 1.000 |
| weaviate | FAIL 0.970 → FAIL 0.989 | FAIL 0.977 → FAIL 0.988 | FAIL 0.946 → FAIL 0.984 | pass 1.000 → pass 1.000 | pass 1.000 → pass 1.000 |
| elasticsearch | FAIL 0.877 → pass 1.000 | FAIL 0.852 → pass 1.000 | FAIL 0.835 → pass 1.000 | FAIL 0.547 → pass 1.000 | FAIL 0.974 → pass 1.000 |
| chroma | FAIL 0.945 → FAIL 0.984 | FAIL 0.880 (n=5) → FAIL 0.978 (n=9) | FAIL 0.980 (n=5) → FAIL 0.980 (n=5) | FAIL 0.980 (n=5) → FAIL 0.978 (n=9) | pass 1.000 (n=5) → pass 1.000 (n=9) |

(Recall on the sample, and sample questions with a short result. n=…: a sampled cell; only the sample questions it ran are checked.)

**Exploratory, after the results: choose with a margin** (tuning recall ≥ 0.995, same deployment; then the same deploy check at 0.99). Setting (test p50 ms) → check.

| Database | no filter | region 50% | dept 10% | team 1% | project 0.1% |
| :--- | :--- | :--- | :--- | :--- | :--- |
| pgvector | ✗ none | default @ 512 (1427.64) → pass 1.000 | default @ 512 (402.05) → pass 1.000 | iterative @ 512 (85.62) → pass 1.000 | default @ 256 (39.2) → pass 1.000 |
| qdrant | acorn @ 512 (23.02) → pass 0.995 | index_first @ 256 (13.32) → pass 0.993 | index_first @ default (6.4) → pass 0.993 | index_first @ 64 (4.03) → pass 0.998 | index_first @ 128 (1.49) → pass 1.000 |
| milvus | schema_index @ 512 (6.86) → pass 0.994 | schema_index @ 512 (6.92) → pass 0.996 | schema_index @ 128 (6.25) → pass 0.993 | schema_index @ default (3.33) → pass 1.000 | schema_index @ default (2.1) → pass 1.000 |
| weaviate | sweeping @ 1024 (14.37) → pass 0.993 | sweeping @ 512 (14.21) → pass 0.991 | sweeping @ 128 (16.68) → pass 0.991 | sweeping @ default (9.86) → pass 1.000 | sweeping @ 1024 (1.53) → pass 1.000 |
| elasticsearch | exact @ default (244.5) → pass 1.000 | exact @ default (126.2) → pass 1.000 | exact @ default (29.93) → pass 1.000 | default @ 512 (3.59) → pass 1.000 | exact @ default (2.03) → pass 1.000 |
| chroma | ✗ none | ✗ none | default @ default (501.4) → FAIL 0.980 | default @ 64 (256.2) → FAIL 0.978 | default @ 64 (445.29) → pass 1.000 |
