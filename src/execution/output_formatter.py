"""Output formatting utilities for execution stage."""

import re
import json
from typing import Any, Optional


def parse_output_by_task(stdout: str, task: str, problem_data: Optional[dict] = None) -> Optional[Any]:
    """
    Parse code execution output based on task type.

    Args:
        stdout: Standard output from code execution
        task: Task name (calendar, meeting, zebralogic, blocksworld)
        problem_data: Optional problem data (needed for some tasks like zebralogic)

    Returns:
        Parsed output in task-specific format, or None if parsing fails
    """
    if not stdout or not stdout.strip():
        return None

    stdout = stdout.strip()

    if task == "calendar":
        return parse_calendar_output(stdout)
    elif task == "meeting":
        return parse_meeting_output(stdout)
    elif task == "zebralogic":
        return parse_zebralogic_output(stdout, problem_data)
    elif task == "blocksworld":
        return parse_blocksworld_output(stdout)
    else:
        # Unknown task, return raw stdout
        return stdout


def parse_calendar_output(stdout: str) -> Optional[list]:
    """
    Parse calendar scheduling output.

    Expected format: ['Day', 'HH:MM', 'HH:MM']
    Example: ['Monday', '13:30', '14:30']

    Args:
        stdout: Output string

    Returns:
        List [day, start_time, end_time] or None
    """
    import ast

    stdout = stdout.strip()

    try:
        # Try to parse as Python literal (handles single quotes from print())
        parsed = ast.literal_eval(stdout)
        if isinstance(parsed, list) and len(parsed) == 3:
            return parsed
    except (ValueError, SyntaxError):
        pass

    try:
        # Try to parse as JSON array (handles double quotes)
        parsed = json.loads(stdout)
        if isinstance(parsed, list) and len(parsed) == 3:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract from string format
    # Look for patterns like: ['Monday', '13:30', '14:30']
    match = re.search(r"\[['\"](.*?)['\"],\s*['\"](.*?)['\"],\s*['\"](.*?)['\"]\]", stdout)
    if match:
        return [match.group(1), match.group(2), match.group(3)]

    # Try simpler format: Monday 13:30 14:30 or Monday, 13:30, 14:30
    match = re.search(r"(\w+)[,\s]+(\d{1,2}:\d{2})[,\s]+(\d{1,2}:\d{2})", stdout)
    if match:
        return [match.group(1), match.group(2), match.group(3)]

    return None


def parse_meeting_output(stdout: str) -> Optional[list]:
    """
    Parse meeting planning output.

    Expected format: List of itinerary strings
    Example: ['You start at Home at 08:00', 'You travel to Office...', ...]

    Args:
        stdout: Output string

    Returns:
        List of itinerary steps or None
    """
    import ast

    stdout = stdout.strip()

    try:
        # Try to parse as Python literal (handles single quotes from print())
        parsed = ast.literal_eval(stdout)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, SyntaxError):
        pass

    try:
        # Try to parse as JSON array (handles double quotes)
        parsed = json.loads(stdout)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to split by newlines (each line is a step)
    lines = [line.strip() for line in stdout.split('\n') if line.strip()]
    if lines and len(lines) > 1:
        return lines

    return None


def parse_zebralogic_output(stdout: str, problem_data: Optional[dict] = None) -> Optional[dict]:
    """
    Parse zebralogic grid output.

    Expected format: Grid with header and rows
    Example: {"header": ["Name", "Age", "City"], "rows": [["Alice", "25", "NYC"], ...]}

    Args:
        stdout: Output string
        problem_data: Problem data containing grid structure info

    Returns:
        Dict with header and rows, or None
    """
    import ast

    stdout = stdout.strip()

    try:
        # Try to parse as Python literal (handles single quotes from print())
        parsed = ast.literal_eval(stdout)
        if isinstance(parsed, dict) and "header" in parsed and "rows" in parsed:
            return parsed
    except (ValueError, SyntaxError):
        pass

    try:
        # Try to parse as JSON (handles double quotes)
        parsed = json.loads(stdout)
        if isinstance(parsed, dict) and "header" in parsed and "rows" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract header from problem_data if available
    if problem_data and "header" in problem_data:
        header = problem_data["header"]

        # Try to parse rows from output
        lines = [line.strip() for line in stdout.split('\n') if line.strip()]
        rows = []

        for line in lines:
            # Try to parse as Python literal first
            try:
                row = ast.literal_eval(line)
                if isinstance(row, list) and len(row) == len(header):
                    rows.append(row)
                    continue
            except (ValueError, SyntaxError):
                pass

            # Try to parse as JSON
            try:
                row = json.loads(line)
                if isinstance(row, list) and len(row) == len(header):
                    rows.append(row)
                    continue
            except (json.JSONDecodeError, ValueError):
                pass

            # Try to split by common delimiters
            for delimiter in [',', '|', '\t']:
                parts = [p.strip() for p in line.split(delimiter)]
                if len(parts) == len(header):
                    rows.append(parts)
                    break

        if rows:
            return {"header": header, "rows": rows}

    return None


def parse_blocksworld_output(stdout: str) -> Optional[dict]:
    """
    Parse blocksworld PDDL output.

    For PDDL tasks, the parsed output comes from execution_result, not stdout.
    This function is kept for compatibility but returns a structured summary.

    Expected format: Dict with plan summary
    Example: {"plan_found": True, "plan_length": 10, "val_valid": True}

    Args:
        stdout: Output string (planner output)

    Returns:
        Dict with plan summary, or None if no plan info found
    """
    # For PDDL, stdout contains planner output which is not the "parsed output"
    # The actual PDDL is extracted in code_executor_pddl.py
    # We just return a summary indicating if a plan was mentioned

    if not stdout or not stdout.strip():
        return None

    # Check if stdout mentions a plan
    stdout_lower = stdout.lower()

    if "plan" in stdout_lower or "solution" in stdout_lower:
        # Count lines that look like actions (simplified heuristic)
        action_lines = [line for line in stdout.split('\n')
                       if line.strip() and not line.strip().startswith(';')]

        return {
            "plan_found": True,
            "plan_length": len(action_lines),
            "planner_output": stdout[:500]  # First 500 chars of planner output
        }

    return {
        "plan_found": False,
        "planner_output": stdout[:500] if stdout else ""
    }
