#!/usr/bin/env bash
# Run src/run_inference.py on one GPU with vllm-env, in a detached tmux session.
# GPU= picks the GPU; it must be a free flex GPU (no process on it, see CLAUDE.md's GPU policy).
# Other arguments are passed through to run_inference.py.
#
# Usage:
#   GPU=0 scripts/run_inference_tmux.sh --task calendar --model qwen --caution-a
#   GPU=1 scripts/run_inference_tmux.sh --task meeting --model qwen --n 2 --output-root output_test
#
# Check on it with: tmux capture-pane -p -t <session>; tail -f logs/<session>.log
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${GPU:-}" ]; then
  echo "Set GPU=<index> to a free GPU (judgement status or nvidia-smi shows which are free)"; exit 1
fi
if [ -n "$(nvidia-smi -i "$GPU" --query-compute-apps=pid --format=csv,noheader)" ]; then
  echo "GPU $GPU is busy; not starting"; exit 1
fi

name="infer-$(echo "$*" | tr -cs 'A-Za-z0-9' '-' | sed 's/^-//; s/-$//')"
mkdir -p logs
args=$(printf '%q ' "$@")

tmux new -d -s "$name" \
  "source /local-ssd/hz466/vllm-test/env.sh && export CUDA_VISIBLE_DEVICES=$GPU && python src/run_inference.py $args 2>&1 | tee logs/$name.log"
echo "tmux session: $name (GPU $GPU)"
echo "log: logs/$name.log"
