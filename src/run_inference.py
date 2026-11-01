#!/usr/bin/env python3
"""
Inference pipeline runner.

Calls models with CSP prompts, extracts code, executes it, and saves results incrementally.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import (
    load_problems_json,
    get_output_path,
    get_timestamp,
    IncrementalJSONWriter,
    load_json_file,
)
from general.prompt_utils import (
    load_prompt_template,
    get_task_prompts,
    build_full_prompt,
    TASK_FL,
    get_repo_root,
)
from general.cli import ProgressTracker
from inference.model_caller import call_model, call_model_batch
from deter.batching import make_groups, build_batch_prompt


def run_inference_pipeline(
    task: str,
    model: str,
    num_examples: int = None,
    offset: int = 0,
    max_tokens: int = None,
    caution_variant: str = None,
    continue_run: bool = False,
    batch_size: int = None,
    output_root: str = None,
    fl: str = None,
    batch_k: int = None,
    placeholder: bool = False,
):
    """
    Run inference pipeline for a task and model.

    Args:
        task: Task name (calendar, meeting, zebralogic, blocksworld)
        model: Model name (deepseek, qwen, gpt)
        num_examples: Number of examples to process (None = all)
        offset: Skip this many examples first (to split a run across GPUs)
        max_tokens: Max tokens for generation (None = use model default)
        caution_variant: Cautionary suffix variant ('a' or 'b'), or None for baseline
        continue_run: Resume from last completed example in existing JSONL
        batch_size: Batch size for vLLM models (None = auto: 16 for qwen/gpt, 1 for deepseek)
        output_root: Output root directory (None = <repo>/output, or output_crossfl for a non-native FL)
        fl: Formal language ('python', 'z3'); None = the task's native one
        batch_k: Put this many problems in each prompt, one program per problem (docs/DETERRENCE_DESIGN.md)
        placeholder: Replace the problem's values with placeholders (data/placeholders/)
    """
    condition = f"caution_{caution_variant}" if caution_variant else "baseline"
    if batch_k:
        condition = f"batch_k{batch_k}"
    elif placeholder:
        condition = "placeholder"
    fl = fl or TASK_FL[task]
    if (batch_k or placeholder) and output_root is None:
        # Deterrence methods: kept out of output/ and output_crossfl/
        output_root = str(get_repo_root() / ("output_deter" if fl == TASK_FL[task] else "output_deter_crossfl"))
    if fl != TASK_FL[task] and output_root is None:
        # Keep cross-FL runs out of output/, which the judges and tables read
        output_root = str(get_repo_root() / "output_crossfl")

    # Auto-select batch size if not specified
    if batch_size is None:
        # vLLM models benefit from batching, DeepSeek is API-based (sequential)
        batch_size = 16 if model in ["qwen", "gpt"] else 1

    print(f"\n=== Inference Pipeline ===")
    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Formal language: {fl}")
    print(f"Examples: {num_examples or 'all'}")
    print(f"Max tokens: {max_tokens or 'default'}")
    print(f"Batch size: {batch_size}")
    print(f"Continue mode: {continue_run}")
    print()

    # Load problems
    print("Loading problems...")
    problems = load_problems_json(task)
    example_ids = list(problems.keys())

    # Limit examples if requested
    example_ids = example_ids[offset:]
    if num_examples is not None:
        example_ids = example_ids[:num_examples]

    print(f"Loaded {len(example_ids)} examples")

    # Load prompts
    print("Loading prompts...")
    universal_prefix_path, output_format_path = get_task_prompts(task, fl)
    universal_prefix = load_prompt_template(universal_prefix_path)
    output_format = load_prompt_template(output_format_path)

    # Load cautionary suffix if enabled
    cautionary_suffix = ""
    if caution_variant:
        cautionary_suffix_path = f"prompts/cautionary/universal_cautionary_suffix_{caution_variant}.txt"
        try:
            cautionary_suffix = load_prompt_template(cautionary_suffix_path)
            print(f"Cautionary suffix variant '{caution_variant}' loaded")
        except FileNotFoundError:
            print(f"Warning: Cautionary suffix file not found at {cautionary_suffix_path}, proceeding without it")
            cautionary_suffix = ""

    print("Prompts loaded")

    # Deterrence methods: a record per group of K problems, or per placeholder problem
    prompt_overrides, record_extras = {}, {}
    if placeholder:
        converted = load_json_file(str(get_repo_root() / "data" / "placeholders" / f"{task}_placeholders.json"))
        note = load_prompt_template(f"prompts/deter/placeholder_note_{task}.txt").strip()
        problems = {eid: {**problems[eid], "problem": f"{note}\n\n{converted[eid]['problem']}"} for eid in example_ids}
    if batch_k:
        lang = "z3" if fl == "z3" else "python"
        batch_prefix = load_prompt_template(f"prompts/deter/batch_prefix_{lang}.txt")
        batch_suffix = load_prompt_template("prompts/deter/batch_suffix.txt")
        groups = make_groups(example_ids, batch_k)
        group_problems = {}
        for g, members in enumerate(groups):
            gid = f"group_k{batch_k}_{g:02d}"
            texts = [problems[eid]["problem"] for eid in members]
            group_problems[gid] = {"problem": "\n\n".join(texts)}
            prompt_overrides[gid] = build_batch_prompt(batch_prefix, texts, output_format, batch_suffix)
            record_extras[gid] = {"member_ids": members, "batch_k": batch_k}
        problems, example_ids = group_problems, list(group_problems)
        print(f"{len(example_ids)} groups of up to {batch_k} problems")

    # Prepare output path
    output_path = get_output_path(model, task, "inference", condition, output_root)
    print(f"Output: {output_path}\n")
    # A run can be claimed by one worker (a <cond>_inference.claim file naming it, matched against
    # $RUN_CLAIM) so that two queues sharing a model's runs never write the same output.
    claim = output_path.with_suffix(".claim")
    if claim.exists() and claim.read_text().strip() != os.environ.get("RUN_CLAIM", ""):
        print(f"{output_path.name} is claimed by {claim.read_text().strip()}; skipping")
        sys.exit(3)

    # Handle continuation mode
    completed_ids = set()
    existing_metadata = None
    if continue_run:
        jsonl_path = output_path.with_suffix('.jsonl')
        if jsonl_path.exists():
            print(f"Found existing JSONL at {jsonl_path}")
            completed_ids, existing_metadata = _load_completed_examples(jsonl_path)

            if completed_ids:
                print(f"Resuming from {len(completed_ids)} completed examples")
                # Filter out completed IDs from example_ids
                example_ids = [eid for eid in example_ids if eid not in completed_ids]
                print(f"Remaining examples to process: {len(example_ids)}")
            else:
                print("No completed examples found in JSONL, starting fresh")
        else:
            print(f"No existing JSONL found at {jsonl_path}, starting fresh")

    # Build run metadata (use existing if continuing, otherwise create new)
    if existing_metadata:
        metadata = existing_metadata
        metadata["resumed_at"] = get_timestamp()
    else:
        metadata = {
            "task": task,
            "model": model,
            "model_full_name": get_model_full_name(model),
            "condition": condition,
            "fl": fl,
            "cautionary_suffix_enabled": bool(caution_variant),
            "cautionary_suffix_variant": caution_variant,
            "batch_k": batch_k,
            "placeholder": placeholder,
            "timestamp": get_timestamp(),
            "num_examples": len(example_ids) + len(completed_ids),
            "max_tokens": max_tokens,
        }

    # Process examples with incremental JSON writing (batch mode)
    success_count = len(completed_ids)
    error_count = 0

    with IncrementalJSONWriter(str(output_path), metadata, continue_mode=continue_run) as writer:
        with ProgressTracker(len(example_ids), f"Processing {task}") as progress:
            # Process in batches
            for batch_start in range(0, len(example_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(example_ids))
                batch_ids = example_ids[batch_start:batch_end]

                try:
                    # Build prompts for entire batch
                    batch_prompts = []
                    batch_problem_texts = []
                    for example_id in batch_ids:
                        problem_data = problems[example_id]
                        problem_text = problem_data.get("problem", "")
                        batch_problem_texts.append(problem_text)

                        # Build prompt (pass problem_data for PDDL tasks with groundtruth info)
                        full_prompt = prompt_overrides.get(example_id) or build_full_prompt(
                            universal_prefix,
                            problem_text,
                            output_format,
                            cautionary_suffix,
                            problem_data=problem_data if task == "blocksworld" else None
                        )
                        batch_prompts.append(full_prompt)

                    # Call model in batch mode
                    if batch_size == 1:
                        # Single prompt: use non-batch interface
                        batch_results = [call_model(model, batch_prompts[0], max_tokens=max_tokens)]
                    else:
                        # Batch inference
                        batch_results = call_model_batch(model, batch_prompts, max_tokens=max_tokens)

                    # Process batch results
                    for idx, (example_id, model_result) in enumerate(zip(batch_ids, batch_results)):
                        try:
                            reasoning_trace = model_result["reasoning_trace"]
                            model_metadata = model_result["metadata"]

                            # Build example result (only reasoning trace, no execution)
                            example_result = {
                                "example_id": example_id,
                                "problem_text": batch_problem_texts[idx],
                                "reasoning_trace": reasoning_trace,
                                "model_metadata": model_metadata,
                                **record_extras.get(example_id, {}),
                            }

                            # Write immediately
                            writer.write_example(example_result)
                            success_count += 1

                        except Exception as e:
                            # Log error but continue
                            error_count += 1
                            print(f"\nError processing result for {example_id}: {str(e)}")

                            # Write error example
                            error_result = {
                                "example_id": example_id,
                                "problem_text": batch_problem_texts[idx],
                                **record_extras.get(example_id, {}),
                                "reasoning_trace": "",
                                "model_metadata": {
                                    "error": str(e),
                                },
                            }
                            writer.write_example(error_result)

                        # Update progress
                        progress.update(1)
                        progress.set_postfix(success=success_count, errors=error_count)

                except Exception as e:
                    # Batch-level error: mark all examples in batch as failed
                    error_count += len(batch_ids)
                    print(f"\nBatch error for {batch_ids}: {str(e)}")

                    for idx, example_id in enumerate(batch_ids):
                        error_result = {
                            "example_id": example_id,
                            "problem_text": problems[example_id].get("problem", ""),
                            **record_extras.get(example_id, {}),
                            "reasoning_trace": "",
                            "model_metadata": {
                                "error": f"Batch processing error: {str(e)}",
                            },
                        }
                        writer.write_example(error_result)

                        # Update progress
                        progress.update(1)
                        progress.set_postfix(success=success_count, errors=error_count)

        # Finalize with summary
        total_examples = len(example_ids) + len(completed_ids)
        summary = {
            "total_examples": total_examples,
            "successful": success_count,
            "errors": error_count,
        }
        writer.finalize_with_summary(summary)

    print(f"\n✓ Inference complete!")
    print(f"  Processed: {success_count}/{total_examples}")
    print(f"  Errors: {error_count}/{total_examples}")
    print(f"  Output: {output_path}")


def _load_completed_examples(jsonl_path: Path) -> tuple[set, dict]:
    """
    Load completed example IDs from existing JSONL.

    Args:
        jsonl_path: Path to existing JSONL file

    Returns:
        Tuple of (set of completed example IDs, metadata dict)
    """
    import json

    completed_ids = set()
    metadata = None

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)

            # Extract metadata if present
            if "_metadata" in obj:
                metadata = obj["_metadata"]
            # Skip summary placeholders
            elif "_summary" in obj:
                continue
            # Regular example
            elif "example_id" in obj:
                completed_ids.add(obj["example_id"])

    return completed_ids, metadata


def get_model_full_name(model: str) -> str:
    """Get full model identifier."""
    model_names = {
        "deepseek": "deepseek-v4-flash",
        "qwen": "Qwen/Qwen3.8-27B",
        "gpt": "openai/gpt-oss-120b",
    }
    return model_names.get(model, model)


def main():
    parser = argparse.ArgumentParser(
        description="Run inference pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Baseline (no cautionary suffix)
  python src/run_inference.py --task calendar --model deepseek --n 10

  # With cautionary suffix variant A
  python src/run_inference.py --task calendar --model deepseek --n 10 --caution-a

  # With cautionary suffix variant B
  python src/run_inference.py --task calendar --model deepseek --n 10 --caution-b

  python src/run_inference.py --task meeting --model qwen --max-tokens 100000
  python src/run_inference.py --task zebralogic --model deepseek --n 10
  python src/run_inference.py --task blocksworld --model gpt --n 5
        """
    )

    parser.add_argument(
        "--task",
        required=True,
        choices=["calendar", "meeting", "zebralogic", "blocksworld"],
        help="Task to run"
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=["deepseek", "qwen", "gpt"],
        help="Model to use"
    )
    parser.add_argument(
        "--n",
        "--num-examples",
        type=int,
        default=None,
        dest="num_examples",
        help="Number of examples to process (default: all)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip this many examples first (with --n, splits a run across GPUs)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max tokens for generation (default: model-specific from .env)"
    )
    # Cautionary suffix variants (mutually exclusive)
    caution_group = parser.add_mutually_exclusive_group()
    caution_group.add_argument(
        "--caution-a",
        action="store_const",
        const="a",
        dest="caution_variant",
        help="Include cautionary suffix variant A in prompts"
    )
    caution_group.add_argument(
        "--caution-b",
        action="store_const",
        const="b",
        dest="caution_variant",
        help="Include cautionary suffix variant B in prompts"
    )
    parser.add_argument(
        "--continue",
        action="store_true",
        dest="continue_run",
        help="Resume from last completed example in existing JSONL (skips completed examples)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for vLLM models (default: auto-detect - 16 for qwen/gpt, 1 for deepseek)"
    )

    parser.add_argument(
        "--fl",
        choices=["python", "z3"],
        default=None,
        help="Formal language; blocksworld also takes python (default: the task's native one; a non-native one writes to output_crossfl/)"
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Output root directory (default: output/). Use a scratch dir for test runs."
    )
    deter_group = parser.add_mutually_exclusive_group()
    deter_group.add_argument(
        "--batch-k",
        type=int,
        default=None,
        help="Deterrence: K problems per prompt, one program each (writes to output_deter/; --n counts problems)"
    )
    deter_group.add_argument(
        "--placeholder",
        action="store_true",
        help="Deterrence: values replaced by placeholders, given to the program as VALUES (calendar, meeting)"
    )

    args = parser.parse_args()

    try:
        run_inference_pipeline(
            task=args.task,
            model=args.model,
            num_examples=args.num_examples,
            offset=args.offset,
            max_tokens=args.max_tokens,
            caution_variant=args.caution_variant,
            continue_run=args.continue_run,
            batch_size=args.batch_size,
            output_root=args.output_root,
            fl=args.fl,
            batch_k=args.batch_k,
            placeholder=args.placeholder,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
