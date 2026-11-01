#!/bin/bash
# Cross-FL runs for DeepSeek (API, no GPU): Calendar and Meeting in Z3-Python, ZebraLogic and BlocksWorld in
# plain Python, three conditions each, in parallel. PAIRS="task:fl ..." picks a subset.
# Waits until .env has DEEPSEEK_API_KEY. max_tokens 131072
# as in the native DeepSeek runs. Usage (inside tmux): bash scripts/run_crossfl_deepseek.sh
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
export CUDA_VISIBLE_DEVICES=
until grep -qE '^DEEPSEEK_API_KEY=.+' .env 2>/dev/null; do sleep 30; done
echo "key found $(date)"
run() {
  task=$1 fl=$2 cond=$3; flag=""
  [ $cond = caution_a ] && flag="--caution-a"; [ $cond = caution_b ] && flag="--caution-b"
  log=logs/crossfl-deepseek-$task-$cond.log; dir=output_crossfl/deepseek/$task
  python src/run_inference.py --task $task --fl $fl --model deepseek $flag --max-tokens 131072 \
    --continue > $log 2>&1 || return
  python src/run_execution.py --input $dir/${cond}_inference.json >> $log 2>&1
  python src/run_evaluation.py --input $dir/${cond}_execution.json >> $log 2>&1
  echo "== deepseek $task $cond $(date)"; grep -E "accuracy|Errors" $log | tail -n 3
}
for pair in ${PAIRS:-calendar:z3 meeting:z3 zebralogic:python blocksworld:python}; do
  for cond in baseline caution_a caution_b; do run ${pair%%:*} ${pair##*:} $cond & done
done
wait
echo "DONE $(date)"
