"""I/O utilities for loading/saving JSON and parsing data files."""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# Task to file mapping
TASK_TO_PROBLEMS_FILE = {
    "calendar": "calendar_scheduling_100.json",
    "meeting": "meeting_planning_100.json",
}

TASK_TO_CONSTRAINTS_FILE = {
    "calendar": "calendar_scheduling_constraints.json",
    "meeting": "meeting_planning_constraints.json",
}


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent.parent


def load_problems_json(task: str) -> dict:
    """
    Load problem dataset for a given task.

    Args:
        task: Task name (calendar, meeting)

    Returns:
        Dict mapping example_id to problem data

    Raises:
        ValueError: If task is unknown
        FileNotFoundError: If problems file not found
    """
    if task not in TASK_TO_PROBLEMS_FILE:
        raise ValueError(f"Unknown task: {task}. Choose from: {list(TASK_TO_PROBLEMS_FILE.keys())}")

    problems_path = get_repo_root() / "data" / "problems" / TASK_TO_PROBLEMS_FILE[task]

    if not problems_path.exists():
        raise FileNotFoundError(f"Problems file not found: {problems_path}")

    with problems_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_constraints_json(task: str) -> dict:
    """
    Load constraints dataset for a given task.

    Args:
        task: Task name (calendar, meeting)

    Returns:
        Dict with constraints data

    Raises:
        ValueError: If task is unknown
        FileNotFoundError: If constraints file not found
    """
    if task not in TASK_TO_CONSTRAINTS_FILE:
        raise ValueError(f"Unknown task: {task}. Choose from: {list(TASK_TO_CONSTRAINTS_FILE.keys())}")

    constraints_path = get_repo_root() / "data" / "constraints" / TASK_TO_CONSTRAINTS_FILE[task]

    if not constraints_path.exists():
        raise FileNotFoundError(f"Constraints file not found: {constraints_path}")

    with constraints_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_output(data: dict, output_path: str) -> None:
    """
    Save pipeline output as JSON with pretty printing.

    Args:
        data: Data to save
        output_path: Path to output file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json_file(file_path: str) -> dict:
    """
    Load JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class IncrementalJSONWriter:
    """
    Write JSON array incrementally to avoid memory issues.

    Writes results as they're generated rather than accumulating in memory.
    """

    def __init__(self, output_path: str, metadata: dict):
        """
        Initialize incremental writer.

        Args:
            output_path: Path to output JSON file
            metadata: Run metadata to write at start
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata = metadata
        self.count = 0
        self.file_handle = None

    def __enter__(self):
        """Open file and write initial structure."""
        self.file_handle = self.output_path.open("w", encoding="utf-8")
        # Write opening structure
        self.file_handle.write("{\n")
        self.file_handle.write(f'  "run_metadata": {json.dumps(self.metadata, indent=2).replace(chr(10), chr(10) + "  ")},\n')
        self.file_handle.write('  "examples": [\n')
        self.file_handle.flush()
        return self

    def write_example(self, example: dict):
        """
        Write a single example to the array.

        Args:
            example: Example data to write
        """
        if self.count > 0:
            self.file_handle.write(",\n")

        # Write example with proper indentation
        example_json = json.dumps(example, indent=2).replace("\n", "\n    ")
        self.file_handle.write(f"    {example_json}")
        self.file_handle.flush()
        self.count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the JSON structure and file."""
        if self.file_handle:
            self.file_handle.write("\n  ]\n")
            self.file_handle.write("}\n")
            self.file_handle.close()


def get_output_path(model: str, task: str, stage: str, condition: str = "baseline") -> Path:
    """
    Get standard output path for a pipeline stage.

    Args:
        model: Model name (deepseek, qwen, gpt)
        task: Task name (calendar, meeting)
        stage: Stage name (inference, evaluation, chunking)
        condition: Condition name (baseline, caution)

    Returns:
        Path to output file
    """
    filename = f"{condition}_{stage}.json"
    return get_repo_root() / "output" / model / task / filename


def get_timestamp() -> str:
    """Get current timestamp in ISO 8601 format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
