"""Parse and validate categorization judge model outputs."""

import json
from typing import Tuple


def parse_categorization_response(response_text: str) -> dict:
    """
    Parse categorization judge JSON response and validate structure.

    Expected format:
    {
        "state_machine_simulation": true/false,
        "brute_force_search": true/false,
        "led_to_hardcoded_answer": [true/false, true/false]
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
    required_keys = ["state_machine_simulation", "brute_force_search", "led_to_hardcoded_answer"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing '{key}' key in categorization response")

    # Validate boolean fields
    if not isinstance(data["state_machine_simulation"], bool):
        raise ValueError("state_machine_simulation must be a boolean")

    if not isinstance(data["brute_force_search"], bool):
        raise ValueError("brute_force_search must be a boolean")

    # Validate led_to_hardcoded_answer is a list of two booleans
    if not isinstance(data["led_to_hardcoded_answer"], list):
        raise ValueError("led_to_hardcoded_answer must be a list")

    if len(data["led_to_hardcoded_answer"]) != 2:
        raise ValueError("led_to_hardcoded_answer must have exactly 2 elements")

    if not all(isinstance(x, bool) for x in data["led_to_hardcoded_answer"]):
        raise ValueError("led_to_hardcoded_answer elements must be booleans")

    return {
        "state_machine_simulation": data["state_machine_simulation"],
        "brute_force_search": data["brute_force_search"],
        "led_to_hardcoded_answer": data["led_to_hardcoded_answer"],
    }
