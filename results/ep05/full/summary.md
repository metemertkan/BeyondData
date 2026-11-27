# Episode 5 summary (full: 250 NQ questions, 100 record lookups)

Items per task: closed 250, rag 250, abstain 100, records 100.

## The weights, read back

| Level | Model | Source | Ollama says | Same bytes as llama-quantize here |
| :--- | :--- | :--- | :--- | :--- |
| F16 | `qwen3:8b-fp16` | Ollama library | F16 |  |
| Q8_0 | `qwen3:8b-q8_0` | Ollama library | Q8_0 | False |
| Q4_K_M | `qwen3:8b` | Ollama library | Q4_K_M | False |
| Q6_K | `bd5/qwen3-8b:q6_k` | llama-quantize from Ollama's fp16 | Q6_K |  |
| Q5_K_M | `bd5/qwen3-8b:q5_k_m` | llama-quantize from Ollama's fp16 | Q5_K_M |  |
| Q4_K_M (made here) | `bd5/qwen3-8b:q4_k_m` | llama-quantize from Ollama's fp16 | Q4_K_M |  |
| Q3_K_M | `bd5/qwen3-8b:q3_k_m` | llama-quantize from Ollama's fp16 | Q3_K_M |  |
| Q2_K | `bd5/qwen3-8b:q2_k` | llama-quantize from Ollama's fp16 | Q2_K |  |

## Every design against the reference (right / lost / gained / changed replies)

