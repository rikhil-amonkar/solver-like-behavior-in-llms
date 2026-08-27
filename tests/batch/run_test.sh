#!/bin/bash
#
# Test batch chunking pipeline with 5 examples
#
# Usage:
#   ./tests/batch/run_test.sh output/deepseek/calendar/baseline_execution.json
#

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <execution-json-path>"
    echo "Example: $0 output/deepseek/calendar/baseline_execution.json"
    exit 1
fi

EXECUTION_JSON="$1"
TEST_DIR="tests/batch"
TEST_DATA="${TEST_DIR}/test_execution.json"
TEST_OUTPUT="${TEST_DIR}/test_chunking.json"
JUDGE_PROMPT="prompts/judge/llm_as_judge_for_chunking.txt"

echo "=== Batch Chunking Test (5 examples) ==="
echo ""

# Step 1: Prepare test data
echo "Step 1: Preparing test data (5 examples)..."
python "${TEST_DIR}/prepare_test_data.py" \
    --input "${EXECUTION_JSON}" \
    --output "${TEST_DATA}" \
    --n 5

echo ""

# Step 2: Run batch chunking
echo "Step 2: Running batch chunking..."
python src/run_chunking.py \
    --input "${TEST_DATA}" \
    --judge-prompt "${JUDGE_PROMPT}"

echo ""
echo "=== Test Complete ==="
echo "Test output: ${TEST_OUTPUT}"
echo ""
echo "To inspect results:"
echo "  cat ${TEST_OUTPUT} | jq '.summary'"
echo "  cat ${TEST_OUTPUT} | jq '.examples[0].chunk_analysis'"
