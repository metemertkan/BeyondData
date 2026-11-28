# Episode 6 summary (pilot)

## The month, per design (questions: retrieval; answers: qwen3:8b)

| Design | index at the end: entries / outdated / deleted / duplicate / missing | questions with an outdated or deleted chunk | answers current / stale / both / declined / other | stale from the index | chunks embedded in the month |
| :--- | :--- | ---: | :--- | ---: | ---: |
| once (as shipped) | 1,649 / 708 / 20 / 0 / 744 | 81 of 100 | 23 / 66 / 0 / 0 / 11 | 66 | 0 |
| rerun nightly (as shipped) | 11,618 / 2835 / 60 / 7058 / 0 | 60 of 100 | 28 / 49 / 4 / 9 / 10 | 53 | 9,969 |
| rebuild nightly | 1,665 / 0 / 0 / 0 / 0 | 52 of 100 | 45 / 45 / 0 / 0 / 10 | 45 | 9,969 |
| upsert nightly | 1,699 / 8 / 20 / 6 / 0 | 54 of 100 | 45 / 45 / 0 / 0 / 10 | 45 | 9,969 |
| record manager | 1,665 / 0 / 0 / 0 / 0 | 13 of 100 | 84 / 10 / 0 / 0 / 6 | 10 | 2,179 |
| poll updated_at | 1,685 / 584 / 20 / 0 / 584 | 37 of 100 | 75 / 17 / 0 / 0 / 8 | 17 | 305 |
| CDC | 1,665 / 0 / 0 / 0 / 0 | 0 of 100 | 94 / 0 / 0 / 0 / 6 | 0 | 1,368 |
| same database | 1,665 / 584 / 0 / 0 / 584 | 24 of 100 | 85 / 7 / 0 / 0 / 8 | 7 | 305 |
| built | 1,665 / 0 / 0 / 0 / 0 | 0 of 100 | 94 / 0 / 0 / 0 / 6 | 0 | 850 |
| rebuild + check (expl.) | 1,665 / 0 / 0 / 0 / 0 | 0 of 100 | 50 / 4 / 0 / 11 / 35 | 0 | 9,969 |
| CDC, worker down 12 h (expl.) | 1,665 / 0 / 0 / 0 / 0 | 3 of 100 | 91 / 2 / 0 / 0 / 7 | 2 | 1,368 |
| built, worker down 12 h (expl.) | 1,665 / 0 / 0 / 0 / 0 | 0 of 100 | 91 / 0 / 0 / 0 / 9 | 0 | 850 |

## How long a change took to reach the index (replay clock; changes in the month's last 24 h left out)

| Design | changes | current: p50 / p95 / max (normal) | migration: max / never | never current | never clean |
| :--- | ---: | :--- | :--- | ---: | ---: |
| once (as shipped) | 650 | — / — / — | — / 488 | 650 | 650 |
| rerun nightly (as shipped) | 658 | 11.4 h / 16.4 h / 17.7 h | 5.0 h / 0 | 0 | 632 |
| rebuild nightly | 746 | 11.7 h / 16.6 h / 17.8 h | 5.0 h / 0 | 0 | 0 |
| upsert nightly | 741 | 11.7 h / 16.6 h / 17.8 h | 5.0 h / 0 | 0 | 18 |
| record manager | 769 | 2 min / 5 min / 5 min | 36 s / 0 | 0 | 0 |
| poll updated_at | 735 | 2 min / 5 min / 5 min | 20.0 h / 521 | 529 | 529 |
| CDC | 769 | 0 s / 0 s / 0 s | 37 s / 0 | 0 | 0 |
| same database | 735 | 0 s / 0 s / 0 s | 20.0 h / 519 | 519 | 519 |
| built | 769 | 0 s / 0 s / 0 s | 21 s / 0 | 0 | 0 |
| rebuild + check (expl.) | 746 | 11.7 h / 16.6 h / 17.8 h | 5.0 h / 0 | 0 | 0 |
| CDC, worker down 12 h (expl.) | 769 | 0 s / 7.4 h / 10.8 h | 37 s / 0 | 0 | 0 |
| built, worker down 12 h (expl.) | 769 | 0 s / 7.4 h / 10.8 h | 21 s / 0 | 0 | 0 |

## Changed facts: current answers by time since the change

| Design | 2 min | 15 min | 1 h | 4 h | 12 h | 1 day | 3 days | 7 days |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| once (as shipped) | 0/9 | 0/9 | 0/9 | 0/9 | 0/8 | 0/8 | 0/8 | — |
| rerun nightly (as shipped) | 0/9 | 0/9 | 0/9 | 0/9 | 2/8 | 1/8 | 3/8 | — |
| rebuild nightly | 0/9 | 0/9 | 0/9 | 0/9 | 5/8 | 8/8 | 8/8 | — |
| upsert nightly | 0/9 | 0/9 | 0/9 | 0/9 | 5/8 | 8/8 | 8/8 | — |
| record manager | 4/9 | 8/9 | 9/9 | 8/9 | 8/8 | 8/8 | 8/8 | — |
| poll updated_at | 3/9 | 7/9 | 8/9 | 7/9 | 6/8 | 6/8 | 6/8 | — |
| CDC | 8/9 | 8/9 | 9/9 | 8/9 | 8/8 | 8/8 | 8/8 | — |
| same database | 7/9 | 7/9 | 8/9 | 7/9 | 6/8 | 6/8 | 6/8 | — |
| built | 8/9 | 8/9 | 9/9 | 8/9 | 8/8 | 8/8 | 8/8 | — |
| rebuild + check (expl.) | 0/9 | 0/9 | 0/9 | 0/9 | 5/8 | 7/8 | 8/8 | — |
| CDC, worker down 12 h (expl.) | 7/9 | 8/9 | 9/9 | 7/9 | 8/8 | 8/8 | 8/8 | — |
| built, worker down 12 h (expl.) | 7/9 | 8/9 | 9/9 | 7/9 | 8/8 | 8/8 | 8/8 | — |

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

## The six databases

| Database | add again: error / count after / found by new / by old (of 200) | update: new at once, old gone at once (of 200) | delete gone at once (of 200), max | recall fresh → rounds → after clean-up | p50 ms fresh → round 3 → after |
| :--- | :--- | :--- | :--- | :--- | :--- |
| chroma | ok / 100,000 / 0 / 200 | 200, 200 | 200, 0 s | 0.9809 → 0.9811 → 0.9796 → 0.9819 → 0.9819 | 4.09 → 12.9 → 4.99 |
| elasticsearch | ok / 100,000 / 200 / 0 | 0, 0 | 0, 1 s | 0.9419 → 0.9486 → 0.9513 → 0.9509 → 0.9486 | 12.25 → 11.6 → 2.98 |
| milvus | ok / 101,000 / 200 / 200 | 0, 0 | 0, 0 s | 0.8568 → 0.8765 → 0.8811 → 0.8889 → 0.8344 | 1.28 → 5.73 → 5.33 |
| pgvector | error / 100,000 / 0 / 200 | 200, 200 | 200, 0 s | 0.9582 → 0.9614 → 0.957 → 0.9518 → 0.9649 | 3.51 → 4.13 → 3.46 |
| qdrant | ok / 100,000 / 200 / 0 | 200, 200 | 200, 0 s | 0.9945 → 0.9946 → 0.993 → 0.9936 → 0.994 | 13.43 → 6.89 → 12.45 |
| weaviate | ok / 100,000 / 200 / 0 | 200, 200 | 200, 0 s | 0.9909 → 0.9914 → 0.9913 → 0.9918 → 0.993 | 2.54 → 3.24 → 9.71 |
