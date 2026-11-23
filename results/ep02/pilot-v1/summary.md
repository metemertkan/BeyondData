# Episode 2 results (pilot: 100,000 passages, 2,452 test questions)

Exact search (brute force): nDCG@10 0.9093, hit@10 0.9772.

## Load and size

| Database | Load (s) | Index wait (s) | Total (min) | Memory after load (MiB) | after queries | Disk (GB) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 4 | 522 | 8.8 | 217 | 218 | 1.90 |
| qdrant | 41 | 6 | 0.8 | 162 | 185 | 0.73 |
| milvus | 11 | 8 | 0.3 | 985 | 695 | 1.65 |
| weaviate | 75 | 0 | 1.2 | 988 | 1024 | 0.51 |
| elasticsearch | 131 | 8 | 2.3 | 8965 | 9098 | 0.60 |
| chroma | 74 | 0 | 1.2 | 539 | 549 | 0.45 |

## Act 1: as shipped (no search parameters)

| Database | Recall@10 | nDCG@10 | hit@10 | p50 ms | p99 ms | Throughput (q/s, 16 clients) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.9527 | 0.8819 | 0.9478 | 3.34 | 5.26 | 910.5 |
| qdrant | 0.9941 | 0.9072 | 0.9739 | 3.97 | 5.34 | 468.3 |
| milvus | 0.9330 | 0.8842 | 0.9507 | 1.47 | 2.49 | 5897.8 |
| weaviate | 0.9896 | 0.9052 | 0.9723 | 2.31 | 3.07 | 1513.2 |
| elasticsearch | 0.9375 | 0.8979 | 0.9657 | 2.27 | 4.57 | 3783.7 |
| chroma | 0.9787 | 0.8982 | 0.9649 | 2.4 | 3.18 | 509.6 |
| exact search | 1.0000 | 0.9093 | 0.9772 | | | |

All 6 databases returned the same top 10 (as a set) for 44.4% of test questions, and the same top 1 for 95.2%. Lowest pairwise overlap: milvus|elasticsearch 91.2%.


## Act 2: the search-time sweep (test questions)


**pgvector** (`hnsw.ef_search`): 10: 0.856 / 1.4 ms; 16: 0.899 / 1.85 ms; 24: 0.927 / 2.36 ms; 32: 0.944 / 2.86 ms; 48: 0.959 / 3.81 ms; 64: 0.969 / 4.8 ms; 96: 0.979 / 6.63 ms; 128: 0.984 / 8.27 ms; 192: 0.989 / 11.45 ms; 256: 0.992 / 14.5 ms; 384: 0.994 / 20.33 ms; 512: 0.996 / 25.97 ms; 768: 0.997 / 36.89 ms

**qdrant** (`hnsw_ef`): 10: 0.895 / 1.98 ms; 16: 0.940 / 2.16 ms; 24: 0.964 / 2.42 ms; 32: 0.974 / 5.66 ms; 48: 0.984 / 3.06 ms; 64: 0.989 / 3.32 ms; 96: 0.994 / 3.89 ms; 128: 0.996 / 4.44 ms; 192: 0.997 / 5.52 ms; 256: 0.998 / 6.17 ms; 384: 0.999 / 7.65 ms; 512: 0.999 / 8.89 ms; 768: 0.999 / 11.13 ms; 1024: 0.999 / 12.95 ms

**milvus** (`ef`): 10: 0.891 / 1.41 ms; 16: 0.933 / 1.47 ms; 24: 0.959 / 1.52 ms; 32: 0.973 / 1.67 ms; 48: 0.985 / 4.81 ms; 64: 0.990 / 2.23 ms; 96: 0.994 / 2.03 ms; 128: 0.934 / 1.96 ms; 192: 0.906 / 2.02 ms; 256: 0.907 / 2.26 ms; 384: 0.907 / 2.92 ms; 512: 0.907 / 3.3 ms; 768: 0.908 / 4.43 ms; 1024: 0.908 / 5.19 ms

**weaviate** (`ef`): 10: 0.872 / 0.87 ms; 16: 0.918 / 0.97 ms; 24: 0.947 / 1.11 ms; 32: 0.962 / 1.27 ms; 48: 0.976 / 1.48 ms; 64: 0.983 / 1.75 ms; 96: 0.989 / 2.22 ms; 128: 0.992 / 2.68 ms; 192: 0.995 / 3.55 ms; 256: 0.996 / 4.28 ms; 384: 0.998 / 5.6 ms; 512: 0.998 / 6.84 ms; 768: 0.999 / 9.12 ms; 1024: 0.999 / 11.17 ms

