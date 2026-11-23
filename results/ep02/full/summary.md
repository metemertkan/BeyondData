# Episode 2 results (full: 1,000,000 passages, 2,452 test questions)

Exact search (brute force): nDCG@10 0.7386, hit@10 0.9152.

## Load and size

| Database | Load (s) | Index wait (s) | Total (min) | Recall just indexed | Settle (s) | Memory after load (MiB) | after queries | Disk (GB) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 30 | 3036 | 51.1 | 0.923 | 0 | 587 | 587 | 14.90 |
| qdrant | 504 | 56 | 9.3 | 0.979 | 0 | 391 | 373 | 4.48 |
| milvus | 129 | 156 | 4.7 | 0.933 | 380 | 3320 | 3376 | 22.27 |
| weaviate | 924 | 0 | 15.4 | 0.982 | 0 | 8515 | 8848 | 4.60 |
| elasticsearch | 1548 | 103 | 27.5 | 0.901 | 0 | 9215 | 9219 | 6.18 |
| chroma | 1108 | 0 | 18.5 | 0.963 | 0 | 4361 | 4360 | 4.42 |

milvus segments while settling: 0 s: 27 (86,000, 31,000, 29,000, 29,510, 28,000, 29,510, 27,980, 31,000, 148,490, 30,510, 28,490, 30,510, 29,000, 28,000, 87,000, 28,000, 30,490, 28,000, 29,000, 30,000, 29,000, 30,020, 30,490, 29,490, 30,510, 28,000, 3,000); 20 s: 25 (29,510, 28,000, 29,510, 27,980, 31,000, 148,490, 30,510, 28,490, 30,510, 29,000, 28,000, 87,000, 28,000, 30,490, 28,000, 29,000, 30,000, 29,000, 30,020, 30,490, 29,490, 146,000, 30,510, 28,000, 3,000); 70 s: 20 (148,490, 28,490, 30,510, 29,000, 28,000, 87,000, 28,000, 30,490, 28,000, 29,000, 30,000, 29,000, 30,020, 30,490, 29,490, 146,000, 30,510, 28,000, 3,000, 176,510); 110 s: 15 (148,490, 30,510, 29,000, 87,000, 30,490, 30,000, 30,020, 30,490, 29,490, 146,000, 30,510, 28,000, 3,000, 176,510, 170,490); 180 s: 10 (148,490, 30,490, 29,490, 146,000, 30,510, 28,000, 3,000, 176,510, 237,020, 170,490); 200 s: 6 (148,490, 146,000, 176,510, 237,020, 170,490, 121,490)

pgvector plans: top 1 = index scan (11.8 ms), top 10 = index scan (3.3 ms); TOAST 5.53 GB.

## Act 1: as shipped (no search parameters)

| Database | Recall@10 | nDCG@10 | hit@10 | Nearest missed | Answer lost | p50 ms | p99 ms | Throughput (q/s, 16 clients) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.9192 | 0.6989 | 0.8679 | 139 | 121 | 4.34 | 7.75 | 680.7 |
| qdrant | 0.9695 | 0.7271 | 0.9013 | 34 | 35 | 4.2 | 5.75 | 403.2 |
| milvus | 0.9106 | 0.7068 | 0.8744 | 123 | 105 | 1.81 | 2.9 | 2176.4 |
| weaviate | 0.9779 | 0.7305 | 0.9054 | 26 | 24 | 2.7 | 3.88 | 1326.6 |
| elasticsearch | 0.9012 | 0.7024 | 0.8703 | 126 | 116 | 2.87 | 5.37 | 1968.6 |
| chroma | 0.9583 | 0.7192 | 0.8927 | 65 | 57 | 2.52 | 3.59 | 495.1 |
| exact search | 1.0000 | 0.7386 | 0.9152 | 0 | 0 | | | |

Nearest missed: test questions whose true nearest passage is not in the top 10. Answer lost: test questions where exact search's top 10 holds a labeled answer and the database's top 10 holds none.

All 6 databases returned the same top 10 (as a set) for 42.8% of test questions, and the same top 1 for 89.7%. Lowest pairwise overlap: milvus|elasticsearch 88.5%.


## Act 2: the search-time sweep (test questions)


**pgvector** (`hnsw.ef_search`): 10: 0.792 / 1.88 ms; 16: 0.845 / 2.44 ms; 24: 0.884 / 3.08 ms; 32: 0.906 / 3.75 ms; 48: 0.930 / 4.89 ms; 64: 0.940 / 6.09 ms; 96: 0.953 / 8.38 ms; 128: 0.959 / 10.41 ms; 192: 0.968 / 14.44 ms; 256: 0.973 / 18.44 ms; 384: 0.979 / 26.05 ms; 512: 0.981 / 33.51 ms; 768: 0.986 / 47.92 ms

**qdrant** (`hnsw_ef`): 10: 0.837 / 1.69 ms; 16: 0.887 / 1.93 ms; 24: 0.916 / 2.16 ms; 32: 0.932 / 2.41 ms; 48: 0.949 / 2.92 ms; 64: 0.958 / 3.33 ms; 96: 0.969 / 4.06 ms; 128: 0.975 / 4.75 ms; 192: 0.981 / 5.97 ms; 256: 0.985 / 7.0 ms; 384: 0.988 / 8.95 ms; 512: 0.991 / 10.72 ms; 768: 0.993 / 14.25 ms; 1024: 0.995 / 17.35 ms

