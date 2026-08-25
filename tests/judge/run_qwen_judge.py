#!/usr/bin/env python3
"""
Judge reasoning chunks using Qwen3.8-27B.

Usage:
    python tests/judge/run_qwen_judge.py --prompt tests/judge/boolean_judge_prompt.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.call_qwen import call_qwen


def load_dataset(dataset_path: str) -> dict:
    """Load the reasoning chunks dataset."""
    with open(dataset_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_prompt(prompt_path: str) -> str:
    """Load the judge prompt template."""
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_judge_response(response: str) -> str:
    """
    Parse judge response to extract classification.
    Tries multiple parsing strategies for robustness.

    Returns:
        "sound", "solver-like", or "error"
    """
    try:
        # Strategy 1: Look for JSON in markdown code block
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        # Strategy 2: Look for any code block
        elif "```" in response:
            json_start = response.find("```") + 3
            # Skip language identifier if present
            first_newline = response.find("\n", json_start)
            if first_newline != -1:
                json_start = first_newline + 1
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        # Strategy 3: Find JSON object in text
        elif "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
        else:
            # Strategy 4: Look for keywords in plain text
            response_lower = response.lower()
            if "solver-like" in response_lower or "solver_like" in response_lower:
                return "solver-like"
            elif "sound" in response_lower:
                return "sound"
            return "error"

        # Clean up common JSON issues
        json_str = json_str.strip()
        # Remove trailing commas before closing braces
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        # Parse JSON
        data = json.loads(json_str)

        # Extract solver_like boolean
        if "solver_like" in data:
            return "solver-like" if data["solver_like"] else "sound"
        elif "classification" in data:
            # Alternative field name
            classification = data["classification"].lower()
            if "solver" in classification:
                return "solver-like"
            elif "sound" in classification:
                return "sound"

        return "error"
    except Exception as e:
        print(f"Parse error: {e}")
        # Last resort: keyword search
        response_lower = response.lower()
        if "solver-like" in response_lower or "solver_like" in response_lower:
            return "solver-like"
        elif "sound" in response_lower:
            return "sound"
        return "error"


def run_judge(prompt_template: str, dataset: dict) -> list:
    """
    Run judge on all chunks in dataset.

    Returns:
        List of dicts with chunk_id, classification, and raw_response
    """
    results = []
    chunks = dataset["chunks"]

    print(f"Judging {len(chunks)} reasoning chunks with Qwen3.8-27B...")

    for i, chunk in enumerate(chunks, 1):
        chunk_id = chunk["chunk_id"]
        reasoning_chunk = chunk["reasoning_chunk"]

        print(f"[{i}/{len(chunks)}] Judging chunk {chunk_id}...", end=" ")

        # Build full prompt
        full_prompt = f"{prompt_template}\n\n# Reasoning Trace to Judge\n\n{reasoning_chunk}"

        try:
            # Call Qwen using repo's model caller
            result = call_qwen(full_prompt, max_tokens=2048, enable_thinking=False)
            response = result["reasoning_trace"]

            # Parse response
            classification = parse_judge_response(response)

            print(f"✓ {classification}")

            results.append({
                "chunk_id": chunk_id,
                "dataset": chunk["dataset"],
                "model": chunk["model"],
                "example_id": chunk["example_id"],
                "classification": classification,
                "raw_response": response
            })

        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                "chunk_id": chunk_id,
                "dataset": chunk["dataset"],
                "model": chunk["model"],
                "example_id": chunk["example_id"],
                "classification": "error",
                "raw_response": str(e)
            })

    return results


def write_results_to_markdown(results: list, model_name: str, output_dir: Path, dataset: dict):
    """
    Write results to a unique markdown file.

    Creates a new file with timestamp in the filename.
    Includes ground truth matching and accuracy calculation.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    # Create unique filename
    output_path = output_dir / f"{model_name.lower().replace('.', '_').replace('-', '_')}_{timestamp}.md"

    # Build ground truth lookup from dataset
    ground_truth = {}
    for chunk in dataset["chunks"]:
        key = (chunk["dataset"], chunk["model"], chunk["example_id"])
        if "ground_truth" in chunk:
            ground_truth[key] = chunk["ground_truth"].lower()

    # Match results with ground truth
    for result in results:
        key = (result["dataset"], result["model"], result["example_id"])
        result["ground_truth"] = ground_truth.get(key, "unknown")

    # Build markdown table
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {model_name} Judge Results\n\n")
        f.write(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

        # Summary statistics
        total = len(results)
        sound_count = sum(1 for r in results if r["classification"] == "sound")
        solver_count = sum(1 for r in results if r["classification"] == "solver-like")
        error_count = sum(1 for r in results if r["classification"] == "error")

        f.write(f"**Summary**: {total} chunks judged\n")
        f.write(f"- Sound: {sound_count} ({sound_count/total*100:.1f}%)\n")
        f.write(f"- Solver-like: {solver_count} ({solver_count/total*100:.1f}%)\n")
        f.write(f"- Errors: {error_count} ({error_count/total*100:.1f}%)\n\n")

        # Results table
        f.write("| Chunk ID | Dataset | Model | Example ID | Classification | Ground Truth |\n")
        f.write("|----------|---------|-------|------------|----------------|--------------|\\n")

        for result in results:
            f.write(f"| {result['chunk_id']} | {result['dataset']} | {result['model']} | {result['example_id']} | {result['classification']} | {result['ground_truth']} |\n")

        f.write("\n")

        # Calculate accuracy
        correct = 0
        incorrect_chunks = []
        for result in results:
            if result["ground_truth"] != "unknown" and result["classification"] != "error":
                if result["classification"] == result["ground_truth"]:
                    correct += 1
                else:
                    incorrect_chunks.append({
                        "chunk_id": result["chunk_id"],
                        "classification": result["classification"],
                        "ground_truth": result["ground_truth"]
                    })

        # Count total judged (excluding errors and unknown ground truth)
        total_judged = sum(1 for r in results if r["ground_truth"] != "unknown" and r["classification"] != "error")

        if total_judged > 0:
            accuracy = correct / total_judged * 100
            f.write(f"**Judge Accuracy**: {correct}/{total_judged} ({accuracy:.1f}%)\n")
            f.write(f"- Correct: {correct}\n")
            f.write(f"- Incorrect: {len(incorrect_chunks)}")
            if incorrect_chunks:
                f.write(" (")
                f.write(", ".join([
                    f"Chunk ID {ic['chunk_id']}: classified as {ic['classification']}, ground truth is {ic['ground_truth']}"
                    for ic in incorrect_chunks
                ]))
                f.write(")")
            f.write("\n")

    print(f"\n✓ Results written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Qwen3.8-27B judge on reasoning chunks"
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Path to judge prompt file"
    )
    parser.add_argument(
        "--dataset",
        default="tests/judge/reasoning_chunks_dataset.json",
        help="Path to dataset JSON (default: tests/judge/reasoning_chunks_dataset.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="tests/judge/results",
        help="Directory for output markdown files (default: tests/judge/results)"
    )

    args = parser.parse_args()

    # Load dataset and prompt
    dataset = load_dataset(args.dataset)
    prompt = load_prompt(args.prompt)

    # Run judge
    results = run_judge(prompt, dataset)

    # Write results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_results_to_markdown(results, "Qwen3.8-27B", output_dir, dataset)

    print(f"\n✓ Judging complete!")
    print(f"  Sound: {sum(1 for r in results if r['classification'] == 'sound')}")
    print(f"  Solver-like: {sum(1 for r in results if r['classification'] == 'solver-like')}")
    print(f"  Errors: {sum(1 for r in results if r['classification'] == 'error')}")


if __name__ == "__main__":
    main()