**elasticsearch** (`num_candidates`): 10: 0.938 / 1.89 ms; 16: 0.938 / 1.82 ms; 24: 0.938 / 1.77 ms; 32: 0.938 / 1.76 ms; 48: 0.942 / 1.72 ms; 64: 0.944 / 1.73 ms; 96: 0.946 / 1.8 ms; 128: 0.948 / 1.82 ms; 192: 0.950 / 1.89 ms; 256: 0.951 / 1.97 ms; 384: 0.952 / 2.02 ms; 512: 0.953 / 2.18 ms; 768: 0.953 / 2.24 ms; 1024: 0.954 / 2.44 ms

**chroma** (`ef_search`): 10: 0.979 / 2.41 ms; 16: 0.979 / 2.38 ms; 24: 0.979 / 2.39 ms; 32: 0.979 / 2.35 ms; 48: 0.979 / 2.38 ms; 64: 0.979 / 2.37 ms; 96: 0.979 / 2.36 ms; 128: 0.979 / 2.39 ms; 192: 0.979 / 2.35 ms; 256: 0.979 / 2.36 ms; 384: 0.979 / 2.35 ms; 512: 0.979 / 2.36 ms; 768: 0.979 / 2.4 ms; 1024: 0.979 / 2.39 ms


## Act 2: tuned to the same recall (cheapest sweep value reaching the target on tuning questions)

| Database | Target | Setting | Test recall@10 | nDCG@10 | p50 ms | p99 ms | Throughput (q/s) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.95 | 48 | 0.9594 | 0.8843 | 3.81 | 5.82 | 795.4 |
| qdrant | 0.95 | 24 | 0.9641 | 0.8958 | 2.42 | 6.28 | 687.1 |
| milvus | 0.95 | 24 | 0.9586 | 0.8937 | 1.52 | 3.21 | 5636.9 |
| weaviate | 0.95 | 32 | 0.9623 | 0.8941 | 1.27 | 1.94 | 3284.5 |
| elasticsearch | 0.95 | 192 | 0.9497 | 0.9061 | 1.89 | 2.42 | 3160.3 |
| chroma | 0.95 | 10 | 0.9787 | 0.8982 | 2.41 | 3.24 | 510.8 |
| pgvector | 0.99 | 256 | 0.9918 | 0.9046 | 14.5 | 21.57 | 204.1 |
| qdrant | 0.99 | 64 | 0.9894 | 0.9052 | 3.32 | 7.2 | 491.8 |
| milvus | 0.99 | 64 | 0.9898 | 0.9043 | 2.23 | 7.21 | 4720.5 |
| weaviate | 0.99 | 128 | 0.9919 | 0.9067 | 2.68 | 3.57 | 1255.4 |
| elasticsearch | 0.99 | not reached (best 0.954 at 1024) | | | | | |
| chroma | 0.99 | not reached (best 0.979 at 10) | | | | | |

## Act 3: built (target recall 0.99: the lowest target at which no tuning point loses more than 0.5 nDCG points against exact search)

| Database | Setting | Test recall@10 | Holds target | nDCG@10 | p50 ms | Deploy check at default | Deploy check at built |
| :--- | ---: | ---: | :---: | ---: | ---: | :---: | :---: |
| pgvector | 256 | 0.9918 | yes | 0.9046 | 14.5 | FAIL (0.953) | pass (0.993) |
| qdrant | 64 | 0.9894 | no | 0.9052 | 3.32 | pass (0.997) | pass (0.990) |
| milvus | 64 | 0.9898 | no | 0.9043 | 2.23 | FAIL (0.932) | pass (0.990) |
| weaviate | 128 | 0.9919 | yes | 0.9067 | 2.68 | pass (0.994) | pass (0.995) |
| elasticsearch | not reachable | | | | | 0.929 | |
| chroma | not reachable | | | | | 0.985 | |

## Read your own write (insert one passage, search for it at once, top 1)

| Database | Found at once | Found after 1 s | Insert p50 ms |
| :--- | ---: | ---: | ---: |
| pgvector | 998/998 | 998/998 | 17.83 |
| qdrant | 998/998 | 998/998 | 3.25 |
| milvus | 0/998 | 998/998 | 0.96 |
| weaviate | 998/998 | 998/998 | 3.06 |
| elasticsearch | 2/998 | 998/998 | 9.98 |
| chroma | 998/998 | 998/998 | 46.89 |