**milvus** (`ef`): 10: 0.864 / 1.73 ms; 16: 0.911 / 1.84 ms; 24: 0.937 / 1.97 ms; 32: 0.952 / 2.03 ms; 48: 0.968 / 2.34 ms; 64: 0.975 / 2.62 ms; 96: 0.983 / 3.15 ms; 128: 0.988 / 3.62 ms; 192: 0.991 / 4.43 ms; 256: 0.993 / 5.07 ms; 384: 0.995 / 6.19 ms; 512: 0.997 / 7.05 ms; 768: 0.998 / 8.61 ms; 1024: 0.998 / 10.09 ms

**weaviate** (`ef`): 10: 0.839 / 0.99 ms; 16: 0.892 / 1.12 ms; 24: 0.925 / 1.28 ms; 32: 0.943 / 1.41 ms; 48: 0.959 / 1.73 ms; 64: 0.968 / 2.01 ms; 96: 0.977 / 2.61 ms; 128: 0.982 / 3.19 ms; 192: 0.986 / 4.18 ms; 256: 0.988 / 5.07 ms; 384: 0.991 / 6.81 ms; 512: 0.992 / 8.39 ms; 768: 0.994 / 11.33 ms; 1024: 0.995 / 14.31 ms

**elasticsearch** (`num_candidates`): 10: 0.901 / 2.4 ms; 16: 0.901 / 2.29 ms; 24: 0.901 / 2.24 ms; 32: 0.906 / 2.23 ms; 48: 0.928 / 2.26 ms; 64: 0.939 / 2.29 ms; 96: 0.950 / 2.41 ms; 128: 0.956 / 2.5 ms; 192: 0.963 / 2.68 ms; 256: 0.967 / 2.78 ms; 384: 0.972 / 3.06 ms; 512: 0.975 / 3.3 ms; 768: 0.979 / 3.75 ms; 1024: 0.982 / 4.16 ms

**chroma** (`ef_search`): 10: 0.769 / 1.41 ms; 16: 0.842 / 1.51 ms; 24: 0.885 / 1.62 ms; 32: 0.907 / 1.71 ms; 48: 0.929 / 1.88 ms; 64: 0.943 / 2.04 ms; 96: 0.957 / 2.39 ms; 128: 0.964 / 2.82 ms; 192: 0.973 / 3.44 ms; 256: 0.977 / 4.11 ms; 384: 0.982 / 5.23 ms; 512: 0.984 / 6.17 ms; 768: 0.988 / 8.05 ms; 1024: 0.989 / 9.8 ms


## Act 2: tuned to the same recall (cheapest sweep value reaching the target on tuning questions)

| Database | Target | Setting | Test recall@10 | nDCG@10 | p50 ms | p99 ms | Throughput (q/s) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | 0.95 | 96 | 0.9532 | 0.7176 | 8.38 | 12.83 | 354.4 |
| qdrant | 0.95 | 48 | 0.9491 | 0.7174 | 2.92 | 3.88 | 661.8 |
| milvus | 0.95 | 32 | 0.9522 | 0.7249 | 2.03 | 3.26 | 1710.6 |
| weaviate | 0.95 | 48 | 0.9591 | 0.7210 | 1.73 | 2.59 | 2214.7 |
| elasticsearch | 0.95 | 96 | 0.9495 | 0.7165 | 2.41 | 3.49 | 1702.8 |
| chroma | 0.95 | 96 | 0.9574 | 0.7190 | 2.39 | 3.16 | 507.0 |
| pgvector | 0.99 | not reached (best 0.986 at 768) | | | | | |
| qdrant | 0.99 | 512 | 0.9913 | 0.7359 | 10.72 | 14.87 | 117.8 |
| milvus | 0.99 | 192 | 0.9911 | 0.7373 | 4.43 | 6.2 | 599.2 |
| weaviate | 0.99 | 384 | 0.9908 | 0.7352 | 6.81 | 9.73 | 468.4 |
| elasticsearch | 0.99 | not reached (best 0.982 at 1024) | | | | | |
| chroma | 0.99 | 1024 | 0.9895 | 0.7339 | 9.8 | 13.18 | 110.1 |

## Act 3: built (target recall 0.99: the lowest target at which no tuning point loses more than 0.5 nDCG points against exact search)

| Database | Setting | Test recall@10 | Holds target | nDCG@10 | p50 ms | Deploy check at default | Deploy check at built |
| :--- | ---: | ---: | :---: | ---: | ---: | :---: | :---: |
| pgvector | not reachable | | | | | 0.922 | |
| qdrant | 512 | 0.9913 | yes | 0.7359 | 10.72 | FAIL (0.976) | pass (0.996) |
| milvus | 192 | 0.9911 | yes | 0.7373 | 4.43 | FAIL (0.912) | pass (0.994) |
| weaviate | 384 | 0.9908 | yes | 0.7352 | 6.81 | FAIL (0.983) | pass (0.993) |
| elasticsearch | not reachable | | | | | 0.912 | |
| chroma | 1024 | 0.9895 | no | 0.7339 | 9.8 | FAIL (0.967) | pass (0.992) |

## Read your own write (insert one passage, search for it at once: in the top 10?)

| Database | Found at once | Found after 1 s | Insert p50 ms | Insert p99 ms |
| :--- | ---: | ---: | ---: | ---: |
| pgvector | 991/991 | 991/991 | 9.85 | 15.68 |
| qdrant | 991/991 | 991/991 | 2.95 | 15.59 |
| milvus | 0/991 | 991/991 | 1.23 | 2.07 |
| weaviate | 991/991 | 991/991 | 3.34 | 5.3 |
| elasticsearch | 1/991 | 991/991 | 9.88 | 15.38 |
| chroma | 991/991 | 991/991 | 46.29 | 61.42 |
