# Episode 2 results (pilot: 100,000 passages, 2,452 test questions)

Exact search (brute force): nDCG@10 0.9093, hit@10 0.9772.

## Load and size

| Database | Load (s) | Index wait (s) | Total (min) | Recall just indexed | Settle (s) | Memory after load (MiB) | after queries | Disk (GB) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 4 | 521 | 8.7 | 0.961 | 0 | 218 | 218 | 1.90 |
| qdrant | 40 | 6 | 0.8 | 0.993 | 0 | 158 | 169 | 0.73 |
| milvus | 12 | 6 | 0.3 | 0.938 | 260 | 637 | 684 | 2.34 |
| weaviate | 75 | 0 | 1.3 | 0.992 | 0 | 1028 | 1029 | 0.51 |
| elasticsearch | 131 | 0 | 2.2 | 0.934 | 0 | 9024 | 9099 | 0.66 |
| chroma | 75 | 0 | 1.2 | 0.984 | 0 | 448 | 446 | 0.45 |

milvus segments while settling: 0 s: 1 (30,490); 10 s: 4 (30,490, 28,020, 27,980, 13,510); 80 s: 1 (100,000)

pgvector plans: top 1 = sequential scan (561.6 ms), top 10 = index scan (6.2 ms); TOAST 0.55 GB.

## Act 1: as shipped (no search parameters)

| Database | Recall@10 | nDCG@10 | hit@10 | Nearest missed | Answer lost | p50 ms | p99 ms | Throughput (q/s, 16 clients) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.9546 | 0.8840 | 0.9494 | 65 | 68 | 3.4 | 5.46 | 902.2 |
| qdrant | 0.9942 | 0.9073 | 0.9743 | 4 | 7 | 3.66 | 4.73 | 481.3 |
| milvus | 0.8473 | 0.8704 | 0.9335 | 109 | 111 | 1.19 | 1.93 | 5920.1 |
| weaviate | 0.9900 | 0.9048 | 0.9719 | 9 | 13 | 2.3 | 3.11 | 1497.6 |
| elasticsearch | 0.9374 | 0.8987 | 0.9653 | 27 | 29 | 2.34 | 4.8 | 3793.9 |
| chroma | 0.9789 | 0.8982 | 0.9649 | 26 | 30 | 2.33 | 3.07 | 519.1 |
| exact search | 1.0000 | 0.9093 | 0.9772 | 0 | 0 | | | |

Nearest missed: test questions whose true nearest passage is not in the top 10. Answer lost: test questions where exact search's top 10 holds a labeled answer and the database's top 10 holds none.

All 6 databases returned the same top 10 (as a set) for 16.6% of test questions, and the same top 1 for 93.7%. Lowest pairwise overlap: milvus|elasticsearch 83.5%.


## Act 2: the search-time sweep (test questions)


**pgvector** (`hnsw.ef_search`): 10: 0.857 / 1.43 ms; 16: 0.900 / 1.84 ms; 24: 0.930 / 2.36 ms; 32: 0.944 / 2.92 ms; 48: 0.961 / 3.86 ms; 64: 0.970 / 4.84 ms; 96: 0.980 / 6.62 ms; 128: 0.984 / 8.36 ms; 192: 0.989 / 11.52 ms; 256: 0.992 / 14.63 ms; 384: 0.994 / 20.36 ms; 512: 0.996 / 26.29 ms; 768: 0.997 / 36.87 ms

**qdrant** (`hnsw_ef`): 10: 0.897 / 1.53 ms; 16: 0.938 / 1.71 ms; 24: 0.961 / 1.92 ms; 32: 0.973 / 2.11 ms; 48: 0.984 / 2.49 ms; 64: 0.989 / 2.93 ms; 96: 0.994 / 3.59 ms; 128: 0.996 / 4.13 ms; 192: 0.997 / 5.1 ms; 256: 0.998 / 5.87 ms; 384: 0.999 / 7.3 ms; 512: 0.999 / 8.64 ms; 768: 1.000 / 10.77 ms; 1024: 1.000 / 12.61 ms

**milvus** (`ef`): 10: 0.805 / 1.17 ms; 16: 0.847 / 1.17 ms; 24: 0.932 / 1.26 ms; 32: 0.952 / 1.27 ms; 48: 0.971 / 1.37 ms; 64: 0.981 / 1.45 ms; 96: 0.989 / 1.61 ms; 128: 0.992 / 1.74 ms; 192: 0.996 / 2.0 ms; 256: 0.997 / 2.33 ms; 384: 0.998 / 3.07 ms; 512: 0.998 / 3.7 ms; 768: 0.999 / 4.68 ms; 1024: 0.999 / 5.8 ms

**weaviate** (`ef`): 10: 0.868 / 0.87 ms; 16: 0.916 / 0.99 ms; 24: 0.946 / 1.14 ms; 32: 0.962 / 1.26 ms; 48: 0.976 / 1.52 ms; 64: 0.984 / 1.75 ms; 96: 0.990 / 2.27 ms; 128: 0.992 / 2.71 ms; 192: 0.995 / 3.55 ms; 256: 0.996 / 4.32 ms; 384: 0.998 / 5.65 ms; 512: 0.998 / 6.86 ms; 768: 0.999 / 9.11 ms; 1024: 0.999 / 11.2 ms

