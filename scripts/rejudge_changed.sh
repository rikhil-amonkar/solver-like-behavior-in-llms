#!/bin/bash
# Judge only the traces whose text changed (e.g. after scripts/reexecute_changed.py) with the final
# judges, then reassemble the labels. The judges cache results by item id + text hash, so a full
# --items all run judges just the changed items. One GPU, one shard.
# Usage (inside tmux): GPU=1 bash scripts/rejudge_changed.sh output|output_crossfl
set -eu
cd /local-ssd/hz466/solver-like-behavior-in-llms
source /local-ssd/hz466/vllm-test/env.sh
ROOT=$1
export CUDA_VISIBLE_DEVICES=${GPU:?set GPU to a free flex GPU}
J="python src/run_ontology_judges.py --items all --root $ROOT"
echo "== A $(date)"; $J a --tag gemma_v11t --thinking 8192 --max-num-seqs 128 --wave-size 256
echo "== B $(date)"; $J b --tag gemma_b5t --thinking 16384
echo "== C $(date)"; $J c --tag gemma_v11c --condense-a-tag gemma_v11t --condense-values-only
python scripts/assemble_ontology_labels.py --root $ROOT --tag gemma_v11_b5t --a-tag gemma_v11t --b-tag gemma_b5t \
  --c-tag gemma_v11c
echo "DONE $(date)"
