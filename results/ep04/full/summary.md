# Episode 4 summary (full: 1,000,000 passages)

Exact float32 search, test questions: nDCG@10 0.739, hit@10 0.915.

## Settings read back

- **pgvector / vector** (float32: HNSW on the vector column (README)): `{"version": "0.8.7", "index": "CREATE INDEX docs_embedding_idx ON public.docs USING hnsw (embedding vector_cosine_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 8177991680, "table_bytes": 5590548480, "toast_bytes": 5530271744, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=3249.11..3308.41 rows=10 width=16) / ->  Index Scan using docs_embedding_idx on docs  (cost=3249.11..5932892.00 rows=1000000 width=16)"}`
- **pgvector / halfvec** (16-bit: HNSW on embedding::halfvec(1024) (README, half-precision indexing)): `{"version": "0.8.7", "index": "CREATE INDEX docs_embedding_idx ON public.docs USING hnsw (((embedding)::halfvec(1024)) halfvec_cosine_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 2726576128, "table_bytes": 5590548480, "toast_bytes": 5530271744, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=1087.33..1101.15 rows=10 width=16) / ->  Index Scan using docs_embedding_idx on docs  (cost=1087.33..1383248.00 rows=1000000 width=16)"}`
- **pgvector / bit** (1-bit: HNSW on binary_quantize(embedding)::bit(1024), the README's re-rank query): `{"version": "0.8.7", "index": "CREATE INDEX docs_binary_quantize_idx ON public.docs USING hnsw (((binary_quantize(embedding))::bit(1024)) bit_hamming_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 433717248, "table_bytes": 5590466560, "toast_bytes": 5530189824, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=190.09..190.11 rows=10 width=16) / ->  Sort  (cost=190.09..190.19 rows=40 width=16) / Sort Key: ((t.embedding <=> '[...]'::vector)) / ->  Subquery Scan on t  (cost=178.08..189.22 rows=40 width=16) / ->  Limit  (cost=178.08..188.72 rows`
- **qdrant / none** (float32: no quantization (default)): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / scalar** (8-bit: scalar int8): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo4** (4-bit: TurboQuant bits4): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo2** (2-bit: TurboQuant bits2): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / binary** (1-bit: binary quantization (the docs' first example)): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo1** (1-bit: TurboQuant bits1): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **milvus / hnsw** (float32: HNSW): `{"index": {"metric_type": "COSINE", "index_type": "HNSW", "field_name": "vector", "index_name": "vector", "total_rows": 1000000, "indexed_rows": 1000000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **milvus / hnsw_sq8** (8-bit: HNSW_SQ (sq_type default SQ8, no refine)): `{"index": {"metric_type": "COSINE", "index_type": "HNSW_SQ", "field_name": "vector", "index_name": "vector", "total_rows": 1000000, "indexed_rows": 1000000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **milvus / autoindex** (4-bit + FP16 refine: AUTOINDEX, the quick setup (Episode 2's default)): `{"index": {"index_type": "AUTOINDEX", "metric_type": "COSINE", "field_name": "vector", "index_name": "vector", "total_rows": 1000000, "indexed_rows": 1000000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": ["[index_type=HNSW_SQ] [sq_type=SQ4U] [refine=true] [refine_type=FP16] [metric_type=COSINE] [traceID=7f7099e44b322e5d80323a77f42b33be] [spanID=aedc1536e0dfc1b0]"], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params"`
- **milvus / ivf_rabitq** (1-bit + SQ8 refine: IVF_RABITQ with the docs' refine for 0.9+ recall): `{"index": {"refine": "True", "refine_type": "SQ8", "metric_type": "COSINE", "index_type": "IVF_RABITQ", "field_name": "vector", "index_name": "vector", "total_rows": 1000000, "indexed_rows": 1000000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **weaviate / none** (float32: no compression (default; DEFAULT_QUANTIZATION unset)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq8** (8-bit: rotational quantization (rq(), the docs' first example)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq4** (4-bit: RQ bits=4 (new in 1.40)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq1** (1-bit: RQ bits=1): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / bq** (1-bit: binary quantization): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": true}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segmen`
- **elasticsearch / hnsw** (float32: index_options type hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 14}`
- **elasticsearch / int8_hnsw** (8-bit: int8_hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "int8_hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 16}`
- **elasticsearch / int4_hnsw** (4-bit: int4_hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "int4_hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 17}`
- **elasticsearch / bbq_hnsw** (1-bit: bbq_hnsw (the default for 384+ dimensions on this license; mapping left as shipped)): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "bbq_hnsw", "m": 16, "ef_construction": 100, "rescore_vector": {"oversample": 3.0}}, "meta": {}}, "segments": 17}`
- **chroma / default** (float32: the only option (no quantization setting in Chroma 1.5.9)): `{"version": "1.0.0", "configuration": {"hnsw": {"space": "cosine", "ef_construction": 100, "ef_search": 100, "max_neighbors": 16, "resize_factor": 1.2, "sync_threshold": 1000}, "spann": null, "embedding_function": {"type": "known", "name": "default", "config": {}}}}`

## Act 1: compression as shipped (no search parameters, all test questions)

| Database | Deployment | Recall | nDCG | Answers lost | Nearest missed | p50 ms | p95 ms | Disk GiB | Mem after load MiB | Ready min | Fits (GiB, shipped) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | vector | 0.916 | 0.694 | 134 | 149 | 5.6 | 7.8 | 13.87 | 437 | 9.5 | none of the ladder |
| pgvector | halfvec | 0.916 | 0.693 | 136 | 148 | 4.3 | 6.1 | 8.80 | 406 | 5.2 | none of the ladder |
| pgvector | bit | 0.841 | 0.666 | 216 | 227 | 4.7 | 6.7 | 6.66 | 369 | 2.0 | ≥ 2 |
| qdrant | none | 0.971 | 0.731 | 28 | 36 | 4.2 | 5.0 | 3.94 | 439 | 9.5 | ≥ 4 |
| qdrant | scalar | 0.952 | 0.727 | 37 | 36 | 2.3 | 2.9 | 5.85 | 1644 | 6.4 | ≥ 2 |
| qdrant | turbo4 | 0.941 | 0.723 | 48 | 35 | 1.8 | 2.1 | 4.43 | 976 | 6.3 | ≥ 1 |
| qdrant | turbo2 | 0.970 | 0.727 | 34 | 39 | 1.7 | 2.0 | 4.19 | 680 | 6.1 | ≥ 1 |
| qdrant | binary | 0.900 | 0.723 | 55 | 55 | 1.5 | 1.7 | 4.88 | 626 | 6.2 | ≥ 0.5 |
| qdrant | turbo1 | 0.951 | 0.726 | 44 | 57 | 1.6 | 1.8 | 4.88 | 718 | 6.0 | ≥ 0.5 |
| milvus | hnsw | 0.940 | 0.719 | 66 | 74 | 5.0 | 5.9 | 24.26 | 4779 | 64.3 | ≥ 8 |
| milvus | hnsw_sq8 | 0.930 | 0.719 | 63 | 83 | 2.8 | 3.5 | 17.36 | 1920 | 25.8 | ≥ 2 |
| milvus | autoindex | 0.911 | 0.709 | 96 | 113 | 1.8 | 2.5 | 20.83 | 3318 | 11.3 | ≥ 4 |
| milvus | ivf_rabitq | 0.886 | 0.694 | 146 | 163 | 89.1 | 107.2 | 18.14 | 1997 | 7.3 | ≥ 2 |
| weaviate | none | 0.978 | 0.732 | 22 | 24 | 2.7 | 3.5 | 4.29 | 8445 | 15.5 | ≥ 8 |
| weaviate | rq8 | 0.978 | 0.730 | 24 | 27 | 2.0 | 2.5 | 5.39 | 3432 | 6.5 | ≥ 2 |
| weaviate | rq4 | 0.978 | 0.730 | 25 | 29 | 1.8 | 2.3 | 4.86 | 2412 | 5.0 | ≥ 2 |
| weaviate | rq1 | 0.972 | 0.726 | 37 | 39 | 1.8 | 2.3 | 4.49 | 1487 | 4.1 | ≥ 2 |
| weaviate | bq | 0.950 | 0.723 | 49 | 49 | 1.9 | 2.5 | 4.54 | 1679 | 4.3 | ≥ 2 |
| elasticsearch | hnsw | 0.912 | 0.698 | 121 | 149 | 4.5 | 6.0 | 5.43 | 9194 | 32.1 | none of the ladder |
| elasticsearch | int8_hnsw | 0.893 | 0.697 | 128 | 136 | 3.4 | 5.3 | 6.48 | 9207 | 29.9 | none of the ladder |
| elasticsearch | int4_hnsw | 0.861 | 0.692 | 142 | 150 | 3.0 | 4.8 | 5.58 | 9136 | 29.1 | ≥ 2 |
| elasticsearch | bbq_hnsw | 0.901 | 0.704 | 106 | 118 | 3.1 | 4.9 | 5.54 | 9165 | 27.9 | ≥ 2 |
| chroma | default | 0.957 | 0.716 | 65 | 75 | 2.5 | 3.1 | 4.12 | 4623 | 19.3 | ≥ 8 |

## Act 2: re-scoring depth (c candidates; recall on the 1,000 seeded test questions, p50 ms)

| Database | Deployment | shipped | c=20 | c=30 | c=50 | c=100 | c=200 | c=500 | smallest c ≥ 0.95 / 0.99 / 0.995 / 0.9975 (tuning) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | vector | 0.913 / 5.6 | 0.857 / 2.9 | 0.895 / 3.7 | 0.922 / 5.3 | 0.951 / 8.9 | 0.967 / 15.6 | 1.000 / 2139.5* | 100 / — / — / — |
| pgvector | halfvec | 0.913 / 4.3 | 0.859 / 2.6 | 0.894 / 3.4 | 0.926 / 4.7 | 0.954 / 8.6 | 0.969 / 14.8 | 0.982 / 32.5 | 100 / — / — / — |
| pgvector | bit | 0.836 / 4.7 | 0.753 / 4.1 | 0.811 / 4.4 | 0.861 / 5.7 | 0.917 / 10.1 | 0.949 / 18.3 | 0.973 / 41.9 | 500 / — / — / — |
| qdrant | none | 0.969 / 4.2 | 0.899 / 2.1 | 0.925 / 2.4 | 0.949 / 3.1 | 0.969 / 4.2 | 0.982 / 6.0 | 0.990 / 10.7 | 50 / 500 / — / — |
| qdrant | scalar | 0.949 / 2.3 | 0.967 / 2.3 | 0.967 / 2.3 | 0.967 / 2.4 | 0.967 / 2.4 | 0.980 / 3.4 | 0.992 / 5.9 | 20 / 500 / — / — |
| qdrant | turbo4 | 0.937 / 1.8 | 0.966 / 1.8 | 0.966 / 1.8 | 0.966 / 1.9 | 0.966 / 2.0 | 0.980 / 2.7 | 0.991 / 4.5 | 20 / 500 / — / — |
| qdrant | turbo2 | 0.966 / 1.7 | 0.967 / 1.6 | 0.967 / 1.7 | 0.967 / 1.7 | 0.967 / 1.8 | 0.978 / 2.5 | 0.990 / 3.9 | 20 / 500 / — / — |
| qdrant | binary | 0.897 / 1.5 | 0.934 / 1.5 | 0.943 / 1.5 | 0.950 / 1.6 | 0.954 / 1.7 | 0.972 / 2.1 | 0.987 / 3.5 | 50 / — / — / — |
| qdrant | turbo1 | 0.949 / 1.6 | 0.955 / 1.6 | 0.956 / 1.6 | 0.957 / 1.7 | 0.957 / 1.7 | 0.973 / 2.2 | 0.988 / 3.5 | 20 / — / — / — |
| milvus | hnsw | 0.938 / 5.0 | 0.952 / 5.4 | 0.968 / 6.3 | 0.982 / 7.8 | 0.992 / 11.4 | 0.996 / 17.4 | 0.999 / 30.5 | 20 / 100 / 200 / 500 |
| milvus | hnsw_sq8 | 0.924 / 2.8 | 0.939 / 3.0 | 0.958 / 3.4 | 0.972 / 4.0 | 0.983 / 5.3 | 0.990 / 7.1 | 0.993 / 11.2 | 30 / 200 / — / — |
| milvus | autoindex | 0.907 / 1.8 | 0.923 / 1.9 | 0.945 / 2.1 | 0.965 / 2.4 | 0.981 / 3.3 | 0.990 / 4.6 | 0.996 / 7.0 | 50 / 200 / 500 / — |
| milvus | ivf_rabitq | 0.882 / 88.8 | 0.939 / 168.1 | 0.962 / 245.9 | 0.980 / 392.8* | 0.989 / 774.9* | 0.993 / 1248.5* | 0.993 / 1248.3* | 30 / — / — / — |
| weaviate | none | 0.979 / 2.7 | 0.912 / 1.2 | 0.941 / 1.4 | 0.959 / 1.8 | 0.979 / 2.7 | 0.986 / 4.3 | 0.992 / 8.2 | 50 / 500 / — / — |
| weaviate | rq8 | 0.978 / 2.0 | 0.915 / 1.1 | 0.943 / 1.2 | 0.958 / 1.5 | 0.978 / 2.1 | 0.986 / 3.3 | 0.992 / 6.4 | 50 / 500 / — / — |
| weaviate | rq4 | 0.977 / 1.8 | 0.916 / 1.0 | 0.940 / 1.2 | 0.959 / 1.4 | 0.977 / 1.9 | 0.987 / 3.0 | 0.993 / 5.6 | 50 / 500 / — / — |
| weaviate | rq1 | 0.971 / 1.8 | 0.859 / 1.0 | 0.905 / 1.1 | 0.946 / 1.4 | 0.971 / 1.8 | 0.983 / 2.8 | 0.990 / 5.3 | 100 / — / — / — |
| weaviate | bq | 0.945 / 1.9 | 0.765 / 1.0 | 0.841 / 1.1 | 0.902 / 1.3 | 0.945 / 1.9 | 0.970 / 2.9 | 0.987 / 5.4 | 200 / — / — / — |
| elasticsearch | hnsw | 0.910 / 4.4 | 0.919 / 4.0 | 0.931 / 4.1 | 0.944 / 4.4 | 0.960 / 5.0 | 0.970 / 5.8 | 0.978 / 6.9 | 100 / — / — / — |
| elasticsearch | int8_hnsw | 0.888 / 3.4 | 0.914 / 3.2 | 0.925 / 3.0 | 0.941 / 3.2 | 0.956 / 3.5 | 0.968 / 3.9 | 0.978 / 4.8 | 100 / — / — / — |
| elasticsearch | int4_hnsw | 0.854 / 3.0 | 0.916 / 2.8 | 0.927 / 2.8 | 0.941 / 2.9 | 0.956 / 3.1 | 0.967 / 3.4 | 0.974 / 4.1 | 100 / — / — / — |
| elasticsearch | bbq_hnsw | 0.897 / 3.1 | 0.850 / 2.4 | 0.897 / 2.4 | 0.928 / 2.5 | 0.950 / 2.7 | 0.963 / 2.9 | 0.975 / 3.5 | 100 / — / — / — |
| chroma | default | 0.955 / 2.5 | 0.856 / 1.6 | 0.892 / 1.7 | 0.924 / 1.9 | 0.955 / 2.5 | 0.970 / 3.6 | 0.984 / 6.2 | 100 / — / — / — |

(* sampled: stopped by the speed guard)

## The memory ladder (200 test questions per step; p50 ms / recall; ✓ fits = runs, answers all, p50 within 2× or 5 ms of its 16 GiB p50)

| Database | Deployment | Setting | 16 GiB | 8 GiB | 4 GiB | 2 GiB | 1 GiB | 0.5 GiB |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| pgvector | vector | shipped | 5.5 | slow 23.3 / 0.908 | slow 42.7 / 0.908 | slow 45.7 / 0.908 | slow 58.1 / 0.908 | slow 66.7 / 0.908 |
| pgvector | vector | tuned (c=200, never reaches its level) | 16.1 | slow 44.1 / 0.963 | slow 80.8 / 0.963 | slow 156.9 / 0.963 | slow 197.9 / 0.963 | slow 235.2 / 0.963 |
| pgvector | halfvec | shipped | 4.4 | slow 18.5 / 0.910 | slow 36.2 / 0.910 | slow 42.1 / 0.910 | slow 74.1 / 0.910 | slow 97.8 / 0.910 |
| pgvector | halfvec | tuned (c=500, never reaches its level) | 33.3 | ✓ 36.9 / 0.976 | ✓ 40.0 / 0.976 | ✗ slow 256 | ✗ slow 554 | ✗ slow 795 |
| pgvector | bit | shipped | 4.7 | ✓ 4.6 / 0.809 | ✓ 7.2 / 0.809 | ✓ 9.3 / 0.809 | slow 9.9 / 0.809 | slow 32.5 / 0.809 |
| pgvector | bit | tuned (c=500, never reaches its level) | 43.3 | ✓ 41.4 / 0.966 | ✓ 68.1 / 0.966 | ✓ 79.8 / 0.966 | slow 94.8 / 0.966 | ✗ slow 332 |
| qdrant | none | shipped | 4.3 | ✓ 4.3 / 0.960 | ✓ 9.0 / 0.960 | slow 158.3 / 0.960 | slow 216.2 / 0.960 | slow 244.4 / 0.960 |
| qdrant | none | tuned (c=500, never reaches its level) | 10.9 | ✓ 11.0 / 0.991 | ✓ 12.7 / 0.991 | ✗ slow 612 | ✗ slow 813 | ✗ slow 912 |
| qdrant | scalar | shipped | 2.3 | ✓ 2.5 / 0.947 | ✓ 2.2 / 0.947 | ✓ 2.4 / 0.947 | ✗ OOM | · |
| qdrant | scalar | tuned (c=500, never reaches its level) | 5.9 | ✓ 5.7 / 0.991 | slow 18.5 / 0.991 | slow 49.8 / 0.991 | ✗ OOM | · |
| qdrant | turbo4 | shipped | 1.8 | ✓ 1.9 / 0.936 | ✓ 2.0 / 0.936 | ✓ 1.9 / 0.936 | ✓ 1.9 / 0.936 | ✗ OOM |
| qdrant | turbo4 | tuned (c=500, never reaches its level) | 4.4 | ✓ 4.6 / 0.989 | slow 15.5 / 0.989 | slow 48.6 / 0.989 | slow 65.2 / 0.989 | ✗ OOM |
| qdrant | turbo2 | shipped | 1.7 | ✓ 1.7 / 0.963 | ✓ 2.0 / 0.963 | ✓ 2.5 / 0.963 | ✓ 5.2 / 0.963 | slow 6.9 / 0.963 |
| qdrant | turbo2 | tuned (c=500, never reaches its level) | 3.8 | ✓ 3.9 / 0.991 | slow 10.0 / 0.991 | slow 38.5 / 0.991 | slow 61.5 / 0.991 | slow 85.6 / 0.991 |
| qdrant | binary | shipped | 1.5 | ✓ 1.5 / 0.872 | ✓ 1.8 / 0.872 | ✓ 2.5 / 0.872 | ✓ 2.8 / 0.872 | ✓ 5.9 / 0.872 |
| qdrant | binary | tuned (c=500, never reaches its level) | 3.6 | ✓ 3.6 / 0.985 | ✓ 7.4 / 0.985 | slow 43.4 / 0.985 | slow 57.8 / 0.985 | slow 86.5 / 0.985 |
| qdrant | turbo1 | shipped | 1.6 | ✓ 1.6 / 0.945 | ✓ 1.9 / 0.945 | ✓ 2.8 / 0.945 | ✓ 3.0 / 0.945 | ✓ 4.6 / 0.945 |
| qdrant | turbo1 | tuned (c=500, never reaches its level) | 3.5 | ✓ 3.7 / 0.985 | slow 8.7 / 0.985 | slow 40.6 / 0.985 | slow 57.0 / 0.985 | slow 69.0 / 0.985 |
| milvus | hnsw | shipped | 5.0 | ✓ 5.1 / 0.933 | ✗ did not start | · | · | · |
| milvus | hnsw | tuned (c=200) | 17.2 | ✓ 16.9 / 0.996 | ✗ did not start | · | · | · |
| milvus | hnsw | tuned_hi (c=500) | 31.1 | ✓ 30.3 / 0.999 | ✗ did not start | · | · | · |
| milvus | hnsw_sq8 | shipped | 2.8 | ✓ 2.6 / 0.915 | ✓ 2.9 / 0.915 | ✓ 2.6 / 0.915 | ✗ did not start | · |
| milvus | hnsw_sq8 | tuned (c=500, never reaches its level) | 11.3 | ✓ 11.2 / 0.992 | ✓ 11.4 / 0.992 | ✓ 11.3 / 0.992 | ✗ did not start | · |
| milvus | autoindex | shipped | 1.9 | ✓ 1.9 / 0.895 | ✓ 2.3 / 0.895 | ✗ did not start | · | · |
| milvus | autoindex | tuned (c=500) | 6.9 | ✓ 6.8 / 0.995 | ✓ 7.5 / 0.995 | ✗ did not start | · | · |
| milvus | ivf_rabitq | shipped | 91.2 | ✓ 90.5 / 0.883 | ✓ 90.8 / 0.883 | ✓ 90.9 / 0.883 | ✗ did not start | · |
| milvus | ivf_rabitq | tuned (c=30, never reaches its level) | 246.7 | ✓ 246.4 / 0.963 | ✓ 246.7 / 0.963 | ✓ 246.6 / 0.963 | ✗ did not start | · |
| weaviate | none | shipped | 2.7 | ✓ 2.9 / 0.975 | ✗ OOM | · | · | · |
| weaviate | none | tuned (c=500, never reaches its level) | 8.4 | ✓ 8.5 / 0.990 | ✗ OOM | · | · | · |
| weaviate | rq8 | shipped | 2.0 | ✓ 2.1 / 0.974 | ✓ 2.7 / 0.974 | ✓ 3.1 / 0.974 | ✗ OOM | · |
| weaviate | rq8 | tuned (c=500, never reaches its level) | 6.5 | ✓ 7.8 / 0.991 | slow 16.1 / 0.991 | slow 31.1 / 0.991 | ✗ OOM | · |
| weaviate | rq4 | shipped | 1.8 | ✓ 1.8 / 0.974 | ✓ 2.3 / 0.974 | ✓ 2.7 / 0.974 | ✗ OOM | · |
| weaviate | rq4 | tuned (c=500, never reaches its level) | 5.6 | ✓ 5.3 / 0.990 | slow 12.2 / 0.990 | slow 21.3 / 0.990 | ✗ OOM | · |
| weaviate | rq1 | shipped | 1.9 | ✓ 1.8 / 0.965 | ✓ 3.1 / 0.965 | ✓ 5.1 / 0.965 | slow 8.0 / 0.965 | ✗ OOM |
| weaviate | rq1 | tuned (c=500, never reaches its level) | 5.3 | ✓ 5.0 / 0.991 | ✓ 9.5 / 0.991 | slow 19.2 / 0.991 | slow 33.6 / 0.991 | ✗ OOM |
| weaviate | bq | shipped | 1.9 | ✓ 1.8 / 0.933 | ✓ 3.1 / 0.933 | ✓ 4.9 / 0.933 | slow 7.3 / 0.933 | ✗ OOM |
| weaviate | bq | tuned (c=500, never reaches its level) | 5.5 | ✓ 5.1 / 0.987 | ✓ 9.4 / 0.987 | slow 19.1 / 0.987 | slow 30.4 / 0.987 | ✗ OOM |
| elasticsearch | hnsw | shipped | 4.1 | slow 26.7 / 0.897 | slow 64.4 / 0.897 | slow 95.9 / 0.897 | slow 116.0 / 0.897 | ✗ OOM |
| elasticsearch | hnsw | tuned (c=500, never reaches its level) | 6.9 | slow 68.2 / 0.970 | ✗ slow 257 | ✗ slow 392 | ✗ slow 475 | ✗ OOM |
| elasticsearch | int8_hnsw | shipped | 3.0 | slow 17.5 / 0.882 | slow 10.0 / 0.882 | slow 39.2 / 0.882 | slow 74.5 / 0.882 | ✗ OOM |
| elasticsearch | int8_hnsw | tuned (c=500, never reaches its level) | 4.9 | slow 18.9 / 0.974 | slow 29.2 / 0.974 | slow 189.0 / 0.974 | ✗ slow 330 | ✗ OOM |
| elasticsearch | int4_hnsw | shipped | 2.7 | ✓ 5.4 / 0.842 | ✓ 6.3 / 0.842 | ✓ 6.3 / 0.842 | slow 64.1 / 0.842 | ✗ OOM |
| elasticsearch | int4_hnsw | tuned (c=500, never reaches its level) | 4.2 | slow 10.4 / 0.969 | slow 15.2 / 0.969 | slow 88.3 / 0.969 | ✗ slow 271 | ✗ OOM |
| elasticsearch | bbq_hnsw | shipped | 2.8 | ✓ 5.9 / 0.892 | ✓ 6.7 / 0.892 | ✓ 6.3 / 0.892 | slow 51.1 / 0.892 | ✗ OOM |
| elasticsearch | bbq_hnsw | tuned (c=500, never reaches its level) | 3.5 | slow 10.9 / 0.976 | slow 14.6 / 0.976 | slow 18.5 / 0.976 | slow 200.2 / 0.976 | ✗ OOM |
| chroma | default | shipped | 2.5 | ✓ 2.5 / 0.950 | ✗ OOM | · | · | · |
| chroma | default | tuned (c=500, never reaches its level) | 6.3 | ✓ 6.3 / 0.982 | · | · | · | · |

## Act 3: the recall target from the labels (tuning questions, every deployment and setting)

| Target | Settings reaching it | Worst nDCG loss (points) | Within 0.5? |
| ---: | ---: | ---: | :--- |
| 0.8 | 154 | 7.21 | no |
| 0.85 | 151 | 7.21 | no |
| 0.9 | 138 | 4.74 | no |
| 0.95 | 95 | 2.32 | no |
| 0.97 | 63 | 1.46 | no |
| 0.99 | 14 | 0.53 | no |
| 0.995 | 3 | 0.04 | yes |

Target: **0.995**.

Act 3 checks the `tuned_hi` setting (tuned to 0.9975 on tuning questions).

## Act 3: built: per database and memory budget, the fastest deployment whose tuned setting passes the deploy check under that limit (recall ≥ 0.995, all answered, p50 within 2× or 5 ms of its 16 GiB p50; 200 test questions)

| Database | Budget GiB | Deployment (c) | Check recall | Check p50 ms | Recall (1,000 test) | nDCG | Answers lost | Others that pass |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | 4 | none passes | | | | | | |
| pgvector | 2 | none passes | | | | | | |
| pgvector | 1 | none passes | | | | | | |
| qdrant | 4 | none passes | | | | | | |
| qdrant | 2 | none passes | | | | | | |
| qdrant | 1 | none passes | | | | | | |
| milvus | 4 | none passes | | | | | | |
| milvus | 2 | none passes | | | | | | |
| milvus | 1 | none passes | | | | | | |
| weaviate | 4 | none passes | | | | | | |
| weaviate | 2 | none passes | | | | | | |
| weaviate | 1 | none passes | | | | | | |
| elasticsearch | 4 | none passes | | | | | | |
| elasticsearch | 2 | none passes | | | | | | |
| elasticsearch | 1 | none passes | | | | | | |
| chroma | 4 | none passes | | | | | | |
| chroma | 2 | none passes | | | | | | |
| chroma | 1 | none passes | | | | | | |


**Exploratory, after the results: the same check at a 0.99 target**, any setting the ladder measured (as shipped or the tuned c), check recall ≥ 0.99, all answered, the same speed rule. p50 in ms at that limit; slower or failing settings are left out.

| Database | 8 GiB | 4 GiB | 2 GiB | 1 GiB |
| :--- | :--- | :--- | :--- | :--- |
| pgvector | — | — | — | — |
| qdrant | turbo2 c=500 3.9 (0.991), scalar c=500 5.7 (0.991), none c=500 11.0 (0.991) | none c=500 12.7 (0.991) | — | — |
| milvus | autoindex c=500 6.8 (0.995), hnsw_sq8 c=500 11.2 (0.992), hnsw c=200 16.9 (0.996), hnsw c=500 30.3 (0.999) | autoindex c=500 7.5 (0.995), hnsw_sq8 c=500 11.4 (0.992) | hnsw_sq8 c=500 11.3 (0.992) | — |
| weaviate | rq1 c=500 5.0 (0.991), rq4 c=500 5.3 (0.990), rq8 c=500 7.8 (0.991), none c=500 8.5 (0.990) | rq1 c=500 9.5 (0.991) | — | — |
| elasticsearch | — | — | — | — |
| chroma | — | — | — | — |

## The vectors alone: Cohere v3, the million, exact search over each representation (test questions)

| Representation | Bytes/vector | Recall (own top 10) | nDCG | Answers lost | Re-scored c=20 | c=50 | c=100 (recall / lost) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| float32 | 4096 | 1.000 | 0.739 | 0 |  |  |  |
| float16 | 2048 | 1.000 | 0.739 | 0 | 1.000 / 0 | 1.000 / 0 | 1.000 / 0 |
| int8 | 1024 | 0.995 | 0.739 | 0 | 1.000 / 0 | 1.000 / 0 | 1.000 / 0 |
| int4 | 512 | 0.925 | 0.734 | 20 | 0.999 / 0 | 1.000 / 0 | 1.000 / 0 |
| 1bit_hamming | 128 | 0.652 | 0.676 | 119 | 0.820 / 51 | 0.934 / 12 | 0.971 / 4 |
| 1bit_float_query | 128 | 0.757 | 0.709 | 58 | 0.923 / 8 | 0.986 / 1 | 0.997 / 0 |
| dims512 | 2048 | 0.701 | 0.707 | 89 | 0.868 / 32 | 0.957 / 14 | 0.983 / 8 |
| dims256 | 1024 | 0.501 | 0.631 | 261 | 0.643 / 163 | 0.779 / 95 | 0.851 / 58 |
| dims128 | 512 | 0.278 | 0.458 | 718 | 0.362 / 569 | 0.469 / 409 | 0.552 / 315 |

## The vectors alone: Matryoshka on the 100,000 subset (test questions; each model against its own exact search)

| Model | Dims | Precision | Bytes | Recall | nDCG | Answers lost | Re-scored c=50 | c=100 (recall / nDCG) |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| cohere | 1024 | float32 | 4096 | 1.000 | 0.909 | 0 | 1.000 / 0.909 | 1.000 / 0.909 |
| cohere | 1024 | int8 | 1024 | 0.995 | 0.909 | 0 | 1.000 / 0.909 | 1.000 / 0.909 |
| cohere | 1024 | 1bit | 128 | 0.612 | 0.878 | 41 | 0.914 / 0.909 | 0.964 / 0.909 |
| cohere | 512 | float32 | 2048 | 0.649 | 0.887 | 37 | 0.942 / 0.909 | 0.979 / 0.909 |
| cohere | 512 | int8 | 512 | 0.649 | 0.887 | 37 | 0.943 / 0.909 | 0.979 / 0.909 |
| cohere | 512 | 1bit | 64 | 0.431 | 0.810 | 148 | 0.707 / 0.896 | 0.802 / 0.902 |
| cohere | 256 | float32 | 1024 | 0.445 | 0.831 | 128 | 0.727 / 0.897 | 0.819 / 0.903 |
| cohere | 256 | int8 | 256 | 0.445 | 0.831 | 127 | 0.727 / 0.897 | 0.819 / 0.903 |
| cohere | 256 | 1bit | 32 | 0.247 | 0.634 | 477 | 0.428 / 0.825 | 0.516 / 0.852 |
| cohere | 128 | float32 | 512 | 0.249 | 0.660 | 430 | 0.430 / 0.826 | 0.522 / 0.851 |
| cohere | 128 | int8 | 128 | 0.250 | 0.661 | 429 | 0.430 / 0.825 | 0.522 / 0.851 |
| cohere | 128 | 1bit | 16 | 0.102 | 0.314 | 1288 | 0.192 / 0.578 | 0.249 / 0.636 |
| cohere | 64 | float32 | 256 | 0.098 | 0.329 | 1242 | 0.184 / 0.573 | 0.241 / 0.637 |
| cohere | 64 | int8 | 64 | 0.098 | 0.329 | 1242 | 0.184 / 0.571 | 0.241 / 0.637 |
| cohere | 64 | 1bit | 8 | 0.026 | 0.071 | 2074 | 0.065 / 0.242 | 0.093 / 0.301 |
| nomic | 768 | float32 | 3072 | 1.000 | 0.895 | 0 | 1.000 / 0.895 | 1.000 / 0.895 |
| nomic | 768 | int8 | 768 | 0.993 | 0.895 | 0 | 1.000 / 0.895 | 1.000 / 0.895 |
| nomic | 768 | 1bit | 96 | 0.555 | 0.842 | 85 | 0.854 / 0.892 | 0.921 / 0.894 |
| nomic | 512 | float32 | 2048 | 0.830 | 0.892 | 11 | 0.999 / 0.895 | 1.000 / 0.895 |
| nomic | 512 | int8 | 512 | 0.830 | 0.892 | 11 | 0.999 / 0.895 | 1.000 / 0.895 |
| nomic | 512 | 1bit | 64 | 0.464 | 0.802 | 136 | 0.747 / 0.886 | 0.834 / 0.889 |
| nomic | 256 | float32 | 1024 | 0.703 | 0.878 | 33 | 0.969 / 0.894 | 0.989 / 0.895 |
| nomic | 256 | int8 | 256 | 0.702 | 0.878 | 33 | 0.969 / 0.894 | 0.989 / 0.895 |
| nomic | 256 | 1bit | 32 | 0.312 | 0.674 | 376 | 0.535 / 0.844 | 0.632 / 0.860 |
| nomic | 128 | float32 | 512 | 0.584 | 0.856 | 69 | 0.888 / 0.892 | 0.947 / 0.894 |
| nomic | 128 | int8 | 128 | 0.584 | 0.855 | 69 | 0.888 / 0.892 | 0.947 / 0.894 |
| nomic | 128 | 1bit | 16 | 0.190 | 0.467 | 836 | 0.343 / 0.720 | 0.425 / 0.767 |
| nomic | 64 | float32 | 256 | 0.436 | 0.789 | 176 | 0.730 / 0.881 | 0.822 / 0.886 |
| nomic | 64 | int8 | 64 | 0.437 | 0.788 | 177 | 0.730 / 0.882 | 0.822 / 0.886 |
| nomic | 64 | 1bit | 8 | 0.100 | 0.227 | 1507 | 0.201 / 0.501 | 0.263 / 0.567 |

