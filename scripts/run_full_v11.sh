#!/bin/bash
# Full ontology run: A judge gemma_v11t (thinking) on every segment, then the A2/C judge
# gemma_v11c on every trace from the Values paragraphs. Shards over the GPUs given (at most four
# flex GPUs for judging). The first run (2026-10-30) read the v12 prompt and is stored as
# gemma_v12t/gemma_v12c; this rerun uses the restored v11 prompt.
# Usage: bash scripts/run_full_v11.sh GPU...     (run inside tmux; logs in logs/)
# With WAIT_FOR=<tmux session>, first waits for that session to end, then checks that each GPU
# has no process on it before starting.
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
G=("$@"); N=${#G[@]}
if [ -n "${WAIT_FOR:-}" ]; then
  while tmux has-session -t "$WAIT_FOR" 2>/dev/null; do sleep 60; done
  echo "$WAIT_FOR ended $(date)"; sleep 60
fi
for g in "${G[@]}"; do
  if [ -n "$(nvidia-smi -i $g --query-compute-apps=pid --format=csv,noheader)" ]; then
    echo "GPU $g is busy; not starting"; nvidia-smi; exit 1
  fi
done
for i in $(seq 0 $((N - 1))); do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py a --items all --tag gemma_v11t --thinking 8192 \
    --max-num-seqs 128 --shard $i/$N > logs/full-v11t-a$i.log 2>&1 &
done
wait
echo "A done $(date)"
for i in $(seq 0 $((N - 1))); do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py c --items all --tag gemma_v11c --condense-a-tag gemma_v11t \
    --condense-values-only --shard $i/$N > logs/full-v11c-c$i.log 2>&1 &
done
wait
echo "DONE $(date)"
