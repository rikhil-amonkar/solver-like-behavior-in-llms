"""
ZebraLogic grid puzzle constraint evaluation (Z3 task).

Validates Z3 grid table output format against logic puzzle constraints.
Checks distinctness (each attribute used exactly once) and golden solution matching.
"""

from typing import Tuple, Dict, List, Any


def evaluate_zebralogic_solution(
    problem: dict,
    solution_output: str
) -> Tuple[bool, dict]:
    """
    Validate ZebraLogic grid solution against problem clues.

    The solution is parsed from Z3 code output, which should be a grid
    showing attribute assignments for each house.

    Args:
        problem: Problem dict from zebralogic_grid_100.json
        solution_output: stdout from Z3 code execution

    Returns:
        (is_valid, error_detail)
    """
    # Extract headers and expected structure
    headers = problem.get("headers", [])
    golden_solution = problem.get("golden_solution", {})
    clues = problem.get("problem", "")

    # Parse solution from output
    parsed_grid = parse_zebralogic_output(solution_output, headers)

    if parsed_grid is None:
        return False, {"error": "failed to parse solution grid from output"}

    # Validate grid structure
    num_houses = len(golden_solution.get("rows", []))
    if len(parsed_grid) != num_houses:
        return False, {
            "error": "incorrect number of houses",
            "expected": num_houses,
            "got": len(parsed_grid)
        }

    # Check that all attributes are present and used exactly once
    for attr_idx, attr_name in enumerate(headers[1:], start=1):  # Skip "House" column
        values_in_grid = [row.get(attr_name) for row in parsed_grid if row.get(attr_name)]

        # Check all values are present
        if len(values_in_grid) != num_houses:
            return False, {
                "error": f"attribute '{attr_name}' not assigned to all houses",
                "expected_count": num_houses,
                "got_count": len(values_in_grid)
            }

        # Check distinctness (each value used exactly once)
        if len(set(values_in_grid)) != len(values_in_grid):
            return False, {
                "error": f"attribute '{attr_name}' has duplicate values",
                "values": values_in_grid
            }

    # Optionally: validate against golden solution
    # (This is a strict check - remove if we only want to check constraint satisfaction)
    if golden_solution:
        golden_rows = golden_solution.get("rows", [])
        for idx, (parsed_row, golden_row) in enumerate(zip(parsed_grid, golden_rows)):
            for attr_idx, attr_name in enumerate(headers[1:], start=1):
                parsed_value = normalize_value(parsed_row.get(attr_name, ""))
                golden_value = normalize_value(golden_row[attr_idx])

                if parsed_value != golden_value:
                    return False, {
                        "error": f"mismatch in house {idx+1}, attribute '{attr_name}'",
                        "expected": golden_value,
                        "got": parsed_value
                    }

    return True, {}


def parse_zebralogic_output(output: str, headers: List[str]) -> List[Dict[str, str]]:
    """
    Parse Z3 solution output into structured grid.

    Expected formats:
    - "House 1: Peter, desert, white"
    - "House 1: Name=Peter, Smoothie=desert, Color=white"

    Args:
        output: stdout from Z3 code
        headers: Expected attribute names

    Returns:
        List of dicts, one per house, or None if parsing fails
    """
    if not output or not output.strip():
        return None

    lines = [line.strip() for line in output.strip().split('\n') if line.strip()]

    grid = []

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

        # Extract house number
        try:
            house_num = int(house_str.replace("House", "").strip())
        except ValueError:
            continue

        # Parse attributes (comma-separated)
        # Format 1: "Peter, desert, white"
        # Format 2: "Name=Peter, Smoothie=desert, Color=white"

        attr_values = [v.strip() for v in attrs_str.split(',')]

        row = {"House": str(house_num)}

        # Try to map attributes to headers
        if '=' in attrs_str:
            # Format 2: key=value pairs
            for attr_val in attr_values:
                if '=' in attr_val:
                    key, val = attr_val.split('=', 1)
                    row[key.strip()] = val.strip()
        else:
            # Format 1: positional values (match to headers order)
            for idx, val in enumerate(attr_values):
                if idx + 1 < len(headers):  # headers[0] is "House"
                    row[headers[idx + 1]] = val

        grid.append(row)

    # Sort by house number
    grid.sort(key=lambda r: int(r.get("House", "0")))

    return grid if grid else None


def normalize_value(value: str) -> str:
    """
    Normalize attribute value for comparison.

    Handles case differences, underscores, etc.
    """
    return value.lower().strip().replace('_', ' ').replace('-', ' ')


def check_zebralogic_distinctness(grid: List[Dict[str, str]], headers: List[str]) -> Tuple[bool, dict]:
    """
    Check that each attribute is used exactly once (distinctness constraint).

    Args:
        grid: Parsed solution grid
        headers: Attribute names

    Returns:
        (is_distinct, error_detail)
    """
    for attr_name in headers[1:]:  # Skip "House"
        values = [row.get(attr_name) for row in grid if row.get(attr_name)]

        if len(values) != len(grid):
            return False, {
                "error": f"attribute '{attr_name}' missing in some houses",
                "expected_count": len(grid),
                "got_count": len(values)
            }

        if len(set(values)) != len(values):
            return False, {
                "error": f"attribute '{attr_name}' has duplicates",
                "values": values
            }

    return True, {}
