#!/usr/bin/env python3
"""
Inference pipeline runner.

Calls models with CSP prompts, extracts code, executes it, and saves results incrementally.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import (
    load_problems_json,
    get_output_path,
    get_timestamp,
    IncrementalJSONWriter,
)
from general.prompt_utils import (
    load_prompt_template,
    get_task_prompts,
    build_full_prompt,
)
from general.cli import ProgressTracker
from inference.model_caller import call_model


def run_inference_pipeline(
    task: str,
    model: str,
    num_examples: int = None,
    max_tokens: int = None,
    caution_variant: str = None,
):
    """
    Run inference pipeline for a task and model.

    Args:
        task: Task name (calendar, meeting, zebralogic, blocksworld)
        model: Model name (deepseek, qwen, gpt)
        num_examples: Number of examples to process (None = all)
        max_tokens: Max tokens for generation (None = use model default)
        caution_variant: Cautionary suffix variant ('a' or 'b'), or None for baseline
    """
    condition = f"caution_{caution_variant}" if caution_variant else "baseline"

    print(f"\n=== Inference Pipeline ===")
    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Examples: {num_examples or 'all'}")
    print(f"Max tokens: {max_tokens or 'default'}")
    print()

    # Load problems
    print("Loading problems...")
    problems = load_problems_json(task)
    example_ids = list(problems.keys())

    # Limit examples if requested
    if num_examples is not None:
        example_ids = example_ids[:num_examples]

    print(f"Loaded {len(example_ids)} examples")

    # Load prompts
    print("Loading prompts...")
    universal_prefix_path, output_format_path = get_task_prompts(task)
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

    # Prepare output path
    output_path = get_output_path(model, task, "inference", condition)
    print(f"Output: {output_path}\n")

    # Build run metadata
    metadata = {
        "task": task,
        "model": model,
        "model_full_name": get_model_full_name(model),
        "condition": condition,
        "cautionary_suffix_enabled": bool(caution_variant),
        "cautionary_suffix_variant": caution_variant,
        "timestamp": get_timestamp(),
        "num_examples": len(example_ids),
        "max_tokens": max_tokens,
    }

    # Process examples with incremental JSON writing
    success_count = 0

    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        with ProgressTracker(len(example_ids), f"Processing {task}") as progress:
            for example_id in example_ids:
                try:
                    # Get problem
                    problem_data = problems[example_id]
                    problem_text = problem_data.get("problem", "")

                    # Build prompt
                    full_prompt = build_full_prompt(
                        universal_prefix,
                        problem_text,
                        output_format,
                        cautionary_suffix
                    )

                    # Call model
                    model_result = call_model(
                        model,
                        full_prompt,
                        max_tokens=max_tokens
                    )

                    reasoning_trace = model_result["reasoning_trace"]
                    model_metadata = model_result["metadata"]

                    # Build example result (only reasoning trace, no execution)
                    example_result = {
                        "example_id": example_id,
                        "problem_text": problem_text,
                        "reasoning_trace": reasoning_trace,
                        "model_metadata": model_metadata,
                    }

                    # Write immediately
                    writer.write_example(example_result)
                    success_count += 1

                except Exception as e:
                    # Log error but continue
                    print(f"\nError on {example_id}: {str(e)}")

                    # Write error example
                    error_result = {
                        "example_id": example_id,
                        "problem_text": problem_data.get("problem", ""),
                        "reasoning_trace": "",
                        "model_metadata": {
                            "error": str(e),
                        },
                    }
                    writer.write_example(error_result)

                # Update progress
                progress.update(1)
                progress.set_postfix(success=success_count)

    print(f"\n✓ Inference complete!")
    print(f"  Processed: {success_count}/{len(example_ids)}")
    print(f"  Output: {output_path}")


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

    args = parser.parse_args()

    try:
        run_inference_pipeline(
            task=args.task,
            model=args.model,
            num_examples=args.num_examples,
            max_tokens=args.max_tokens,
            caution_variant=args.caution_variant,
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
