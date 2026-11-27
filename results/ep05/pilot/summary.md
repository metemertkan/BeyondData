# Episode 5 summary (pilot: 60 NQ questions, 24 record lookups)

Items per task: closed 60, rag 60, abstain 30, records 24.

## The weights, read back

| Level | Model | Source | Ollama says | Same bytes as llama-quantize here |
| :--- | :--- | :--- | :--- | :--- |
| F16 | `qwen3:8b-fp16` | Ollama library | F16 |  |
| Q8_0 | `qwen3:8b-q8_0` | Ollama library | Q8_0 | False |
| Q4_K_M | `qwen3:8b` | Ollama library | Q4_K_M | False |
| Q6_K | `bd5/qwen3-8b:q6_k` | llama-quantize from Ollama's fp16 | Q6_K |  |
| Q5_K_M | `bd5/qwen3-8b:q5_k_m` | llama-quantize from Ollama's fp16 | Q5_K_M |  |
| Q3_K_M | `bd5/qwen3-8b:q3_k_m` | llama-quantize from Ollama's fp16 | Q3_K_M |  |
| Q2_K | `bd5/qwen3-8b:q2_k` | llama-quantize from Ollama's fp16 | Q2_K |  |

## Every design against the reference (right / lost / gained / changed replies)

| Design | closed | rag | abstain | records | data tasks: lost |
| :--- | ---: | ---: | ---: | ---: | ---: |
| fp16 (reference) | 15/60 · −0 +0 · 0 | 35/60 · −0 +0 · 0 | 11/30 · −0 +0 · 0 | 20/24 · −0 +0 · 0 | 0 |
| Q4_K_M (Ollama's file) | 16/60 · −0 +1 · 17 | 31/60 · −4 +0 · 12 | 14/30 · −0 +3 · 11 | 21/24 · −0 +1 · 4 | 4 |
| Q4_K_M (made here) | 15/60 · −1 +1 · 17 | 32/60 · −3 +0 · 10 | 14/30 · −0 +3 · 9 | 20/24 · −1 +1 · 5 | 4 |
| Q2_K | 8/60 · −9 +2 · 52 | 29/60 · −10 +4 · 29 | 19/30 · −1 +9 · 15 | 10/24 · −11 +1 · 23 | 22 |
| as shipped (Q4_K_M, default context, sampled) | 15/60 · −2 +2 · 36 | 32/60 · −3 +0 · 10 | 14/30 · −0 +3 · 11 | 13/24 · −7 +0 · 13 | 10 |
| as shipped, context set |  |  |  | 21/24 · −0 +1 · 3 | 0 |
| Q4_K_M, run again | 16/60 · −0 +1 · 17 | 31/60 · −4 +0 · 12 | 14/30 · −0 +3 · 11 | 20/24 · −1 +1 · 6 | 5 |
| Q4_K_M, KV container f16 |  | 32/60 · −3 +0 · 8 | 14/30 · −0 +3 · 11 | 21/24 · −0 +1 · 4 | 3 |
| Q4_K_M, KV container f16, closed first | 16/60 · −0 +1 · 17 | 31/60 · −4 +0 · 12 | 14/30 · −0 +3 · 11 | 20/24 · −1 +1 · 6 | 5 |
| Q4_K_M, KV q4_0 |  | 32/60 · −4 +1 · 16 | 13/30 · −1 +3 · 13 | 23/24 · −0 +3 · 3 | 5 |

Cells: right of n · answers lost and gained against fp16 · replies that differ from fp16's.

## Repeat checks (same settings, same history: replies that differ)

- as shipped (Q4_K_M, default context, sampled) vs as shipped, context set (rag, abstain): 0 of 0 differ
- Q4_K_M (Ollama's file) vs Q4_K_M, run again (closed, rag, abstain, records): 2 of 174 differ
- Q4_K_M (Ollama's file) vs Q4_K_M, KV container f16, closed first (closed, rag, abstain, records): 2 of 174 differ

## Declines and abstention

| Design | rag: declined (answer in passages / not) | abstain: declined correctly | abstain: answered with the right answer anyway |
| :--- | ---: | ---: | ---: |
| fp16 (reference) | 5 / 2 | 11/30 | 3 |
| Q4_K_M (Ollama's file) | 5 / 2 | 14/30 | 1 |
| Q4_K_M (made here) | 5 / 2 | 14/30 | 1 |
| Q2_K | 15 / 4 | 19/30 | 2 |
| as shipped (Q4_K_M, default context, sampled) | 6 / 3 | 14/30 | 3 |
| Q4_K_M, run again | 5 / 2 | 14/30 | 1 |
| Q4_K_M, KV container f16 | 5 / 2 | 14/30 | 1 |
| Q4_K_M, KV container f16, closed first | 5 / 2 | 14/30 | 1 |
| Q4_K_M, KV q4_0 | 5 / 3 | 13/30 | 1 |

## Records: right by context, kind and position

| Design | S | L | amount | date | email | number | L first third | L middle | L last third | L prompt tokens (median) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fp16 (reference) | 12/12 | 8/12 | 6/6 | 5/6 | 4/6 | 5/6 | 2/4 | 3/4 | 3/4 | 13329 |
| Q4_K_M (Ollama's file) | 12/12 | 9/12 | 6/6 | 5/6 | 5/6 | 5/6 | 2/4 | 4/4 | 3/4 | 13329 |
| Q4_K_M (made here) | 11/12 | 9/12 | 6/6 | 4/6 | 5/6 | 5/6 | 2/4 | 4/4 | 3/4 | 13329 |
| Q2_K | 6/12 | 4/12 | 6/6 | 2/6 | 2/6 | 0/6 | 2/4 | 1/4 | 1/4 | 13329 |
| as shipped (Q4_K_M, default context, sampled) | 11/12 | 2/12 | 4/6 | 2/6 | 4/6 | 3/6 | 0/4 | 0/4 | 2/4 | 2050 |
| as shipped, context set | 12/12 | 9/12 | 6/6 | 5/6 | 5/6 | 5/6 | 2/4 | 4/4 | 3/4 | 13329 |
| Q4_K_M, run again | 12/12 | 8/12 | 6/6 | 5/6 | 5/6 | 4/6 | 2/4 | 3/4 | 3/4 | 13329 |
| Q4_K_M, KV container f16 | 12/12 | 9/12 | 6/6 | 5/6 | 5/6 | 5/6 | 2/4 | 4/4 | 3/4 | 13329 |
| Q4_K_M, KV container f16, closed first | 12/12 | 8/12 | 6/6 | 5/6 | 5/6 | 4/6 | 2/4 | 3/4 | 3/4 | 13329 |
| Q4_K_M, KV q4_0 | 12/12 | 11/12 | 6/6 | 6/6 | 6/6 | 5/6 | 3/4 | 4/4 | 4/4 | 13329 |

## Speed and memory

| Design | prompt tokens/s | reply tokens/s (short prompts) | loaded size, NQ context (GiB) | loaded size, records context (GiB) | KV cache (log) |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fp16 (reference) | 30.4 | 1.56 | 15.93 | 17.76 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M (Ollama's file) | 40.7 | 4.63 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M (made here) | 41.1 | 4.79 | 5.35 | 7.18 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q2_K | 40.2 | 7.22 | 3.73 | 5.55 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| as shipped (Q4_K_M, default context, sampled) | 61.0 | 4.61 | 5.54 | 5.54 | size =  576.00 MiB (  4096 cells,  36 layers,  1/1 seqs), K (f16):  288.00 MiB,  |
| as shipped, context set | 40.8 | 0.0 |  | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M, run again | 40.8 | 4.63 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M, KV container f16 | 41.1 | 4.64 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M, KV container f16, closed first | 41.0 | 4.63 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M, KV q4_0 | 19.6 | 4.59 | 5.13 | 5.74 | size =  648.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (q4_0):  324.00 MiB, |
