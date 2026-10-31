#!/usr/bin/env bash
# Deterrence runs (docs/DETERRENCE_DESIGN.md) for one model on one GPU, in a detached tmux session:
# inference, then src/run_execution_deter.py and src/run_evaluation.py for each cell.
# GPU= must be a free flex GPU (no process on it; see CLAUDE.md's GPU policy).
#
#   GPU=3 MODEL=qwen N=20 ROOT=output_deter_pilot scripts/run_deter.sh
#
# CELLS: space-separated task:fl:method, method = k<K> or ph (default: the pilot's four cells).
# ROOT: output root (default output_deter; use output_deter_crossfl for second-FL cells).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GPU:?set GPU}" "${MODEL:?set MODEL}"
N=${N:-100}
ROOT=${ROOT:-output_deter}
CELLS=${CELLS:-"calendar:python:k5 meeting:python:k5 calendar:python:ph meeting:python:ph"}
if [ -n "$(nvidia-smi -i "$GPU" --query-compute-apps=pid --format=csv,noheader)" ]; then
  echo "GPU $GPU is busy; not starting"; exit 1
fi
name="deter-$MODEL-$(basename "$ROOT")"
mkdir -p logs
cmds="source /local-ssd/hz466/vllm-test/env.sh && export CUDA_VISIBLE_DEVICES=$GPU"
for cell in $CELLS; do
  IFS=: read -r task fl method <<< "$cell"
  if [ "$method" = ph ]; then flag="--placeholder"; cond=placeholder; else flag="--batch-k ${method#k}"; cond="batch_$method"; fi
  inf="$ROOT/$MODEL/$task/${cond}_inference.json"
  # A failed cell does not stop the next one
  cmds+="; ( python src/run_inference.py --task $task --fl $fl --model $MODEL --n $N $flag --output-root $ROOT"
  cmds+=" && python src/run_execution_deter.py --input $inf && python src/run_evaluation.py --input ${inf%_inference.json}_execution.json )"
done
tmux new -d -s "$name" "{ $cmds; } 2>&1 | tee logs/$name.log"
echo "tmux session: $name (GPU $GPU); log: logs/$name.log"
