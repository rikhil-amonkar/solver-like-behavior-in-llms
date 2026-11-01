#!/bin/bash
# Extra worker for one model's remaining cross-FL runs, alongside run_crossfl_gpu7.sh (forward
# queue) and run_crossfl_claim.sh (backward queue). Unlike run_crossfl_claim.sh it never takes a
# run another worker has claimed, and it marks each run it takes as started (the forward queue's
# log name), so the backward queue stops before reaching it. The forward queue skips claimed runs
# in run_inference.py.
# Usage (inside tmux): GPU=0 MODEL=qwen RUNS="zebralogic:python:caution_a ..." bash scripts/run_crossfl_extra.sh
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
export CUDA_VISIBLE_DEVICES=$GPU RUN_CLAIM=gpu$GPU
if [ -n "$(nvidia-smi -i $GPU --query-compute-apps=pid --format=csv,noheader)" ]; then
  echo "GPU $GPU is busy; not starting"; nvidia-smi; exit 1
fi
extra=""; [ $MODEL = gpt ] && extra="--max-tokens 384000"

# Claim every run up front so neither queue starts one of them
mine=""
for run in $RUNS; do
  IFS=: read task fl cond <<< "$run"
  dir=output_crossfl/$MODEL/$task; mkdir -p $dir
  claim=$dir/${cond}_inference.claim
  if [ -e $claim ] && [ "$(cat $claim)" != "$RUN_CLAIM" ]; then echo "$task $cond claimed by $(cat $claim); leaving it"; continue; fi
  if [ -e logs/crossfl-$MODEL-$task-$cond.log ] || [ -e $dir/${cond}_inference.json ]; then echo "$task $cond already started; leaving it"; continue; fi
  echo $RUN_CLAIM > $claim
  echo "claimed by $RUN_CLAIM ($(date)); this run's log is logs/crossfl-$MODEL-$task-$cond-$RUN_CLAIM.log" > logs/crossfl-$MODEL-$task-$cond.log
  mine="$mine $run"
done

for run in $mine; do
  IFS=: read task fl cond <<< "$run"
  flag=""; [ $cond = caution_a ] && flag="--caution-a"; [ $cond = caution_b ] && flag="--caution-b"
  dir=output_crossfl/$MODEL/$task
  log=logs/crossfl-$MODEL-$task-$cond-$RUN_CLAIM.log
  echo "== $MODEL $task/$fl $cond $(date)"
  python src/run_inference.py --task $task --fl $fl --model $MODEL $flag $extra \
    --batch-size 100 --continue > $log 2>&1 || { echo "inference failed"; continue; }
  python src/run_execution.py --input $dir/${cond}_inference.json >> $log 2>&1
  python src/run_evaluation.py --input $dir/${cond}_execution.json >> $log 2>&1
  grep -E "accuracy" $log | tail -n 2
done
echo "DONE $(date)"
