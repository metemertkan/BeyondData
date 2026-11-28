# Episode 6 summary (full)

## The month, per design (questions: retrieval; answers: qwen3:8b)

| Design | index at the end: entries / outdated / deleted / duplicate / missing | questions with an outdated or deleted chunk | answers current / stale / both / declined / other | stale from the index | chunks embedded in the month |
| :--- | :--- | ---: | :--- | ---: | ---: |
| once (as shipped) | 1,649 / 825 / 58 / 0 / 954 | 428 of 500 | 95 / 297 / 0 / 1 / 107 | 297 | 0 |
| rerun nightly (as shipped) | 50,420 / 15248 / 816 / 32636 / 0 | 261 of 500 | 170 / 208 / 4 / 10 / 108 | 181 | 48,771 |
| rebuild nightly | 1,720 / 0 / 0 / 0 / 0 | 178 of 500 | 238 / 173 / 0 / 5 / 84 | 168 | 48,771 |
| upsert nightly | 1,830 / 36 / 58 / 16 / 0 | 223 of 500 | 216 / 197 / 0 / 5 / 82 | 192 | 48,771 |
| record manager | 1,720 / 0 / 0 / 0 / 0 | 48 of 500 | 373 / 51 / 0 / 5 / 71 | 47 | 5,469 |
| poll updated_at | 1,778 / 464 / 58 / 0 / 464 | 148 of 500 | 359 / 75 / 0 / 1 / 65 | 71 | 1,209 |
| CDC | 1,720 / 0 / 0 / 0 / 0 | 0 of 500 | 418 / 4 / 0 / 5 / 73 | 0 | 2,280 |
| same database | 1,720 / 464 / 0 / 0 / 464 | 87 of 500 | 422 / 11 / 0 / 1 / 66 | 7 | 1,209 |
| built | 1,720 / 0 / 0 / 0 / 0 | 0 of 500 | 418 / 4 / 0 / 5 / 73 | 0 | 1,455 |
| rebuild + check (expl.) | 1,720 / 0 / 0 / 0 / 0 | 0 of 500 | 280 / 21 / 0 / 22 / 177 | 0 | 48,771 |
| CDC, worker down 12 h (expl.) | 1,720 / 0 / 0 / 0 / 0 | 7 of 500 | 411 / 11 / 0 / 5 / 73 | 7 | 2,280 |
| built, worker down 12 h (expl.) | 1,720 / 0 / 0 / 0 / 0 | 0 of 500 | 411 / 4 / 0 / 9 / 76 | 0 | 1,455 |

## How long a change took to reach the index (replay clock; changes in the month's last 24 h left out)

| Design | changes | current: p50 / p95 / max (normal) | migration: max / never | never current | never clean |
| :--- | ---: | :--- | :--- | ---: | ---: |
| once (as shipped) | 778 | — / — / — | — / 341 | 778 | 778 |
| rerun nightly (as shipped) | 797 | 12.8 h / 17.4 h / 18.0 h | 5.0 h / 0 | 0 | 701 |
| rebuild nightly | 1266 | 12.9 h / 17.5 h / 18.0 h | 5.0 h / 0 | 0 | 0 |
| upsert nightly | 1232 | 12.8 h / 17.5 h / 18.0 h | 5.0 h / 0 | 0 | 64 |
| record manager | 1311 | 3 min / 5 min / 5 min | 37 s / 0 | 0 | 0 |
| poll updated_at | 1165 | 3 min / 5 min / 5 min | 10.8 d / 420 | 444 | 444 |
| CDC | 1313 | 0 s / 0 s / 0 s | 37 s / 0 | 0 | 0 |
| same database | 1165 | 0 s / 0 s / 0 s | 10.8 d / 412 | 412 | 412 |
| built | 1313 | 0 s / 0 s / 0 s | 22 s / 0 | 0 | 0 |
| rebuild + check (expl.) | 1266 | 12.9 h / 17.5 h / 18.0 h | 5.0 h / 0 | 0 | 0 |
| CDC, worker down 12 h (expl.) | 1313 | 0 s / 0 s / 11.2 h | 37 s / 0 | 0 | 0 |
| built, worker down 12 h (expl.) | 1313 | 0 s / 0 s / 11.2 h | 22 s / 0 | 0 | 0 |

## Changed facts: current answers by time since the change

