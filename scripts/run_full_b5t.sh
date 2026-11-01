#!/bin/bash
# Full B run (2026-10-30): B judge gemma_b5t (thinking 16384) on every trace with a program,
# sharded over four flex GPUs (judging cap).
# Usage: bash scripts/run_full_b5t.sh G0 G1 G2 G3     (run inside tmux; logs in logs/)
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
G=("$@")
for i in 0 1 2 3; do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py b --items all --tag gemma_b5t --thinking 16384 \
    --shard $i/4 > logs/full-b5t-b$i.log 2>&1 &
done
wait
echo "DONE $(date)"
