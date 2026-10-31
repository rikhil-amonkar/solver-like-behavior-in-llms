#!/bin/bash
# Ontology judges on the cross-FL runs (output_crossfl/, results in output_crossfl/ontology/):
# A (gemma_v11t), then B (gemma_b5t), then A2/C (gemma_v11c), with the same prompts and settings as
# the native runs, then assembly into <cond>_ontology_gemma_v11_b5t.json.
# Uses whichever of GPUs 0-3 have no process (at most four flex GPUs). While Qwen's cross-FL
# queues (tmux crossfl-qwen*) still run, A is judged in rounds: each round rebuilds the items
# (new Qwen runs join) and, when another GPU frees up, the shards are stopped right after a wave
# is cached and restarted over more GPUs. Judged items are cached, so nothing is judged twice.
# Usage (inside tmux): bash scripts/run_crossfl_judges.sh
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
ROOT=output_crossfl
free_gpus() { for g in 0 1 2 3; do [ -z "$(nvidia-smi -i $g --query-compute-apps=pid --format=csv,noheader)" ] && echo -n "$g "; done; }
qwen_running() { tmux ls 2>/dev/null | grep -q "^crossfl-qwen"; }
run_kind() {  # kind tag log-prefix extra-args...; shards over the free GPUs; returns 1 if restarted for more GPUs
  local kind=$1 tag=$2 pre=$3; shift 3
  local G=($(free_gpus)); local N=${#G[@]}
  [ $N -eq 0 ] && { echo "no free GPU; waiting"; sleep 300; return 1; }
  echo "== $kind on GPUs ${G[*]} $(date)"
  local pids=()
  for i in $(seq 0 $((N - 1))); do
    CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py $kind --items all --root $ROOT --tag $tag \
      --shard $i/$N "$@" > logs/$pre$i.log 2>&1 &
    pids+=($!)
  done
  local waves=$(cat logs/$pre*.log | grep -c " judged,")
  while kill -0 ${pids[@]} 2>/dev/null; do
    sleep 30
    local now=$(cat logs/$pre*.log | grep -c " judged,")
    if [ $now -gt $waves ]; then  # a wave was just cached: restart now if more GPUs are free
      waves=$now
      # only GPUs outside this round count: a shard that finished its share frees its own GPU
      local more=$(for g in $(free_gpus); do [[ " ${G[*]} " == *" $g "* ]] || echo -n "$g "; done)
      if [ -n "$more" ]; then
        echo "more GPUs free ($more); restarting $kind $(date)"
        for p in ${pids[@]}; do kill $p $(pgrep -P $p) 2>/dev/null; done; wait; sleep 30; return 1
      fi
    fi
  done
  wait
  qwen_running && return 1 || return 0
}
A=(--thinking 8192 --max-num-seqs 128 --wave-size 256)
until run_kind a gemma_v11t crossfl-judge-a "${A[@]}"; do sleep 60; done
echo "A done $(date)"
until run_kind b gemma_b5t crossfl-judge-b --thinking 16384; do sleep 60; done
echo "B done $(date)"
until run_kind c gemma_v11c crossfl-judge-c --condense-a-tag gemma_v11t --condense-values-only; do sleep 60; done
python scripts/assemble_ontology_labels.py --root $ROOT --tag gemma_v11_b5t --a-tag gemma_v11t --b-tag gemma_b5t \
  --c-tag gemma_v11c > logs/crossfl-judge-assemble.log 2>&1
echo "DONE $(date)"
