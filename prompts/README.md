# Prompts Directory

This directory contains all prompt templates used in the inference and chunking pipelines.

## Prompt Structure

### Inference Prompts

The inference stage builds prompts by combining:
1. **Universal CSP Prefix** (`universal_csp_prefix.txt`) - Frames all tasks as CSPs
2. **Problem Text** - Injected via `{PROBLEM}` placeholder
3. **Task-Specific Output Format** - Defines expected output structure

Example for calendar task:
```
[universal_csp_prefix.txt content]
{PROBLEM} ← replaced with actual problem
[calendar_output_format.txt content]
```

### Task Output Formats

- `calendar_output_format.txt` - Calendar scheduling: `['Monday', '13:30', '14:00']`
- `meeting_output_format.txt` - Meeting planning: itinerary steps
- `blocksworld_output_format.txt` - (placeholder for future)
- `zebralogic_output_format.txt` - (placeholder for future)

### Judge Prompts

- `llm_as_judge_for_chunking.txt` - Gemini judge prompt for chunking reasoning traces
  into "sound" vs "solver-like" segments

### Other

- `universal_cautionary_suffix.txt` - (placeholder, currently unused)
