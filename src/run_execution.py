#!/usr/bin/env python3
"""
Execution pipeline runner.

Extracts code from reasoning traces, executes it, and formats output.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import (
    load_json_file,
    load_problems_json,
    get_timestamp,
    IncrementalJSONWriter,
    make_path_relative,
)
from general.cli import ProgressTracker
from execution.code_extractor import (
    split_reasoning_and_code,
    clean_extracted_code,
    validate_code_extraction,
)
from execution.output_formatter import parse_output_by_task
from inference.code_executor import execute_code_by_language, get_language_from_task

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        encoding: Tiktoken encoding name (default: cl100k_base for GPT-4)

    Returns:
        Token count, or -1 if tiktoken not available
    """
    if not TIKTOKEN_AVAILABLE or not text:
        return -1

    try:
        tokenizer = tiktoken.get_encoding(encoding)
        return len(tokenizer.encode(text))
    except Exception:
        # Fallback: return -1 to indicate unavailable
        return -1


def run_execution_pipeline(
    inference_json_path: str,
    code_timeout: float = 30.0,
):
    """
    Run execution pipeline on inference results.

    Args:
        inference_json_path: Path to inference JSON output
        code_timeout: Timeout for code execution in seconds
    """
    print(f"\n=== Execution Pipeline ===")
    print(f"Input: {inference_json_path}\n")

    # Load inference results
    print("Loading inference results...")
    inference_data = load_json_file(inference_json_path)

    task = inference_data["run_metadata"]["task"]
    model = inference_data["run_metadata"]["model"]
    condition = inference_data["run_metadata"].get("condition", "baseline")
    examples = inference_data["examples"]

    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Condition: {condition}")
    print(f"Examples: {len(examples)}")

    # Load problem data (needed for some tasks like zebralogic)
    print("Loading problem data...")
    problems = load_problems_json(task)

    # Determine output path (use same condition as inference)
    inference_path = Path(inference_json_path)
    output_filename = f"{condition}_execution.json"
    output_path = inference_path.parent / output_filename
    print(f"Output: {output_path}\n")

    # Build metadata
    metadata = {
        "task": task,
        "model": model,
        "condition": condition,
        "inference_json": make_path_relative(str(inference_json_path)),
        "timestamp": get_timestamp(),
        "num_examples": len(examples),
        "code_timeout_sec": code_timeout,
    }

    # Process examples
    success_count = 0
    error_count = 0
    language = get_language_from_task(task)

    with IncrementalJSONWriter(str(output_path), metadata) as writer:
        with ProgressTracker(len(examples), f"Executing {task}") as progress:
            for example in examples:
                try:
                    example_id = example["example_id"]
                    reasoning_trace = example.get("reasoning_trace", "")
                    problem_data = problems.get(example_id, {})

                    # Split reasoning and extract code
                    reasoning_before_code, extracted_code = split_reasoning_and_code(
                        reasoning_trace
                    )

                    # Clean and validate extracted code
                    if extracted_code:
                        extracted_code = clean_extracted_code(extracted_code)

                        # Validate code looks reasonable (not strict syntax check)
                        if not validate_code_extraction(extracted_code, language):
                            print(f"\n  ⚠ Warning: Extracted code for {example_id} may be malformed")

                    # Execute code if present
                    if extracted_code and extracted_code.strip():
                        # For zebralogic, pass problem data for header extraction
                        # For blocksworld (PDDL), pass groundtruth problem PDDL
                        extra_kwargs = {}
                        if task == "zebralogic":
                            extra_kwargs["problem_data"] = problem_data
                        elif task == "blocksworld":
                            extra_kwargs["groundtruth_problem_pddl"] = problem_data.get("groundtruth_problem_pddl")

                        code_result = execute_code_by_language(
                            extracted_code,
                            language=language,
                            timeout_sec=code_timeout,
                            **extra_kwargs
                        )

                        # Parse output if execution succeeded
                        # For PDDL, check 'ran' instead of 'exit_code'
                        if language == "pddl":
                            # PDDL returns different structure: ran, syntax_valid, plan_found, val_valid
                            if code_result.get("ran") and code_result.get("stdout"):
                                parsed_output = parse_output_by_task(
                                    code_result["stdout"],
                                    task,
                                    problem_data
                                )
                                code_result["parsed_output"] = parsed_output
                            else:
                                code_result["parsed_output"] = None
                        else:
                            # Python/Z3 standard execution
                            if code_result.get("exit_code") == 0 and code_result.get("stdout"):
                                parsed_output = parse_output_by_task(
                                    code_result["stdout"],
                                    task,
                                    problem_data
                                )
                                code_result["parsed_output"] = parsed_output
                            else:
                                code_result["parsed_output"] = None

                    else:
                        # No code extracted
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

                    # Count tokens for reasoning and code
                    reasoning_tokens = count_tokens(reasoning_before_code or "")
                    code_tokens = count_tokens(extracted_code or "")

                    # Build execution result
                    execution_result = {
                        "example_id": example_id,
                        "reasoning_before_code": reasoning_before_code,
                        "reasoning_before_code_tokens": reasoning_tokens,
                        "extracted_code": extracted_code,
                        "extracted_code_tokens": code_tokens,
                        "code_execution": code_result,
                    }

                    writer.write_example(execution_result)

                    # Count success based on language type
                    if language == "pddl":
                        if code_result.get("ran") and code_result.get("syntax_valid"):
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        if code_result.get("exit_code") == 0:
                            success_count += 1
                        else:
                            error_count += 1

                except Exception as e:
                    # Log error but continue
                    error_count += 1
                    print(f"\nError on {example.get('example_id', '?')}: {str(e)}")

                    # Write error example
                    error_result = {
                        "example_id": example.get("example_id", "unknown"),
                        "reasoning_before_code": "",
                        "reasoning_before_code_tokens": 0,
                        "extracted_code": "",
                        "extracted_code_tokens": 0,
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
                    }
                    writer.write_example(error_result)

                # Update progress
                progress.update(1)
                progress.set_postfix(success=success_count, errors=error_count)

        # Finalize with summary
        summary = {
            "total_examples": len(examples),
            "successful_executions": success_count,
            "failed_executions": error_count,
        }
        writer.finalize_with_summary(summary)

    print(f"\n✓ Execution complete!")
    print(f"  Success: {success_count}/{len(examples)}")
    print(f"  Errors: {error_count}/{len(examples)}")
    print(f"  Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run execution pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/run_execution.py --input output/deepseek/calendar/baseline_inference.json
  python src/run_execution.py --input output/qwen/meeting/caution_a_inference.json --timeout 60
        """
    )

    parser.add_argument(
        "--input",
        "--inference-json",
        required=True,
        dest="inference_json",
        help="Path to inference JSON output"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout for code execution in seconds (default: 30)"
    )

    args = parser.parse_args()

    try:
        run_execution_pipeline(
            args.inference_json,
            code_timeout=args.timeout,
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
