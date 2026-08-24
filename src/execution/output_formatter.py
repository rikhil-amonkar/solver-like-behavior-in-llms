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
    Parse zebralogic grid output from Z3 code.

    Expected format (from Z3):
        House 1: Peter, desert, white
        House 2: Alice, cherry, green
        ...

    Alternative format (structured):
        {"header": ["House", "Name", "Smoothie", "Color"], "rows": [["1", "Peter", "desert", "white"], ...]}

    This parser is lenient and will accept partial solutions (e.g., missing columns).
    Missing attributes are filled with empty strings. The evaluation stage will catch
    these as incorrect solutions rather than parse errors.

    Args:
        stdout: Output string from Z3 execution
        problem_data: Problem data containing header info (golden_solution.header)

    Returns:
        Dict with header and rows (padded with empty strings if needed), or None if parsing fails entirely
    """
    import ast

    stdout = stdout.strip()

    # Try structured format first (dict with header and rows)
    try:
        parsed = ast.literal_eval(stdout)
        if isinstance(parsed, dict) and "header" in parsed and "rows" in parsed:
            return parsed
    except (ValueError, SyntaxError):
        pass

    try:
        parsed = json.loads(stdout)
        if isinstance(parsed, dict) and "header" in parsed and "rows" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Extract header from problem_data
    headers = None
    if problem_data:
        golden = problem_data.get("golden_solution", {})
        headers = problem_data.get("headers") or problem_data.get("header") or golden.get("header") or golden.get("headers")

    if not headers:
        # Cannot parse without headers
        return None

    # Parse "House X: attr1, attr2, ..." format (most common Z3 output)
    lines = [line.strip() for line in stdout.split('\n') if line.strip()]
    rows = []

    for line in lines:
        # Skip non-house lines
        if not line.startswith("House"):
            continue

        # Extract house number and attributes
        if ':' not in line:
            continue

        parts = line.split(':', 1)
        house_str = parts[0].strip()
        attrs_str = parts[1].strip()

        # Handle leading comma or whitespace
        if attrs_str.startswith(','):
            attrs_str = attrs_str[1:].strip()

        # Extract house number
        try:
            house_num = int(house_str.replace("House", "").strip())
        except ValueError:
            continue

        # Parse attributes (comma-separated)
        attr_values = [v.strip() for v in attrs_str.split(',') if v.strip()]

        # Check if format uses key=value pairs or positional values
        if '=' in attrs_str:
            # Format: "House 1: Name=Peter, Smoothie=desert, Color=white"
            row = [str(house_num)]
            for attr_name in headers[1:]:  # Skip "House" column
                found = False
                for attr_val in attr_values:
                    if '=' in attr_val:
                        key, val = attr_val.split('=', 1)
                        if key.strip().lower() == attr_name.lower():
                            row.append(val.strip())
                            found = True
                            break
                if not found:
                    row.append("")  # Missing attribute
        else:
            # Format: "House 1: Peter, desert, white" (positional)
            # Build row with house number + provided attributes
            row = [str(house_num)] + attr_values

            # Pad with empty strings if we have fewer attributes than expected
            # This allows partial solutions to be parsed (they'll be marked incorrect during evaluation)
            while len(row) < len(headers):
                row.append("")

        # Accept row even if it has fewer attributes than expected (will be caught during evaluation)
        # Only reject if it has MORE attributes than expected (truly malformed)
        if len(row) <= len(headers):
            # Pad to correct length if needed
            while len(row) < len(headers):
                row.append("")
            rows.append(row)

    # Sort by house number
    rows.sort(key=lambda r: int(r[0]) if r[0].isdigit() else 0)

    if rows:
        return {"header": headers, "rows": rows}

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
