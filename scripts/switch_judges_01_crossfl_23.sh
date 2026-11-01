#!/bin/bash
# One-off (2026-10-30, Harry): move the full-v11 judge run from GPUs 0-3 to 0,1 and run the
# Qwen/GPT-OSS cross-FL pairings on 2 (Qwen) and 3 (GPT-OSS).
# 1. Pause run_full_v11.sh so it cannot start its C stage on all four GPUs (killing it would
#    end its tmux session and hang up the shards still running).
# 2. Stop A shards 2 and 3 right after their next wave is written (nothing is lost: the judge
#    caches by item, reading every shard file), then start cross-FL on the freed GPU.
# 3. When shards 0 and 1 finish, judge the remaining A items and then C over two shards on 0,1.
# Usage (inside tmux): bash scripts/switch_judges_01_crossfl_23.sh ORCHESTRATOR_PID
set -u
cd /local-ssd/hz466/solver-like-behavior-in-llms
ORCH=$1
kill -STOP "$ORCH" && echo "paused run_full_v11.sh ($ORCH) $(date)"
shard_pid() { pgrep -f "run_ontology_judges.py a .*--tag gemma_v11t .*--shard $1/4"; }
progress() { grep -E "^[0-9]+/[0-9]+ judged" logs/full-v11t-a$1.log | tail -n 1 | cut -d/ -f1; }
gpu_free() { [ -z "$(nvidia-smi -i $1 --query-compute-apps=pid --format=csv,noheader)" ]; }
start_crossfl() {  # gpu model
  tmux new -d -s crossfl-$2 "GPU=$1 MODELS=$2 bash scripts/run_crossfl_gpu7.sh 2>&1 | tee logs/crossfl-$2.log"
  echo "started crossfl-$2 on GPU $1 $(date)"
}
declare -A TARGET MODEL=([2]=qwen [3]=gpt)
for s in 2 3; do TARGET[$s]=$(( $(progress $s) + 1024 )); echo "shard $s: stop after ${TARGET[$s]}"; done
left="2 3"
while [ -n "$left" ]; do
  next=""
  for s in $left; do
    pid=$(shard_pid $s)
    if [ -z "$pid" ] || [ "$(progress $s)" -ge "${TARGET[$s]}" ]; then
      if [ -n "$pid" ]; then  # the shard and its vLLM engine process
        kids=$(pgrep -P $pid); kill $pid $kids; echo "stopped shard $s at $(progress $s) $(date)"
        for i in $(seq 120); do gpu_free $s && break; sleep 5; done
        gpu_free $s || { kill -KILL $pid $kids 2>/dev/null; sleep 30; }
      fi
      if gpu_free $s; then start_crossfl $s ${MODEL[$s]}; else echo "GPU $s still busy"; nvidia-smi; fi
    else next="$next $s"; fi
  done
  left=$next; [ -n "$left" ] && sleep 20
done
while [ -n "$(shard_pid 0)$(shard_pid 1)" ]; do sleep 60; done
echo "shards 0,1 done $(date)"
kill -KILL "$ORCH"
source /local-ssd/hz466/vllm-test/env.sh
G=(0 1)
for g in "${G[@]}"; do gpu_free $g || { echo "GPU $g busy; stopping"; nvidia-smi; exit 1; }; done
for i in 0 1; do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py a --items all --tag gemma_v11t --thinking 8192 \
    --max-num-seqs 128 --shard $i/2 > logs/full-v11t-a$i-r2.log 2>&1 &
done
wait
echo "A done $(date)"
for i in 0 1; do
  CUDA_VISIBLE_DEVICES=${G[$i]} python src/run_ontology_judges.py c --items all --tag gemma_v11c --condense-a-tag gemma_v11t \
    --condense-values-only --shard $i/2 > logs/full-v11c-c$i.log 2>&1 &
done
wait
echo "DONE $(date)"
