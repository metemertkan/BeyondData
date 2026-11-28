#!/bin/sh
# Episode 6, the full run: one step after another, so nothing else competes for the CPU.
#   sh scripts/ep06_full.sh > results/ep06/full.log 2>&1
set -e
cd "$(dirname "$0")/.."
uv run python -m scripts.ep06_run --size full                       # the month, replayed into every design
uv run python -m scripts.ep06_run --size full --answers             # qwen3:8b on every distinct prompt
for d in poll cdc same_db built; do                                  # the continuous designs in real time
  uv run python -m sync.realtime --design "$d" --minutes 20 --size full
done
uv run python -m scripts.ep06_stores --size full                    # the six databases at one million
uv run python -m scripts.ep06_summary --size full
echo "full run done $(date)"
