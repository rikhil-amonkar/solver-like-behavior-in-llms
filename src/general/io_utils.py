"""I/O utilities for loading/saving JSON and parsing data files."""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# Task to file mapping
TASK_TO_PROBLEMS_FILE = {
    "calendar": "calendar_scheduling_100.json",
    "meeting": "meeting_planning_100.json",
    "zebralogic": "zebralogic_grid_100.json",
    "blocksworld": "blocksworld_100.json",
}

TASK_TO_CONSTRAINTS_FILE = {
    "calendar": "calendar_scheduling_constraints.json",
    "meeting": "meeting_planning_constraints.json",
    # zebralogic and blocksworld constraints are embedded in problem statements
    # No separate constraints files needed
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


def load_problems_with_solutions(task: str) -> dict:
    """
    Load problems JSON and extract golden solutions.

    Args:
        task: Task name (calendar, meeting, etc.)

    Returns:
        Dict mapping example_id to golden solution (parsed into expected format)
    """
    problems = load_problems_json(task)
    solutions = {}

    for example_id, problem_data in problems.items():
        raw_solution = problem_data.get("golden_solution")
        if raw_solution:
            # Parse the golden solution based on task type
            parsed = parse_golden_solution(raw_solution, task)
            if parsed:
                solutions[example_id] = parsed

    return solutions


def parse_golden_solution(raw_solution, task: str):
    """
    Parse raw golden solution into expected format.

    Args:
        raw_solution: Raw solution from problems JSON (string or list depending on task)
        task: Task name to determine parsing logic

    Returns:
        Parsed solution in expected format, or None if parsing fails
    """
    import re

    if task == "calendar":
        # Format: "Here is the proposed time: Monday, 13:30 - 14:30"
        # Extract: ["Monday", "13:30", "14:30"]
        if isinstance(raw_solution, str):
            match = re.search(r'(\w+),\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', raw_solution)
            if match:
                day, start, end = match.groups()
                return [day, start, end]
        return None

    elif task == "meeting":
        # Meeting golden solutions are already lists of itinerary steps
        # Format: ["You start at X at Y", "You travel to...", ...]
        if isinstance(raw_solution, list):
            # Return as-is if it's already a list
            return raw_solution
        return None

    elif task == "zebralogic":
        # ZebraLogic golden solutions are dicts with header and rows
        # Format: {"header": [...], "rows": [[...], [...]]}
        if isinstance(raw_solution, dict):
            # Return as-is, evaluator will parse the grid structure
            return raw_solution
        return None

    elif task == "blocksworld":
        # BlocksWorld golden solutions are dicts with PDDL domain and problem
        # Format: {"domain_pddl": "...", "problem_pddl": "..."}
        if isinstance(raw_solution, dict):
            # Return as-is, evaluator will compare PDDL structures
            return raw_solution
        return None

    return None


def load_constraints_json(task: str) -> dict:
    """
    Load constraints dataset for a given task.

    Args:
        task: Task name (calendar, meeting, zebralogic, blocksworld)

    Returns:
        Dict with constraints data (empty dict for tasks with embedded constraints)

    Raises:
        ValueError: If task is unknown
        FileNotFoundError: If constraints file not found
    """
    # Check if task has a separate constraints file
    if task not in TASK_TO_CONSTRAINTS_FILE:
        # For tasks like zebralogic/blocksworld, constraints are in problem statements
        if task in TASK_TO_PROBLEMS_FILE:
            return {}  # Return empty dict, constraints are embedded
        else:
            raise ValueError(f"Unknown task: {task}. Choose from: {list(TASK_TO_PROBLEMS_FILE.keys())}")

    constraints_file = TASK_TO_CONSTRAINTS_FILE.get(task)
    if not constraints_file:
        # Task exists but has no separate constraints file
        return {}

    constraints_path = get_repo_root() / "data" / "constraints" / constraints_file

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

    Writes results as JSONL during execution, converts to JSON when complete.
    """

    def __init__(self, output_path: str, metadata: dict, summary: Optional[dict] = None):
        """
        Initialize incremental writer.

        Args:
            output_path: Path to output JSON file
            metadata: Run metadata to write at start
            summary: Optional summary to write at start (if known upfront)
        """
        self.output_path = Path(output_path)
        self.jsonl_path = self.output_path.with_suffix('.jsonl')
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata = metadata
        self.summary = summary
        self.count = 0
        self.file_handle = None

    def __enter__(self):
        """Open JSONL file for writing."""
        self.file_handle = self.jsonl_path.open("w", encoding="utf-8")

        # Write metadata as first line
        self.file_handle.write(json.dumps({"_metadata": self.metadata}) + "\n")

        # Write summary placeholder if provided
        if self.summary is not None:
            self.file_handle.write(json.dumps({"_summary": self.summary}) + "\n")

        self.file_handle.flush()
        return self

    def write_example(self, example: dict):
        """
        Write a single example as a JSONL line.

        Args:
            example: Example data to write
        """
        # Write example as single line
        self.file_handle.write(json.dumps(example) + "\n")
        self.file_handle.flush()
        self.count += 1

    def finalize_with_summary(self, summary: dict):
        """
        Close JSONL and convert to JSON.

        Args:
            summary: Final summary statistics
        """
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()

        # Convert JSONL to JSON
        self._convert_jsonl_to_json(summary)

    def _convert_jsonl_to_json(self, final_summary: dict):
        """
        Convert JSONL file to final JSON format.

        Args:
            final_summary: Final summary to include
        """
        # Read all lines from JSONL
        examples = []
        metadata = None

        with self.jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)

                # Check for special keys
                if "_metadata" in obj:
                    metadata = obj["_metadata"]
                elif "_summary" in obj:
                    # Skip placeholder summary
                    continue
                else:
                    # Regular example
                    examples.append(obj)

        # Build final JSON structure
        final_data = {
            "run_metadata": metadata or self.metadata,
        }

        # Add summary if we have it
        if final_summary is not None:
            final_data["summary"] = final_summary

        # Add examples
        final_data["examples"] = examples

        # Write final JSON
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Remove JSONL file
        self.jsonl_path.unlink()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the JSONL file and convert to JSON."""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()

            # Convert to JSON (without summary update)
            if exc_type is None:  # Only convert if no exception
                self._convert_jsonl_to_json(self.summary)


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


def make_path_relative(path: str) -> str:
    """
    Convert absolute path to relative path from repo root.

    Args:
        path: Absolute or relative path

    Returns:
        Path relative to repository root
    """
    path_obj = Path(path)
    repo_root = get_repo_root()

    try:
        # If path is absolute and within repo, make it relative
        if path_obj.is_absolute():
            return str(path_obj.relative_to(repo_root))
        else:
            # Already relative
            return str(path_obj)
    except ValueError:
        # Path is not relative to repo root, return as-is
        return str(path_obj)