| Design | 2 min | 15 min | 1 h | 4 h | 12 h | 1 day | 3 days | 7 days |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| once (as shipped) | 0/38 | 0/38 | 0/38 | 0/38 | 0/38 | 0/37 | 0/37 | 0/36 |
| rerun nightly (as shipped) | 2/38 | 2/38 | 3/38 | 2/38 | 5/38 | 10/37 | 21/37 | 23/36 |
| rebuild nightly | 0/38 | 1/38 | 1/38 | 1/38 | 13/38 | 32/37 | 32/37 | 31/36 |
| upsert nightly | 0/38 | 1/38 | 1/38 | 1/38 | 12/38 | 31/37 | 31/37 | 29/36 |
| record manager | 11/38 | 26/38 | 33/38 | 33/38 | 32/38 | 32/37 | 32/37 | 29/36 |
| poll updated_at | 12/38 | 27/38 | 33/38 | 33/38 | 32/38 | 33/37 | 33/37 | 30/36 |
| CDC | 29/38 | 26/38 | 33/38 | 33/38 | 32/38 | 32/37 | 32/37 | 29/36 |
| same database | 30/38 | 27/38 | 33/38 | 33/38 | 32/38 | 33/37 | 33/37 | 30/36 |
| built | 29/38 | 26/38 | 33/38 | 33/38 | 32/38 | 32/37 | 32/37 | 29/36 |
| rebuild + check (expl.) | 4/38 | 4/38 | 4/38 | 4/38 | 15/38 | 33/37 | 32/37 | 30/36 |
| CDC, worker down 12 h (expl.) | 27/38 | 25/38 | 31/38 | 31/38 | 32/38 | 32/37 | 32/37 | 29/36 |
| built, worker down 12 h (expl.) | 27/38 | 25/38 | 31/38 | 31/38 | 32/38 | 32/37 | 32/37 | 29/36 |

## The target (Act 3)

| Design | no stale context | fresh (normal) | fresh (migration) | agrees at audits | passes |
| :--- | :---: | :---: | :---: | :---: | :---: |
| once (as shipped) | no | no | no | no | **no** |
| rerun nightly (as shipped) | no | no | no | no | **no** |
| rebuild nightly | no | no | no | no | **no** |
| upsert nightly | no | no | no | no | **no** |
| record manager | no | yes | yes | no | **no** |
| poll updated_at | no | no | no | no | **no** |
| CDC | yes | yes | yes | yes | **yes** |
| same database | no | yes | no | no | **no** |
| built | yes | yes | yes | yes | **yes** |
| rebuild + check (expl.) | yes | no | no | no | **no** |
| CDC, worker down 12 h (expl.) | no | no | yes | no | **no** |
| built, worker down 12 h (expl.) | yes | no | yes | no | **no** |

## Real time (writer: an edit every 10 s, a 300-article burst at minute 7)

| Design | saves | synced | never | steady p50 / max | burst p50 / max | save p50 | burst saves total |
| :--- | ---: | ---: | ---: | :--- | :--- | :--- | :--- |
| poll updated_at | 420 | 412 | 1 | 3 min / 10 min | 3 min / 5 min | 0.012 s | 1.0 s |
| CDC | 420 | 420 | 0 | 1 s / 2 s | 7 s / 14 s | 0.012 s | 1.1 s |
| same database | 420 | 420 | 0 | 0 s / 0 s | 0 s / 0 s | 0.034 s | 12.7 s |
| built | 420 | 420 | 0 | 1 s / 2 s | 7 s / 15 s | 0.012 s | 1.0 s |

## The six databases

| Database | add again: error / count after / found by new / by old (of 200) | update: new at once, old gone at once (of 200) | delete gone at once (of 200), max | recall fresh → rounds → after clean-up | p50 ms fresh → round 3 → after |
| :--- | :--- | :--- | :--- | :--- | :--- |
| chroma | ok / 1,000,000 / 0 / 200 | 200, 200 | 200, 0 s | 0.9594 → 0.9542 → 0.9569 → 0.957 → 0.957 | 2.91 → 2.92 → 3.11 |
| elasticsearch | ok / 1,000,000 / 200 / 0 | 0, 0 | 0, 1 s | 0.9037 → 0.9068 → 0.9085 → 0.9089 → 0.9089 | 5.07 → 3.15 → 3.12 |
| milvus | ok / 1,001,000 / 200 / 200 | 0, 0 | 0, 0 s | 0.9118 → 0.9058 → 0.8983 → 0.8962 → 0.8813 | 2.02 → 14.53 → 6.01 |
| pgvector | error / 1,000,000 / 0 / 200 | 200, 200 | 200, 0 s | 0.9223 → 0.9222 → 0.9162 → 0.9098 → 0.9294 | 5.91 → 5.47 → 4.71 |
| qdrant | ok / 1,000,000 / 200 / 0 | 200, 200 | 200, 0 s | 0.9723 → 0.9716 → 0.9695 → 0.9683 → 0.9705 | 4.92 → 87.87 → 4.94 |
| weaviate | ok / 1,000,000 / 200 / 0 | 200, 200 | 200, 0 s | 0.9793 → 0.9819 → 0.9826 → 0.9837 → 0.9826 | 2.87 → 8.9 → 3.66 |

## Exploratory: the new value and the old one both in the context

Distinct prompts (changed facts with distinct values; new value in a current chunk, old value in an outdated or deleted one): 24. Replies: old 17, new 4, both 3, other 0. New value ranked above the old one: 24. New value only in a release note: 13 (12 of them stale).
