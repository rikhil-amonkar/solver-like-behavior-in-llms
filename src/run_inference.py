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
from general.parsing_utils import split_reasoning_and_code, extract_code_block
from general.cli import ProgressTracker
from inference.model_caller import call_model
from inference.code_executor import run_code


def run_inference_pipeline(
    task: str,
    model: str,
    num_examples: int = None,
    max_tokens: int = None,
    code_timeout: float = 30.0,
    use_caution: bool = False,
):
    """
    Run inference pipeline for a task and model.

    Args:
        task: Task name (calendar, meeting)
        model: Model name (deepseek, qwen, gpt)
        num_examples: Number of examples to process (None = all)
        max_tokens: Max tokens for generation (None = use model default)
        code_timeout: Timeout for code execution in seconds
        use_caution: Whether to include cautionary suffix in prompts
    """
    condition = "caution" if use_caution else "baseline"

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
    if use_caution:
        cautionary_suffix_path = "prompts/universal_cautionary_suffix.txt"
        try:
            cautionary_suffix = load_prompt_template(cautionary_suffix_path)
            print("Cautionary suffix loaded")
        except FileNotFoundError:
            print("Warning: Cautionary suffix file not found, proceeding without it")
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
        "cautionary_suffix_enabled": use_caution,
        "timestamp": get_timestamp(),
        "num_examples": len(example_ids),
        "max_tokens": max_tokens,
        "code_timeout_sec": code_timeout,
    }

    # Process examples with incremental JSON writing
    success_count = 0
    error_count = 0

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

                    # Split reasoning and code
                    reasoning_before_code, extracted_code = split_reasoning_and_code(
                        reasoning_trace
                    )

                    # Execute code
                    if extracted_code:
                        code_result = run_code(extracted_code, timeout_sec=code_timeout)
                    else:
                        code_result = {
                            "ran": False,
                            "exit_code": None,
                            "stdout": "",
                            "stderr": "",
                            "timed_out": False,
                            "timeout_sec": code_timeout,
                            "error": "no code extracted",
                            "parsed_output": None,
                        }

                    # Build example result
                    example_result = {
                        "example_id": example_id,
                        "problem_text": problem_text,
                        "reasoning_trace": reasoning_trace,
                        "reasoning_before_code": reasoning_before_code,
                        "extracted_code": extracted_code,
                        "code_execution": code_result,
                        "model_metadata": model_metadata,
                    }

                    # Write immediately
                    writer.write_example(example_result)

                    if code_result.get("exit_code") == 0:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    # Log error but continue
                    error_count += 1
                    print(f"\nError on {example_id}: {str(e)}")

                    # Write error example
                    error_result = {
                        "example_id": example_id,
                        "problem_text": problem_data.get("problem", ""),
                        "reasoning_trace": "",
                        "reasoning_before_code": "",
                        "extracted_code": "",
                        "code_execution": {
                            "ran": False,
                            "exit_code": None,
                            "stdout": "",
                            "stderr": "",
                            "timed_out": False,
                            "timeout_sec": code_timeout,
                            "error": f"pipeline error: {str(e)}",
                            "parsed_output": None,
                        },
                        "model_metadata": {},
                    }
                    writer.write_example(error_result)

                # Update progress
                progress.update(1)
                progress.set_postfix(success=success_count, errors=error_count)

    print(f"\n✓ Inference complete!")
    print(f"  Success: {success_count}/{len(example_ids)}")
    print(f"  Errors: {error_count}/{len(example_ids)}")
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
  python src/run_inference.py --task calendar --model deepseek --n 10
  python src/run_inference.py --task meeting --model qwen --max-tokens 100000
        """
    )

    parser.add_argument(
        "--task",
        required=True,
        choices=["calendar", "meeting"],
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
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout for code execution in seconds (default: 30)"
    )
    parser.add_argument(
        "--caution",
        "--use-caution",
        action="store_true",
        dest="use_caution",
        help="Include cautionary suffix in prompts (default: False, baseline condition)"
    )

    args = parser.parse_args()

    try:
        run_inference_pipeline(
            task=args.task,
            model=args.model,
            num_examples=args.num_examples,
            max_tokens=args.max_tokens,
            code_timeout=args.timeout,
            use_caution=args.use_caution,
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
