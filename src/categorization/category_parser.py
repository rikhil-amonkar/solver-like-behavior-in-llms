"""Parse and validate categorization judge model outputs."""

import json


def parse_categorization_response(response_text: str) -> dict:
    """
    Parse categorization judge JSON response and validate structure.

    Expected format:
    {
        "state_machine_simulation": true/false,
        "brute_force_search": true/false
    }

    Args:
        response_text: Raw JSON response from categorization judge

    Returns:
        Parsed dict with categorization fields

    Raises:
        ValueError: If response is invalid
    """
    if not response_text or not response_text.strip():
        raise ValueError("Empty categorization judge response")

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from categorization judge: {str(e)}")

    # Validate required keys
    required_keys = ["state_machine_simulation", "brute_force_search"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing '{key}' key in categorization response")

    # Validate boolean fields
    if not isinstance(data["state_machine_simulation"], bool):
        raise ValueError("state_machine_simulation must be a boolean")

    if not isinstance(data["brute_force_search"], bool):
        raise ValueError("brute_force_search must be a boolean")

    return {
        "state_machine_simulation": data["state_machine_simulation"],
        "brute_force_search": data["brute_force_search"],
    }
