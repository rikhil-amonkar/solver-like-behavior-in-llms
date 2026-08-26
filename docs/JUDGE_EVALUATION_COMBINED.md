# Combined Judge Evaluation Results

**Report Generated**: 2026-08-25

This report combines judge evaluation results from multiple judge models tested on the same set of 20 ground-truth labeled reasoning chunks.

## Executive Summary

Four judge models were evaluated on their ability to classify reasoning chunks as "sound" (proper formalization) vs "solver-like" (solving in natural language):

| Judge Model | Accuracy | Correct | Incorrect | Sound Classifications | Solver-like Classifications |
|-------------|----------|---------|-----------|----------------------|----------------------------|
| **Gemini-2.5-Pro** | **95.0%** | 19/20 | 1 | 14 (70.0%) | 6 (30.0%) |
| **DeepSeek-V4-Flash** | **95.0%** | 19/20 | 1 | 14 (70.0%) | 6 (30.0%) |
| **GPT-OSS-120B** | **95.0%** | 19/20 | 1 | 14 (70.0%) | 6 (30.0%) |
| **Qwen3.8-27B** | 85.0% | 17/20 | 3 | 12 (60.0%) | 8 (40.0%) |

**Key Findings**:
- Three judges (Gemini-2.5-Pro, DeepSeek-V4-Flash, GPT-OSS-120B) achieved identical 95% accuracy
- Qwen3.8-27B showed lower accuracy (85%) with 3 misclassifications
- All three top-performing judges made the same single error (Chunk ID 7)
- Qwen3.8-27B made 2 additional errors (Chunk IDs 6 and 11)

## Detailed Results by Judge

### Gemini-2.5-Pro
**Test Date**: 2026-08-25 18:19:21 UTC
**Accuracy**: 19/20 (95.0%)

**Errors**:
- Chunk ID 7: Classified as `sound`, ground truth is `solver-like`
  - Example: `meeting_planning_example_385` (qwen3-32b model)

---

### DeepSeek-V4-Flash
**Test Date**: 2026-08-25 18:20:28 UTC
**Accuracy**: 19/20 (95.0%)

**Errors**:
- Chunk ID 7: Classified as `sound`, ground truth is `solver-like`
  - Example: `meeting_planning_example_385` (qwen3-32b model)

---

### GPT-OSS-120B
**Test Date**: 2026-08-25 18:25:41 UTC
**Accuracy**: 19/20 (95.0%)

**Errors**:
- Chunk ID 7: Classified as `sound`, ground truth is `solver-like`
  - Example: `meeting_planning_example_385` (qwen3-32b model)

---

### Qwen3.8-27B
**Test Date**: 2026-08-25 18:21:49 UTC
**Accuracy**: 17/20 (85.0%)

**Errors**:
1. Chunk ID 6: Classified as `solver-like`, ground truth is `sound`
   - Example: `calendar_scheduling_example_544` (deepseek-reasoner model)
2. Chunk ID 7: Classified as `sound`, ground truth is `solver-like`
   - Example: `meeting_planning_example_385` (qwen3-32b model)
3. Chunk ID 11: Classified as `solver-like`, ground truth is `sound`
   - Example: `meeting_planning_example_715` (gpt-oss-120b model)

---

## Error Analysis

### Common Error (All Top-3 Judges)
**Chunk ID 7**: `meeting_planning_example_385` from qwen3-32b
- All three high-performing judges classified this as `sound`
- Ground truth label is `solver-like`
- This represents a challenging edge case where solver-like behavior may be subtle

### Qwen3.8-27B Additional Errors
**Chunk ID 6**: `calendar_scheduling_example_544` from deepseek-reasoner
- Misclassified as `solver-like` (ground truth: `sound`)
- False positive for solver-like behavior

**Chunk ID 11**: `meeting_planning_example_715` from gpt-oss-120b
- Misclassified as `solver-like` (ground truth: `sound`)
- False positive for solver-like behavior

**Pattern**: Qwen3.8-27B shows tendency to over-classify as solver-like (8 total vs 6 for other judges)

---

## Full Test Set Results

Below is the complete test set showing all 20 chunks with classifications from each judge:

| Chunk ID | Dataset | Model | Example ID | Ground Truth | Gemini-2.5-Pro | DeepSeek-V4-Flash | GPT-OSS-120B | Qwen3.8-27B |
|----------|---------|-------|------------|--------------|----------------|-------------------|--------------|-------------|
| 1 | meeting | deepseek-reasoner | meeting_planning_example_974 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 2 | calendar | deepseek-reasoner | calendar_scheduling_example_707 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 3 | meeting | qwen3-32b | meeting_planning_example_813 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 4 | calendar | deepseek-reasoner | calendar_scheduling_example_583 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 5 | calendar | qwen2.5-32b-instruct | calendar_scheduling_example_473 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 6 | calendar | deepseek-reasoner | calendar_scheduling_example_544 | sound | ✓ sound | ✓ sound | ✓ sound | ✗ solver-like |
| 7 | meeting | qwen3-32b | meeting_planning_example_385 | solver-like | ✗ sound | ✗ sound | ✗ sound | ✗ sound |
| 8 | calendar | qwen3-32b | calendar_scheduling_example_356 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 9 | meeting | gpt-oss-120b | meeting_planning_example_911 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 10 | meeting | gpt-oss-120b | meeting_planning_example_409 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 11 | meeting | gpt-oss-120b | meeting_planning_example_715 | sound | ✓ sound | ✓ sound | ✓ sound | ✗ solver-like |
| 12 | meeting | qwen3-32b | meeting_planning_example_934 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 13 | calendar | gpt-oss-120b | calendar_scheduling_example_865 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 14 | meeting | qwen3-32b | meeting_planning_example_813 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 15 | meeting | deepseek-reasoner | meeting_planning_example_577 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 16 | meeting | gpt-oss-120b | meeting_planning_example_700 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 17 | calendar | qwen2.5-32b-instruct | calendar_scheduling_example_304 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 18 | calendar | deepseek-reasoner | calendar_scheduling_example_544 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |
| 19 | calendar | qwen3-32b | calendar_scheduling_example_493 | solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like | ✓ solver-like |
| 20 | meeting | qwen3-32b | meeting_planning_example_203 | sound | ✓ sound | ✓ sound | ✓ sound | ✓ sound |

**Legend**: ✓ = Correct classification, ✗ = Incorrect classification

---

## Recommendations

Based on these results:

1. **Production Use**: Gemini-2.5-Pro, DeepSeek-V4-Flash, or GPT-OSS-120B are all suitable for judge tasks with 95% accuracy
2. **Cost Consideration**: DeepSeek-V4-Flash may be most cost-effective if all three perform identically
3. **Edge Case Analysis**: Investigate Chunk ID 7 (`meeting_planning_example_385`) to understand why it's challenging for all judges
4. **Qwen3.8-27B**: Not recommended for production judging due to 10% lower accuracy and tendency to over-classify as solver-like

---

## Test Metadata

- **Test Set Size**: 20 ground-truth labeled chunks
- **Datasets**: calendar scheduling, meeting planning
- **Source Models**: deepseek-reasoner, qwen3-32b, qwen2.5-32b-instruct, gpt-oss-120b
- **Ground Truth Distribution**: 14 sound (70%), 6 solver-like (30%)
- **Original Results Location**: `tests/judge/results/`
