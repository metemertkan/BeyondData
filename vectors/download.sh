#!/usr/bin/env bash
# Episode 2 raw data: BEIR Natural Questions with Cohere embed-english-v3 vectors (~4.5 GB, no account needed).
#   bash vectors/download.sh && uv run python -m vectors.data --prepare
set -euo pipefail
cd "$(dirname "$0")/.."
BASE=https://huggingface.co/datasets/CohereLabs/beir-embed-english-v3/resolve/main/nq
for f in corpus/0000 corpus/0001 corpus/0002 qrels/test queries/test; do
  mkdir -p "data/ep02/raw/nq/$(dirname "$f")"
  curl -sSL --retry 5 -C - -o "data/ep02/raw/nq/$f.parquet" "$BASE/$f.parquet"
done
