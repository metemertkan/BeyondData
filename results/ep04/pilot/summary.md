# Episode 4 summary (pilot: 100,000 passages)

Exact float32 search, test questions: nDCG@10 0.909, hit@10 0.977.

## Settings read back

- **pgvector / vector** (float32: HNSW on the vector column (README)): `{"version": "0.8.7", "index": "CREATE INDEX docs_embedding_idx ON public.docs USING hnsw (embedding vector_cosine_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 818954240, "table_bytes": 559128576, "toast_bytes": 553074688, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=2754.14..2794.35 rows=10 width=16) / ->  Index Scan using docs_embedding_idx on docs  (cost=2754.14..404824.00 rows=100000 width=16)"}`
- **pgvector / halfvec** (16-bit: HNSW on embedding::halfvec(1024) (README, half-precision indexing)): `{"version": "0.8.7", "index": "CREATE INDEX docs_embedding_idx ON public.docs USING hnsw (((embedding)::halfvec(1024)) halfvec_cosine_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 272990208, "table_bytes": 559128576, "toast_bytes": 553074688, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=921.50..935.26 rows=10 width=16) / ->  Index Scan using docs_embedding_idx on docs  (cost=921.50..138490.00 rows=100000 width=16)"}`
- **pgvector / bit** (1-bit: HNSW on binary_quantize(embedding)::bit(1024), the README's re-rank query): `{"version": "0.8.7", "index": "CREATE INDEX docs_binary_quantize_idx ON public.docs USING hnsw (((binary_quantize(embedding))::bit(1024)) bit_hamming_ops)", "reloptions (empty = m 16, ef_construction 64)": null, "index_bytes": 43474944, "table_bytes": 559120384, "toast_bytes": 553066496, "hnsw.ef_search": "40", "shared_buffers": "128MB", "plan": "Limit  (cost=163.06..163.09 rows=10 width=16) / ->  Sort  (cost=163.06..163.16 rows=40 width=16) / Sort Key: ((t.embedding <=> '[...]'::vector)) / ->  Subquery Scan on t  (cost=151.09..162.20 rows=40 width=16) / ->  Limit  (cost=151.09..161.70 rows=40`
- **qdrant / none** (float32: no quantization (default)): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / scalar** (8-bit: scalar int8): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo4** (4-bit: TurboQuant bits4): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo2** (2-bit: TurboQuant bits2): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / binary** (1-bit: binary quantization (the docs' first example)): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **qdrant / turbo1** (1-bit: TurboQuant bits1): `{"status": "green", "segments_count": 6, "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine", "hnsw_config": null, "quantization_config": null, "on_disk": null, "memory": null, "datatype": null, "multivector_config": null}, "shard_number": 1, "sharding_method": null, "replication_factor": 1, "write_consistency_factor": 1, "read_fan_out_factor": null, "read_fan_out_delay_ms": null, "on_disk_payload": true, "payload": null, "id_tracker": null, "sparse_vectors": null}, "hnsw_config": {"m": 16, "ef_construct": 100, "full_scan_threshold": 10000, "max_indexing_threads": 0, "on_disk"`
- **milvus / hnsw** (float32: HNSW): `{"index": {"metric_type": "COSINE", "index_type": "HNSW", "field_name": "vector", "index_name": "vector", "total_rows": 100000, "indexed_rows": 100000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **milvus / hnsw_sq8** (8-bit: HNSW_SQ (sq_type default SQ8, no refine)): `{"index": {"metric_type": "COSINE", "index_type": "HNSW_SQ", "field_name": "vector", "index_name": "vector", "total_rows": 100000, "indexed_rows": 100000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **milvus / autoindex** (4-bit + FP16 refine: AUTOINDEX, the quick setup (Episode 2's default)): `{"index": {"index_type": "AUTOINDEX", "metric_type": "COSINE", "field_name": "vector", "index_name": "vector", "total_rows": 100000, "indexed_rows": 100000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": ["[index_type=HNSW_SQ] [sq_type=SQ4U] [refine=true] [refine_type=FP16] [metric_type=COSINE] [traceID=3d5fc1a7fbc2e9a15dd45793f775be3b] [spanID=8a2e2316d925605e]"], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": `
- **milvus / ivf_rabitq** (1-bit + SQ8 refine: IVF_RABITQ with the docs' refine for 0.9+ recall): `{"index": {"refine": "True", "refine_type": "SQ8", "metric_type": "COSINE", "index_type": "IVF_RABITQ", "field_name": "vector", "index_name": "vector", "total_rows": 100000, "indexed_rows": 100000, "pending_index_rows": 0, "state": "Finished"}, "autoindex_built_as": [], "consistency_level": 2, "fields": [{"field_id": 100, "name": "id", "description": "", "type": 5, "params": {}, "is_primary": true}, {"field_id": 101, "name": "vector", "description": "", "type": 101, "params": {"dim": 1024}}]}`
- **weaviate / none** (float32: no compression (default; DEFAULT_QUANTIZATION unset)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq8** (8-bit: rotational quantization (rq(), the docs' first example)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq4** (4-bit: RQ bits=4 (new in 1.40)): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / rq1** (1-bit: RQ bits=1): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": false}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segme`
- **weaviate / bq** (1-bit: binary quantization): `{"version": "1.40.7", "vectorConfig": {"default": {"vectorIndexConfig": {"bq": {"enabled": true}, "cleanupIntervalSeconds": 300, "distance": "cosine", "dynamicEfFactor": 8, "dynamicEfMax": 500, "dynamicEfMin": 100, "ef": -1, "efConstruction": 128, "filterStrategy": "acorn", "flatSearchCutoff": 40000, "maxConnections": 32, "multivector": {"aggregation": "maxSim", "enabled": false, "muvera": {"dprojections": 16, "enabled": false, "ksim": 4, "repetitions": 10}}, "pq": {"bitCompression": false, "centroids": 256, "enabled": false, "encoder": {"distribution": "log-normal", "type": "kmeans"}, "segmen`
- **elasticsearch / hnsw** (float32: index_options type hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 11}`
- **elasticsearch / int8_hnsw** (8-bit: int8_hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "int8_hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 10}`
- **elasticsearch / int4_hnsw** (4-bit: int4_hnsw): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "int4_hnsw", "m": 16, "ef_construction": 100}, "meta": {}}, "segments": 10}`
- **elasticsearch / bbq_hnsw** (1-bit: bbq_hnsw (the default for 384+ dimensions on this license; mapping left as shipped)): `{"version": "9.5.5", "license": "basic", "mapping": {"type": "dense_vector", "element_type": "float", "dims": 1024, "index": true, "similarity": "cosine", "index_options": {"type": "bbq_hnsw", "m": 16, "ef_construction": 100, "rescore_vector": {"oversample": 3.0}}, "meta": {}}, "segments": 5}`
- **chroma / default** (float32: the only option (no quantization setting in Chroma 1.5.9)): `{"version": "1.0.0", "configuration": {"hnsw": {"space": "cosine", "ef_construction": 100, "ef_search": 100, "max_neighbors": 16, "resize_factor": 1.2, "sync_threshold": 1000}, "spann": null, "embedding_function": {"type": "known", "name": "default", "config": {}}}}`

## Act 1: compression as shipped (no search parameters, all test questions)

| Database | Deployment | Recall | nDCG | Answers lost | Nearest missed | p50 ms | p95 ms | Disk GiB | Mem after load MiB | Ready min | Fits (GiB, shipped) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | vector | 0.954 | 0.882 | 73 | 69 | 3.4 | 4.7 | 2.19 | 232 | 1.8 | ≥ 1 |
| pgvector | halfvec | 0.954 | 0.883 | 70 | 65 | 2.6 | 3.5 | 1.48 | 208 | 1.5 | ≥ 0.5 |
| pgvector | bit | 0.860 | 0.871 | 109 | 104 | 1.2 | 1.5 | 1.09 | 200 | 0.7 | ≥ 0.5 |
| qdrant | none | 0.994 | 0.908 | 6 | 3 | 3.8 | 4.6 | 5.02 | 505 | 0.8 | ≥ 0.5 |
| qdrant | scalar | 0.974 | 0.907 | 8 | 4 | 1.9 | 2.3 | 0.77 | 378 | 0.6 | ≥ 0.5 |
| qdrant | turbo4 | 0.959 | 0.906 | 12 | 6 | 1.6 | 1.9 | 0.72 | 360 | 0.7 | ≥ 0.5 |
| qdrant | turbo2 | 0.994 | 0.906 | 9 | 8 | 1.4 | 1.7 | 6.04 | 289 | 0.7 | ≥ 0.5 |
| qdrant | binary | 0.905 | 0.904 | 22 | 15 | 1.3 | 1.6 | 6.13 | 553 | 0.6 | ≥ 0.5 |
| qdrant | turbo1 | 0.983 | 0.907 | 6 | 6 | 1.4 | 1.7 | 5.97 | 533 | 0.6 | ≥ 0.5 |
| milvus | hnsw | 0.933 | 0.886 | 66 | 58 | 1.7 | 2.5 | 2.51 | 785 | 7.8 | ≥ 1 |
| milvus | hnsw_sq8 | 0.924 | 0.885 | 69 | 66 | 1.3 | 1.7 | 1.99 | 480 | 5.4 | ≥ 0.5 |
| milvus | autoindex | 0.849 | 0.871 | 111 | 103 | 1.2 | 1.7 | 2.26 | 632 | 4.8 | ≥ 1 |
| milvus | ivf_rabitq | 0.703 | 0.838 | 187 | 188 | 36.0 | 48.6 | 1.99 | 666 | 4.4 | ≥ 0.5 |
| weaviate | none | 0.990 | 0.905 | 13 | 9 | 2.3 | 2.9 | 0.48 | 1062 | 1.3 | ≥ 1 |
| weaviate | rq8 | 0.990 | 0.904 | 15 | 10 | 1.6 | 2.0 | 0.58 | 678 | 0.5 | ≥ 0.5 |
| weaviate | rq4 | 0.991 | 0.906 | 11 | 6 | 1.3 | 1.7 | 0.53 | 432 | 0.4 | ≥ 0.5 |
| weaviate | rq1 | 0.986 | 0.904 | 17 | 11 | 1.5 | 1.8 | 0.49 | 300 | 0.4 | ≥ 0.5 |
| weaviate | bq | 0.957 | 0.903 | 21 | 12 | 1.4 | 1.8 | 0.46 | 296 | 0.4 | ≥ 0.5 |
| elasticsearch | hnsw | 0.968 | 0.897 | 33 | 34 | 4.2 | 5.9 | 0.64 | 8994 | 2.4 | ≥ 2 |
| elasticsearch | int8_hnsw | 0.947 | 0.890 | 47 | 42 | 3.0 | 5.0 | 0.68 | 8974 | 2.3 | ≥ 1 |
| elasticsearch | int4_hnsw | 0.902 | 0.893 | 39 | 34 | 2.9 | 4.9 | 0.65 | 8954 | 2.3 | ≥ 1 |
| elasticsearch | bbq_hnsw | 0.938 | 0.899 | 27 | 27 | 2.5 | 4.5 | 0.65 | 8928 | 2.2 | ≥ 1 |
| chroma | default | 0.978 | 0.897 | 33 | 28 | 2.4 | 2.9 | 0.42 | 537 | 1.3 | ≥ 0.5 |

## Act 2: re-scoring depth (c candidates; recall on the 1,000 seeded test questions, p50 ms)

| Database | Deployment | shipped | c=20 | c=30 | c=50 | c=100 | c=200 | c=500 | smallest c ≥ 0.95 / 0.99 / 0.995 / 0.9975 (tuning) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | vector | 0.955 / 3.4 | 0.913 / 2.1 | 0.941 / 2.8 | 0.961 / 4.1 | 0.981 / 6.9 | 0.989 / 12.1 | 0.995 / 26.3 | 50 / 500 / — / — |
| pgvector | halfvec | 0.954 / 2.6 | 0.916 / 1.7 | 0.941 / 2.2 | 0.961 / 3.0 | 0.980 / 5.1 | 0.989 / 8.8 | 0.995 / 18.7 | 50 / 500 / — / — |
| pgvector | bit | 0.857 / 1.2 | 0.764 / 0.9 | 0.827 / 1.1 | 0.886 / 1.5 | 0.942 / 2.7 | 0.975 / 5.2 | 0.992 / 12.4 | 200 / 500 / — / — |
| qdrant | none | 0.993 / 3.8 | 0.951 / 2.3 | 0.970 / 2.2 | 0.983 / 2.9 | 0.993 / 3.8 | 0.998 / 5.4 | 0.999 / 8.9 | 20 / 100 / 200 / 200 |
| qdrant | scalar | 0.974 / 1.9 | 0.994 / 1.9 | 0.994 / 2.0 | 0.994 / 1.9 | 0.994 / 2.0 | 0.998 / 2.8 | 1.000 / 4.5 | 20 / 20 / 200 / 200 |
| qdrant | turbo4 | 0.959 / 1.6 | 0.993 / 1.6 | 0.993 / 1.6 | 0.993 / 1.7 | 0.993 / 1.8 | 0.997 / 2.3 | 0.999 / 3.7 | 20 / 20 / 200 / 500 |
| qdrant | turbo2 | 0.993 / 1.4 | 0.993 / 1.5 | 0.993 / 1.5 | 0.993 / 1.5 | 0.993 / 1.6 | 0.998 / 2.0 | 0.999 / 3.3 | 20 / 20 / 200 / 500 |
| qdrant | binary | 0.904 / 1.3 | 0.954 / 1.4 | 0.970 / 1.4 | 0.982 / 1.4 | 0.987 / 1.5 | 0.995 / 1.8 | 0.999 / 2.9 | 20 / 200 / 200 / 500 |
| qdrant | turbo1 | 0.982 / 1.4 | 0.990 / 1.4 | 0.990 / 1.5 | 0.990 / 1.5 | 0.990 / 1.5 | 0.996 / 1.9 | 0.999 / 3.1 | 20 / 30 / 200 / 500 |
| milvus | hnsw | 0.933 / 1.7 | 0.948 / 1.8 | 0.969 / 2.3 | 0.986 / 2.7 | 0.995 / 3.9 | 0.997 / 5.2 | 0.999 / 8.1 | 30 / 100 / 100 / 200 |
| milvus | hnsw_sq8 | 0.922 / 1.3 | 0.941 / 1.4 | 0.960 / 1.5 | 0.977 / 1.8 | 0.988 / 2.4 | 0.993 / 3.2 | 0.994 / 5.8 | 30 / 100 / 500 / — |
| milvus | autoindex | 0.848 / 1.2 | 0.916 / 1.2 | 0.947 / 1.3 | 0.972 / 1.4 | 0.989 / 1.6 | 0.995 / 2.1 | 0.999 / 3.4 | 50 / 100 / 200 / 500 |
| milvus | ivf_rabitq | 0.705 / 36.2 | 0.878 / 68.7 | 0.935 / 101.0 | 0.969 / 164.6 | 0.989 / 317.8* | 0.998 / 514.1* | 0.998 / 514.5* | 50 / — / — / — |
| weaviate | none | 0.990 / 2.3 | 0.936 / 1.1 | 0.960 / 1.2 | 0.978 / 1.5 | 0.990 / 2.3 | 0.995 / 3.7 | 0.999 / 6.8 | 30 / 200 / 200 / 500 |
| weaviate | rq8 | 0.990 / 1.6 | 0.990 / 1.6 | 0.990 / 1.7 | 0.990 / 1.7 | 0.990 / 1.8 | 0.990 / 1.7 | 0.990 / 1.7 | 20 / — / — / — |
| weaviate | rq4 | 0.990 / 1.3 | 0.990 / 1.3 | 0.990 / 1.4 | 0.990 / 1.4 | 0.990 / 1.4 | 0.990 / 1.5 | 0.990 / 1.5 | 20 / — / — / — |
| weaviate | rq1 | 0.987 / 1.5 | 0.919 / 1.3 | 0.960 / 1.3 | 0.981 / 1.3 | 0.987 / 1.5 | 0.987 / 1.4 | 0.987 / 1.5 | 30 / — / — / — |
| weaviate | bq | 0.955 / 1.4 | 0.755 / 0.8 | 0.831 / 0.9 | 0.898 / 1.0 | 0.955 / 1.4 | 0.982 / 2.1 | 0.995 / 3.8 | 100 / 500 / 500 / — |
| elasticsearch | hnsw | 0.965 / 4.2 | 0.971 / 3.7 | 0.978 / 3.8 | 0.984 / 4.0 | 0.991 / 4.5 | 0.994 / 5.1 | 0.997 / 6.1 | 20 / 100 / 500 / — |
| elasticsearch | int8_hnsw | 0.944 / 3.0 | 0.972 / 2.6 | 0.978 / 2.5 | 0.985 / 2.6 | 0.991 / 2.8 | 0.994 / 3.3 | 0.997 / 3.9 | 20 / 100 / 500 / — |
| elasticsearch | int4_hnsw | 0.899 / 2.9 | 0.970 / 2.4 | 0.978 / 2.3 | 0.984 / 2.3 | 0.990 / 2.5 | 0.993 / 2.7 | 0.997 / 3.4 | 20 / 200 / 500 / — |
| elasticsearch | bbq_hnsw | 0.936 / 2.4 | 0.887 / 2.0 | 0.936 / 2.0 | 0.967 / 1.9 | 0.986 / 2.0 | 0.993 / 2.2 | 0.996 / 2.7 | 50 / 200 / 500 / — |
| chroma | default | 0.977 / 2.4 | 0.897 / 1.5 | 0.931 / 1.6 | 0.956 / 1.9 | 0.977 / 2.4 | 0.988 / 3.5 | 0.996 / 5.6 | 50 / 500 / 500 / — |

(* sampled: stopped by the speed guard)

## The memory ladder (200 test questions per step; p50 ms / recall; ✓ fits = runs, answers all, p50 within 2× or 5 ms of its 16 GiB p50)

| Database | Deployment | Setting | 16 GiB | 2 GiB | 1 GiB | 0.5 GiB |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| pgvector | vector | shipped | 3.2 | ✓ 5.2 / 0.953 | ✓ 6.7 / 0.953 | slow 33.0 / 0.953 |
| pgvector | vector | tuned (c=500, never reaches its level) | 26.7 | ✓ 26.6 / 0.994 | ✓ 28.6 / 0.994 | ✗ slow 268 |
| pgvector | halfvec | shipped | 2.6 | ✓ 2.4 / 0.951 | ✓ 3.6 / 0.951 | ✓ 3.7 / 0.951 |
| pgvector | halfvec | tuned (c=500, never reaches its level) | 18.9 | ✓ 18.4 / 0.994 | ✓ 20.5 / 0.994 | ✓ 20.1 / 0.994 |
| pgvector | bit | shipped | 1.2 | ✓ 1.4 / 0.857 | ✓ 2.9 / 0.857 | ✓ 4.2 / 0.857 |
| pgvector | bit | tuned (c=500, never reaches its level) | 12.3 | ✓ 13.5 / 0.992 | ✓ 15.2 / 0.992 | slow 28.0 / 0.992 |
| qdrant | none | shipped | 3.8 | ✓ 3.7 / 0.994 | ✓ 3.9 / 0.994 | ✓ 4.0 / 0.994 |
| qdrant | none | tuned (c=200) | 5.3 | ✓ 5.5 / 0.996 | ✓ 5.4 / 0.996 | ✓ 5.6 / 0.996 |
| qdrant | scalar | shipped | 1.8 | ✓ 2.1 / 0.970 | ✓ 1.9 / 0.970 | ✓ 2.0 / 0.970 |
| qdrant | scalar | tuned (c=200) | 2.8 | ✓ 3.1 / 1.000 | ✓ 2.9 / 1.000 | slow 8.3 / 1.000 |
| qdrant | turbo4 | shipped | 1.6 | ✓ 1.7 / 0.955 | ✓ 1.6 / 0.955 | ✓ 1.6 / 0.955 |
| qdrant | turbo4 | tuned (c=200) | 2.3 | ✓ 2.5 / 0.995 | ✓ 2.3 / 0.995 | ✓ 3.7 / 0.995 |
| qdrant | turbo2 | shipped | 1.4 | ✓ 1.5 / 0.991 | ✓ 1.4 / 0.991 | ✓ 1.9 / 0.991 |
| qdrant | turbo2 | tuned (c=200) | 2.0 | ✓ 2.1 / 0.998 | ✓ 2.2 / 0.998 | slow 8.3 / 0.998 |
| qdrant | binary | shipped | 1.3 | ✓ 1.4 / 0.900 | ✓ 1.4 / 0.900 | ✓ 1.8 / 0.900 |
| qdrant | binary | tuned (c=200) | 1.9 | ✓ 2.2 / 0.997 | ✓ 1.9 / 0.997 | ✓ 5.8 / 0.997 |
| qdrant | turbo1 | shipped | 1.4 | ✓ 1.4 / 0.982 | ✓ 1.4 / 0.982 | ✓ 1.8 / 0.982 |
| qdrant | turbo1 | tuned (c=200) | 1.9 | ✓ 2.0 / 0.997 | ✓ 1.9 / 0.997 | ✓ 5.0 / 0.997 |
| milvus | hnsw | shipped | 1.6 | ✓ 2.3 / 0.925 | ✓ 2.0 / 0.925 | ✗ did not start |
| milvus | hnsw | tuned (c=100) | 3.9 | ✓ 4.1 / 0.995 | ✓ 4.5 / 0.995 | ✗ failed |
| milvus | hnsw | tuned_hi (c=200) | 5.1 | ✓ 5.5 / 0.998 | ✓ 5.5 / 0.998 | ✗ failed |
| milvus | hnsw_sq8 | shipped | 1.3 | ✓ 1.8 / 0.909 | ✓ 1.7 / 0.909 | ✓ 1.6 / 0.909 |
| milvus | hnsw_sq8 | tuned (c=500) | 5.9 | ✓ 6.5 / 0.995 | ✓ 6.0 / 0.995 | ✓ 6.4 / 0.995 |
| milvus | autoindex | shipped | 1.2 | ✓ 1.5 / 0.840 | ✓ 1.5 / 0.840 | ✗ did not start |
| milvus | autoindex | tuned (c=200) | 2.1 | ✓ 2.3 / 0.998 | ✓ 2.7 / 0.998 | ✗ failed |
| milvus | autoindex | tuned_hi (c=500) | 3.7 | ✓ 4.5 / 0.999 | ✓ 4.5 / 0.999 | ✗ failed |
| milvus | ivf_rabitq | shipped | 37.2 | ✓ 37.6 / 0.692 | ✓ 37.7 / 0.692 | ✓ 38.0 / 0.692 |
| milvus | ivf_rabitq | tuned (c=50, never reaches its level) | 165.7 | ✓ 166.0 / 0.968 | ✓ 165.5 / 0.968 | ✓ 165.4 / 0.968 |
| weaviate | none | shipped | 2.3 | ✓ 2.3 / 0.987 | ✓ 2.4 / 0.987 | ✗ OOM 4 |
| weaviate | none | tuned (c=200) | 3.7 | ✓ 3.7 / 0.993 | ✓ 3.7 / 0.993 | · |
| weaviate | none | tuned_hi (c=500) | 6.9 | ✓ 6.9 / 0.999 | ✓ 6.9 / 0.999 | · |
| weaviate | rq8 | shipped | 1.6 | ✓ 1.6 / 0.985 | ✓ 1.5 / 0.985 | ✓ 2.2 / 0.985 |
| weaviate | rq8 | tuned (c=20, never reaches its level) | 1.6 | ✓ 1.5 / 0.985 | ✓ 1.6 / 0.985 | ✓ 1.7 / 0.985 |
| weaviate | rq4 | shipped | 1.3 | ✓ 1.3 / 0.985 | ✓ 1.4 / 0.985 | ✓ 1.7 / 0.985 |
| weaviate | rq4 | tuned (c=20, never reaches its level) | 1.3 | ✓ 1.4 / 0.985 | ✓ 1.3 / 0.985 | ✓ 1.5 / 0.985 |
| weaviate | rq1 | shipped | 1.4 | ✓ 1.4 / 0.986 | ✓ 1.4 / 0.986 | ✓ 1.8 / 0.986 |
| weaviate | rq1 | tuned (c=100, never reaches its level) | 1.5 | ✓ 1.4 / 0.986 | ✓ 1.4 / 0.986 | ✓ 1.5 / 0.986 |
| weaviate | bq | shipped | 1.4 | ✓ 1.4 / 0.952 | ✓ 1.5 / 0.952 | ✓ 1.9 / 0.952 |
| weaviate | bq | tuned (c=500) | 3.8 | ✓ 3.6 / 0.996 | ✓ 3.6 / 0.996 | ✓ 4.6 / 0.996 |
| elasticsearch | hnsw | shipped | 3.8 | ✓ 6.7 / 0.962 | slow 60.3 / 0.962 | ✗ OOM |
| elasticsearch | hnsw | tuned (c=500) | 6.2 | ✓ 9.0 / 0.997 | slow 235.7 / 0.997 | ✗ OOM |
| elasticsearch | int8_hnsw | shipped | 2.6 | ✓ 5.4 / 0.941 | ✓ 5.8 / 0.941 | ✗ OOM |
| elasticsearch | int8_hnsw | tuned (c=500) | 3.9 | ✓ 7.1 / 0.997 | slow 55.4 / 0.997 | ✗ OOM |
| elasticsearch | int4_hnsw | shipped | 2.6 | ✓ 5.2 / 0.901 | ✓ 5.4 / 0.901 | ✗ OOM |
| elasticsearch | int4_hnsw | tuned (c=500) | 3.4 | ✓ 6.4 / 0.996 | slow 25.8 / 0.996 | ✗ OOM |
| elasticsearch | bbq_hnsw | shipped | 2.1 | ✓ 4.4 / 0.927 | ✓ 5.2 / 0.927 | ✗ OOM |
| elasticsearch | bbq_hnsw | tuned (c=500) | 2.6 | ✓ 5.3 / 0.994 | slow 16.4 / 0.994 | ✗ OOM |
| chroma | default | shipped | 2.4 | ✓ 2.4 / 0.980 | ✓ 2.4 / 0.980 | ✓ 2.4 / 0.980 |
| chroma | default | tuned (c=500) | 5.6 | ✓ 5.7 / 0.996 | ✓ 5.7 / 0.996 | ✓ 5.8 / 0.996 |

## Act 3: the recall target from the labels (tuning questions, every deployment and setting)

| Target | Settings reaching it | Worst nDCG loss (points) | Within 0.5? |
| ---: | ---: | ---: | :--- |
| 0.8 | 155 | 5.37 | no |
| 0.85 | 152 | 5.37 | no |
| 0.9 | 148 | 5.37 | no |
| 0.95 | 127 | 3.04 | no |
| 0.97 | 111 | 1.71 | no |
| 0.99 | 56 | 0.64 | no |
| 0.995 | 26 | 0.57 | no |

No level keeps every setting within 0.5 points; target: the highest, **0.995**.

Act 3 checks the `tuned_hi` setting (tuned to 0.9975 on tuning questions).

## Act 3: built: per database and memory budget, the fastest deployment whose tuned setting passes the deploy check under that limit (recall ≥ 0.995, all answered, p50 within 2× or 5 ms of its 16 GiB p50; 200 test questions)

| Database | Budget GiB | Deployment (c) | Check recall | Check p50 ms | Recall (1,000 test) | nDCG | Answers lost | Others that pass |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| pgvector | 2 | none passes | | | | | | |
| pgvector | 1 | none passes | | | | | | |
| pgvector | 0.5 | none passes | | | | | | |
| qdrant | 2 | none passes | | | | | | |
| qdrant | 1 | none passes | | | | | | |
| qdrant | 0.5 | none passes | | | | | | |
| milvus | 2 | autoindex (500) | 0.999 | 4.5 | 0.999 | 0.920 | 1 | hnsw |
| milvus | 1 | autoindex (500) | 0.999 | 4.5 | 0.999 | 0.920 | 1 | hnsw |
| milvus | 0.5 | none passes | | | | | | |
| weaviate | 2 | none (500) | 0.999 | 6.9 | 0.999 | 0.919 | 2 | — |
| weaviate | 1 | none (500) | 0.999 | 6.9 | 0.999 | 0.919 | 2 | — |
| weaviate | 0.5 | none passes | | | | | | |
| elasticsearch | 2 | none passes | | | | | | |
| elasticsearch | 1 | none passes | | | | | | |
| elasticsearch | 0.5 | none passes | | | | | | |
| chroma | 2 | none passes | | | | | | |
| chroma | 1 | none passes | | | | | | |
| chroma | 0.5 | none passes | | | | | | |


**Exploratory, after the results: the same check at a 0.99 target**, any setting the ladder measured (as shipped or the tuned c), check recall ≥ 0.99, all answered, the same speed rule. p50 in ms at that limit; slower or failing settings are left out.

| Database | 8 GiB | 2 GiB | 1 GiB | 0.5 GiB |
| :--- | :--- | :--- | :--- | :--- |
| pgvector | — | bit c=500 13.5 (0.992), halfvec c=500 18.4 (0.994), vector c=500 26.6 (0.994) | bit c=500 15.2 (0.992), halfvec c=500 20.5 (0.994), vector c=500 28.6 (0.994) | halfvec c=500 20.1 (0.994) |
| qdrant | — | turbo2 c=None 1.5 (0.991), turbo1 c=200 2.0 (0.997), turbo2 c=200 2.1 (0.998), binary c=200 2.2 (0.997), turbo4 c=200 2.5 (0.995), scalar c=200 3.1 (1.000), none c=None 3.7 (0.994), none c=200 5.5 (0.996) | turbo2 c=None 1.4 (0.991), binary c=200 1.9 (0.997), turbo1 c=200 1.9 (0.997), turbo2 c=200 2.2 (0.998), turbo4 c=200 2.3 (0.995), scalar c=200 2.9 (1.000), none c=None 3.9 (0.994), none c=200 5.4 (0.996) | turbo2 c=None 1.9 (0.991), turbo4 c=200 3.7 (0.995), none c=None 4.0 (0.994), turbo1 c=200 5.0 (0.997), none c=200 5.6 (0.996), binary c=200 5.8 (0.997) |
| milvus | — | autoindex c=200 2.3 (0.998), hnsw c=100 4.1 (0.995), autoindex c=500 4.5 (0.999), hnsw c=200 5.5 (0.998), hnsw_sq8 c=500 6.5 (0.995) | autoindex c=200 2.7 (0.998), hnsw c=100 4.5 (0.995), autoindex c=500 4.5 (0.999), hnsw c=200 5.5 (0.998), hnsw_sq8 c=500 6.0 (0.995) | hnsw_sq8 c=500 6.4 (0.995) |
| weaviate | — | bq c=500 3.6 (0.996), none c=200 3.7 (0.993), none c=500 6.9 (0.999) | bq c=500 3.6 (0.996), none c=200 3.7 (0.993), none c=500 6.9 (0.999) | bq c=500 4.6 (0.996) |
| elasticsearch | — | bbq_hnsw c=500 5.3 (0.994), int4_hnsw c=500 6.4 (0.996), int8_hnsw c=500 7.1 (0.997), hnsw c=500 9.0 (0.997) | — | — |
| chroma | — | default c=500 5.7 (0.996) | default c=500 5.7 (0.996) | default c=500 5.8 (0.996) |

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

