"""Calendar scheduling constraint evaluation."""

from datetime import datetime
from typing import Tuple, Optional


def evaluate_calendar_solution(constraints: dict, solution: list) -> Tuple[bool, dict]:
    """
    Validate calendar scheduling solution against constraints.

    Args:
        constraints: Constraints from task JSON
        solution: ['Monday', '13:30', '14:30'] format

    Returns:
        (is_valid, error_detail)
    """
    # Check solution shape
    if not isinstance(solution, list) or len(solution) != 3:
        return False, {"error": "expected list of 3 strings", "got": solution}

    if not all(isinstance(x, str) for x in solution):
        return False, {"error": "all elements must be strings", "got": solution}

    day, start_str, end_str = solution

    # Parse times
    start_hours = parse_time_to_hours(start_str)
    end_hours = parse_time_to_hours(end_str)

    if start_hours is None or end_hours is None:
        return False, {"error": "invalid time format", "start": start_str, "end": end_str}

    if end_hours <= start_hours:
        return False, {"error": "end time must be after start time", "start_hours": start_hours, "end_hours": end_hours}

    # Check duration
    actual_duration = end_hours - start_hours
    expected_duration = float(constraints.get("meeting_duration", 0))

    if abs(actual_duration - expected_duration) > 0.01:
        return False, {
            "error": "duration mismatch",
            "expected": expected_duration,
            "actual": actual_duration
        }

    # Check no overlap with disallowed ranges
    disallowed = constraints.get("disallowed_ranges", [])
    for dr in disallowed:
        if dr.get("day") != day:
            continue

        range_start = float(dr["start"])
        range_end = float(dr["end"])

        # Check for overlap
        if start_hours < range_end and end_hours > range_start:
            return False, {
                "error": "overlaps disallowed range",
                "range": dr
            }

    return True, {}


def parse_time_to_hours(time_str: str) -> Optional[float]:
    """
    Parse time string to hours as float.

    Supports:
    - 24-hour: "13:30" -> 13.5
    - 12-hour: "1:30 PM" -> 13.5
    """
    if not time_str or not time_str.strip():
        return None

    try:
        t = time_str.strip().upper()

        # Try 12-hour format first
        if "AM" in t or "PM" in t:
            t_clean = t.replace(" ", "")
            dt = datetime.strptime(t_clean, "%I:%M%p")
        else:
            # 24-hour format
            dt = datetime.strptime(time_str.strip(), "%H:%M")

        return dt.hour + dt.minute / 60.0

    except ValueError:
        return None
