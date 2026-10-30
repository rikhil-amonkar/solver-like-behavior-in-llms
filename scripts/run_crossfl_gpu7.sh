#!/bin/bash
# Cross-FL runs: Calendar in Z3-Python and ZebraLogic in plain Python, so that dataset and formal
# language are crossed (native: Calendar=Python, ZebraLogic=Z3). Qwen and GPT-OSS on GPU 7, all
# three conditions, then execution and evaluation. Outputs go to output_crossfl/.
# Settings match the native runs: Qwen max_tokens 131072 (default), GPT-OSS 384000 (clamped to
# the context), default sampling.
# Usage (inside tmux): bash scripts/run_crossfl_gpu7.sh
# With WAIT_FOR=<tmux session>, first waits for that session to end. Resumable (--continue).
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
export CUDA_VISIBLE_DEVICES=7
if [ -n "${WAIT_FOR:-}" ]; then
  while tmux has-session -t "$WAIT_FOR" 2>/dev/null; do sleep 60; done
  echo "$WAIT_FOR ended $(date)"; sleep 60
fi
if [ -n "$(nvidia-smi -i 7 --query-compute-apps=pid --format=csv,noheader)" ]; then
  echo "GPU 7 is busy; not starting"; nvidia-smi; exit 1
fi
for model in qwen gpt; do
  extra=""; [ $model = gpt ] && extra="--max-tokens 384000"
  for pair in calendar:z3 zebralogic:python; do
    task=${pair%%:*}; fl=${pair##*:}
    for cond in baseline caution_a caution_b; do
      flag=""; [ $cond = caution_a ] && flag="--caution-a"; [ $cond = caution_b ] && flag="--caution-b"
      dir=output_crossfl/$model/$task
      echo "== $model $task/$fl $cond $(date)"
      python src/run_inference.py --task $task --fl $fl --model $model $flag $extra \
        --batch-size 100 --continue > logs/crossfl-$model-$task-$cond.log 2>&1 || { echo "inference failed"; continue; }
      python src/run_execution.py --input $dir/${cond}_inference.json >> logs/crossfl-$model-$task-$cond.log 2>&1
      python src/run_evaluation.py --input $dir/${cond}_execution.json >> logs/crossfl-$model-$task-$cond.log 2>&1
      grep -E "accuracy" logs/crossfl-$model-$task-$cond.log | tail -n 2
    done
  done
done
echo "DONE $(date)"