| Design | closed | rag | abstain | records | data tasks: lost |
| :--- | ---: | ---: | ---: | ---: | ---: |
| fp16 (reference) | 65/250 · −0 +0 · 0 | 145/250 · −0 +0 · 0 | 42/100 · −0 +0 · 0 | 78/100 · −0 +0 · 0 | 0 |
| fp16, prompt reworded (noise floor) | 62/250 · −4 +1 · 85 | 152/250 · −3 +10 · 51 | 45/100 · −0 +3 · 15 | 81/100 · −2 +5 · 15 | 5 |
| Q8_0 | 66/250 · −0 +1 · 20 | 143/250 · −3 +1 · 16 | 42/100 · −0 +0 · 1 | 78/100 · −0 +0 · 1 | 3 |
| Q6_K | 65/250 · −2 +2 · 68 | 144/250 · −5 +4 · 25 | 43/100 · −0 +1 · 8 | 77/100 · −1 +0 · 8 | 6 |
| Q5_K_M | 65/250 · −4 +4 · 83 | 150/250 · −3 +8 · 35 | 43/100 · −1 +2 · 11 | 81/100 · −1 +4 · 9 | 5 |
| Q4_K_M (Ollama's file) | 63/250 · −8 +6 · 113 | 138/250 · −9 +2 · 46 | 48/100 · −1 +7 · 23 | 83/100 · −3 +8 · 19 | 13 |
| Q4_K_M (made here) | 63/250 · −8 +6 · 118 | 138/250 · −9 +2 · 52 | 49/100 · −0 +7 · 24 | 84/100 · −1 +7 · 18 | 10 |
| Q3_K_M | 52/250 · −22 +9 · 173 | 130/250 · −24 +9 · 73 | 61/100 · −0 +19 · 36 | 73/100 · −12 +7 · 35 | 36 |
| Q2_K | 27/250 · −43 +5 · 227 | 102/250 · −53 +10 · 125 | 56/100 · −11 +25 · 56 | 48/100 · −36 +6 · 79 | 100 |
| as shipped (Q4_K_M, default context, sampled) | 54/250 · −18 +7 · 177 | 138/250 · −14 +7 · 64 | 47/100 · −2 +7 · 30 | 46/100 · −35 +3 · 67 | 51 |
| as shipped, context set |  | 138/250 · −14 +7 · 64 | 47/100 · −2 +7 · 30 | 82/100 · −3 +7 · 18 | 19 |
| Q4_K_M, KV q8_0 |  | 138/250 · −9 +2 · 44 | 49/100 · −1 +8 · 25 | 88/100 · −2 +12 · 21 | 12 |
| Q4_K_M, KV q4_0 |  | 143/250 · −12 +10 · 52 | 48/100 · −0 +6 · 22 | 85/100 · −5 +12 · 27 | 17 |
| Q6_K, KV q8_0 |  | 146/250 · −4 +5 · 28 | 42/100 · −1 +1 · 13 | 86/100 · −1 +9 · 17 | 6 |
| qwen3:4b Q8_0 | 45/250 · −32 +12 · 207 | 147/250 · −15 +17 · 104 | 42/100 · −6 +6 · 44 | 74/100 · −12 +8 · 35 | 33 |

Cells: right of n · answers lost and gained against fp16 · replies that differ from fp16's.

## Repeat checks (same settings, same history: replies that differ)

- as shipped (Q4_K_M, default context, sampled) vs as shipped, context set (rag, abstain): 0 of 350 differ

## Declines and abstention

| Design | rag: declined (answer in passages / not) | abstain: declined correctly | abstain: answered with the right answer anyway |
| :--- | ---: | ---: | ---: |
| fp16 (reference) | 17 / 11 | 42/100 | 8 |
| fp16, prompt reworded (noise floor) | 16 / 12 | 45/100 | 8 |
| Q8_0 | 17 / 12 | 42/100 | 7 |
| Q6_K | 17 / 11 | 43/100 | 9 |
| Q5_K_M | 15 / 10 | 43/100 | 7 |
| Q4_K_M (Ollama's file) | 19 / 11 | 48/100 | 7 |
| Q4_K_M (made here) | 21 / 10 | 49/100 | 8 |
| Q3_K_M | 34 / 15 | 61/100 | 3 |
| Q2_K | 51 / 15 | 56/100 | 2 |
| as shipped (Q4_K_M, default context, sampled) | 22 / 10 | 47/100 | 9 |
| as shipped, context set | 22 / 10 | 47/100 | 9 |
| Q4_K_M, KV q8_0 | 18 / 11 | 49/100 | 6 |
| Q4_K_M, KV q4_0 | 20 / 12 | 48/100 | 9 |
| Q6_K, KV q8_0 | 15 / 10 | 42/100 | 6 |
| qwen3:4b Q8_0 | 17 / 11 | 42/100 | 7 |

## Records: right by context, kind and position

| Design | S | L | amount | date | email | number | L first third | L middle | L last third | L prompt tokens (median) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fp16 (reference) | 36/40 | 42/60 | 22/25 | 19/25 | 18/25 | 19/25 | 16/20 | 8/20 | 18/20 | 13329 |
| fp16, prompt reworded (noise floor) | 37/40 | 44/60 | 22/25 | 19/25 | 19/25 | 21/25 | 18/20 | 9/20 | 17/20 | 13330 |
| Q8_0 | 36/40 | 42/60 | 22/25 | 19/25 | 18/25 | 19/25 | 16/20 | 8/20 | 18/20 | 13329 |
| Q6_K | 35/40 | 42/60 | 22/25 | 19/25 | 18/25 | 18/25 | 16/20 | 8/20 | 18/20 | 13329 |
| Q5_K_M | 37/40 | 44/60 | 21/25 | 20/25 | 20/25 | 20/25 | 16/20 | 8/20 | 20/20 | 13329 |
| Q4_K_M (Ollama's file) | 38/40 | 45/60 | 23/25 | 18/25 | 21/25 | 21/25 | 18/20 | 10/20 | 17/20 | 13329 |
| Q4_K_M (made here) | 38/40 | 46/60 | 23/25 | 21/25 | 19/25 | 21/25 | 17/20 | 11/20 | 18/20 | 13329 |
| Q3_K_M | 36/40 | 37/60 | 21/25 | 20/25 | 15/25 | 17/25 | 13/20 | 8/20 | 16/20 | 13329 |
| Q2_K | 29/40 | 19/60 | 15/25 | 15/25 | 12/25 | 6/25 | 10/20 | 1/20 | 8/20 | 13329 |
| as shipped (Q4_K_M, default context, sampled) | 37/40 | 9/60 | 13/25 | 11/25 | 10/25 | 12/25 | 0/20 | 0/20 | 9/20 | 2050 |
| as shipped, context set | 37/40 | 45/60 | 23/25 | 18/25 | 20/25 | 21/25 | 18/20 | 10/20 | 17/20 | 13329 |
| Q4_K_M, KV q8_0 | 38/40 | 50/60 | 23/25 | 21/25 | 21/25 | 23/25 | 18/20 | 15/20 | 17/20 | 13329 |
| Q4_K_M, KV q4_0 | 36/40 | 49/60 | 23/25 | 24/25 | 19/25 | 19/25 | 17/20 | 15/20 | 17/20 | 13329 |
| Q6_K, KV q8_0 | 36/40 | 50/60 | 23/25 | 22/25 | 19/25 | 22/25 | 16/20 | 15/20 | 19/20 | 13329 |
| qwen3:4b Q8_0 | 37/40 | 37/60 | 22/25 | 20/25 | 16/25 | 16/25 | 15/20 | 10/20 | 12/20 | 13329 |

## Speed and memory

| Design | prompt tokens/s | reply tokens/s (short prompts) | loaded size, NQ context (GiB) | loaded size, records context (GiB) | KV cache (log) |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fp16 (reference) | 30.4 | 1.53 | 15.93 | 17.76 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| fp16, prompt reworded (noise floor) | 30.0 | 1.5 | 15.93 | 17.76 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q8_0 | 33.7 | 2.77 | 8.91 | 10.74 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q6_K | 41.5 | 3.59 | 6.93 | 8.76 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q5_K_M | 41.1 | 4.1 | 6.12 | 7.94 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M (Ollama's file) | 41.0 | 4.43 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M (made here) | 39.9 | 4.48 | 5.35 | 7.18 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q3_K_M | 40.8 | 5.52 | 4.51 | 6.34 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q2_K | 34.3 | 6.4 | 3.73 | 5.55 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| as shipped (Q4_K_M, default context, sampled) | 62.0 | 4.5 | 5.54 | 5.54 | size =  576.00 MiB (  4096 cells,  36 layers,  1/1 seqs), K (f16):  288.00 MiB,  |
| as shipped, context set | 39.5 | 4.32 | 5.54 | 7.36 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |
| Q4_K_M, KV q8_0 | 18.9 | 4.22 | 5.27 | 6.31 | size = 1224.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (q8_0):  612.00 MiB, |
| Q4_K_M, KV q4_0 | 19.0 | 4.3 | 5.13 | 5.74 | size =  648.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (q4_0):  324.00 MiB, |
| Q6_K, KV q8_0 | 18.8 | 3.41 | 6.67 | 7.70 | size = 1224.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (q8_0):  612.00 MiB, |
| qwen3:4b Q8_0 | 47.3 | 4.8 | 4.71 | 6.51 | size = 2304.00 MiB ( 16384 cells,  36 layers,  1/1 seqs), K (f16): 1152.00 MiB,  |

## Act 3: built (context 16,384; the noise floor loses 5 answers on the data tasks)

| Budget | Pick (most weight bits that fit; KV f16, else q8_0, else q4_0) | Loaded size GiB | Lost on data tasks | Passes (≤ noise floor) |
| ---: | :--- | ---: | ---: | :--- |
| 6 | Q4_K_M, KV q4_0 | 5.74 | 17 | no |
| 8 | Q6_K, KV q8_0 | 7.7 | 6 | no |
| 12 | Q8_0 | 10.74 | 3 | yes |