**elasticsearch** (`num_candidates`): 10: 0.937 / 1.96 ms; 16: 0.937 / 1.81 ms; 24: 0.937 / 1.8 ms; 32: 0.943 / 1.76 ms; 48: 0.969 / 1.75 ms; 64: 0.978 / 1.76 ms; 96: 0.986 / 1.87 ms; 128: 0.989 / 1.9 ms; 192: 0.992 / 2.01 ms; 256: 0.994 / 2.19 ms; 384: 0.995 / 2.45 ms; 512: 0.996 / 2.6 ms; 768: 0.997 / 2.94 ms; 1024: 0.998 / 3.3 ms

**chroma** (`ef_search`): 10: 0.816 / 1.39 ms; 16: 0.877 / 1.43 ms; 24: 0.913 / 1.54 ms; 32: 0.933 / 1.61 ms; 48: 0.956 / 1.82 ms; 64: 0.967 / 2.01 ms; 96: 0.978 / 2.31 ms; 128: 0.984 / 2.68 ms; 192: 0.988 / 3.32 ms; 256: 0.991 / 3.9 ms; 384: 0.994 / 4.84 ms; 512: 0.996 / 5.63 ms; 768: 0.997 / 7.17 ms; 1024: 0.998 / 8.64 ms


## Act 2: tuned to the same recall (cheapest sweep value reaching the target on tuning questions)

| Database | Target | Setting | Test recall@10 | nDCG@10 | p50 ms | p99 ms | Throughput (q/s) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.95 | 48 | 0.9609 | 0.8861 | 3.86 | 6.18 | 791.6 |
| qdrant | 0.95 | 24 | 0.9613 | 0.8919 | 1.92 | 2.96 | 1115.5 |
| milvus | 0.95 | 32 | 0.9519 | 0.8915 | 1.27 | 2.28 | 5355.9 |
| weaviate | 0.95 | 32 | 0.9620 | 0.8935 | 1.26 | 1.76 | 3264.1 |
| elasticsearch | 0.95 | 48 | 0.9690 | 0.9013 | 1.75 | 2.17 | 3610.0 |
| chroma | 0.95 | 48 | 0.9556 | 0.8853 | 1.82 | 2.56 | 728.4 |
| pgvector | 0.99 | 256 | 0.9920 | 0.9046 | 14.63 | 21.72 | 203.9 |
| qdrant | 0.99 | 96 | 0.9940 | 0.9072 | 3.59 | 4.79 | 491.8 |
| milvus | 0.99 | 96 | 0.9887 | 0.9045 | 1.61 | 2.67 | 3978.4 |
| weaviate | 0.99 | 128 | 0.9918 | 0.9054 | 2.71 | 3.79 | 1255.0 |
| elasticsearch | 0.99 | 192 | 0.9924 | 0.9056 | 2.01 | 2.49 | 2749.1 |
| chroma | 0.99 | 256 | 0.9914 | 0.9031 | 3.9 | 5.12 | 300.1 |

## Act 3: built (target recall 0.99: the lowest target at which no tuning point loses more than 0.5 nDCG points against exact search)

| Database | Setting | Test recall@10 | Holds target | nDCG@10 | p50 ms | Deploy check at default | Deploy check at built |
| :--- | ---: | ---: | :---: | ---: | ---: | :---: | :---: |
| pgvector | 256 | 0.9920 | yes | 0.9046 | 14.63 | FAIL (0.953) | pass (0.993) |
| qdrant | 96 | 0.9940 | yes | 0.9072 | 3.59 | pass (0.994) | pass (0.994) |
| milvus | 96 | 0.9887 | no | 0.9045 | 1.61 | FAIL (0.848) | pass (0.991) |
| weaviate | 128 | 0.9918 | yes | 0.9054 | 2.71 | pass (0.994) | pass (0.995) |
| elasticsearch | 192 | 0.9924 | yes | 0.9056 | 2.01 | FAIL (0.935) | pass (0.995) |
| chroma | 256 | 0.9914 | yes | 0.9031 | 3.9 | FAIL (0.985) | pass (0.995) |

## Read your own write (insert one passage, search for it at once: in the top 10?)

| Database | Found at once | Found after 1 s | Insert p50 ms | Insert p99 ms |
| :--- | ---: | ---: | ---: | ---: |
| pgvector | 998/998 | 998/998 | 9.21 | 13.89 |
| qdrant | 998/998 | 998/998 | 2.93 | 15.55 |
| milvus | 0/998 | 998/998 | 0.97 | 1.75 |
| weaviate | 998/998 | 998/998 | 3.07 | 4.51 |
| elasticsearch | 2/998 | 998/998 | 10.05 | 14.93 |
| chroma | 998/998 | 998/998 | 46.41 | 62.94 |
