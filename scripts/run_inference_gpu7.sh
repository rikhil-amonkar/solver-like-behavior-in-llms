#!/usr/bin/env bash
# Run src/run_inference.py on GPU 7 with vllm-env, in a detached tmux session.
# Arguments are passed through to run_inference.py.
#
# Usage:
#   scripts/run_inference_gpu7.sh --task calendar --model qwen --caution-a
#   scripts/run_inference_gpu7.sh --task meeting --model qwen --n 2 --output-root output_test
#
# Check on it with: tmux capture-pane -p -t <session>; tail -f logs/<session>.log
set -euo pipefail
cd "$(dirname "$0")/.."

name="infer-$(echo "$*" | tr -cs 'A-Za-z0-9' '-' | sed 's/^-//; s/-$//')"
mkdir -p logs
args=$(printf '%q ' "$@")

tmux new -d -s "$name" \
  "source /local-ssd/hz466/vllm-test/env.sh && export CUDA_VISIBLE_DEVICES=7 && python src/run_inference.py $args 2>&1 | tee logs/$name.log"
echo "tmux session: $name"
echo "log: logs/$name.log"
