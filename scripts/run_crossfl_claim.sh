#!/bin/bash
# Second queue for one model's cross-FL runs, working backwards through RUNS while
# run_crossfl_gpu7.sh works forwards on another GPU. Each run is claimed first
# (<cond>_inference.claim, see run_inference.py), so the forward queue skips it; the queue stops
# at the first run the forward queue has already started (its log exists).
# Usage (inside tmux): GPU=3 MODEL=qwen RUNS="blocksworld:python:caution_b ..." bash scripts/run_crossfl_claim.sh
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
export CUDA_VISIBLE_DEVICES=$GPU RUN_CLAIM=gpu$GPU
if [ -n "$(nvidia-smi -i $GPU --query-compute-apps=pid --format=csv,noheader)" ]; then
  echo "GPU $GPU is busy; not starting"; nvidia-smi; exit 1
fi
extra=""; [ $MODEL = gpt ] && extra="--max-tokens 384000"
for run in $RUNS; do
  IFS=: read task fl cond <<< "$run"
  if [ -e logs/crossfl-$MODEL-$task-$cond.log ]; then echo "$task $cond already started by the other queue; stopping"; break; fi
  flag=""; [ $cond = caution_a ] && flag="--caution-a"; [ $cond = caution_b ] && flag="--caution-b"
  dir=output_crossfl/$MODEL/$task; mkdir -p $dir; echo $RUN_CLAIM > $dir/${cond}_inference.claim
  log=logs/crossfl-$MODEL-$task-$cond-$RUN_CLAIM.log
  echo "== $MODEL $task/$fl $cond $(date)"
  python src/run_inference.py --task $task --fl $fl --model $MODEL $flag $extra \
    --batch-size 100 --continue > $log 2>&1 || { echo "inference failed"; continue; }
  python src/run_execution.py --input $dir/${cond}_inference.json >> $log 2>&1
  python src/run_evaluation.py --input $dir/${cond}_execution.json >> $log 2>&1
  grep -E "accuracy" $log | tail -n 2
done
echo "DONE $(date)"
