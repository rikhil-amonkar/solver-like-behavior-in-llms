#!/bin/bash
# Full ontology run (2026-10-30): A judge gemma_v11t (thinking) on every segment, then the A2/C
# judge gemma_v11c on every trace from the Values paragraphs. Two flex GPUs (judging cap).
# Usage: bash scripts/run_full_v11.sh GPU_A GPU_B     (run inside tmux; logs in logs/)
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
G=("$1" "$2")
for i in 0 1; do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py a --items all --tag gemma_v11t --thinking 8192 \
    --max-num-seqs 128 --shard $i/2 > logs/full-v11t-a$i.log 2>&1 &
done
wait
echo "A done $(date)"
for i in 0 1; do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py c --items all --tag gemma_v11c --condense-a-tag gemma_v11t \
    --condense-values-only --shard $i/2 > logs/full-v11c-c$i.log 2>&1 &
done
wait
echo "DONE $(date)"
