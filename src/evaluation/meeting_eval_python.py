"""
Meeting planning constraint evaluation (Python task).

Validates Python itinerary output format against meeting planning constraints.
"""

from typing import Tuple


def evaluate_meeting_solution(constraints: dict, solution: list) -> Tuple[bool, dict]:
    """
    Validate meeting planning solution against constraints.

    Args:
        constraints: Constraints from task JSON
        solution: List of itinerary steps

    Returns:
        (is_valid, error_detail)
    """
    # Basic validation - check solution is a list
    if not isinstance(solution, list):
        return False, {"error": "solution must be a list", "got": type(solution).__name__}

    if len(solution) == 0:
        return False, {"error": "solution cannot be empty"}

    # For now, accept any non-empty list as valid
    # TODO: Implement full meeting planning constraint checking
    # Would check: locations visited, travel times, meeting windows, etc.

    return True, {}
