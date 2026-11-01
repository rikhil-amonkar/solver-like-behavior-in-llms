#!/usr/bin/env bash
# Clone and build the local PDDL tools used for BlocksWorld into repos/ (git-ignored):
#   repos/downward/fast-downward.py   Fast Downward planner (execution stage)
#   repos/VAL/build/bin/Validate      VAL plan validator (execution + evaluation)
# Requires cmake, g++, make, flex and bison.
set -euo pipefail
cd "$(dirname "$0")/.."

FD_COMMIT=487e33cd68c8d5ed1a766ac1efb4cc57f37dcf6f
VAL_COMMIT=3c7a1f330bdab0ba28a4762bb45c3f06c27fb6d4
mkdir -p repos

if [ ! -d repos/downward ]; then
  git clone https://github.com/aibasel/downward.git repos/downward
fi
git -C repos/downward checkout -q "$FD_COMMIT"
(cd repos/downward && python3 build.py -j "$(nproc)")

if [ ! -d repos/VAL ]; then
  git clone https://github.com/KCL-Planning/VAL.git repos/VAL
fi
git -C repos/VAL checkout -q "$VAL_COMMIT"
mkdir -p repos/VAL/build
(cd repos/VAL/build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j "$(nproc)")

ls repos/downward/builds/release/bin/downward repos/VAL/build/bin/Validate
