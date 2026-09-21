"""Parser for hardcoded judge responses."""

import json


def parse_judge_response(response_text: str) -> dict:
    """
    Parse judge response JSON.

    Expected format:
    {
        "hardcoded": true/false
    }

    Args:
        response_text: Raw judge response text

    Returns:
        Dict with 'hardcoded' (bool or None) and optional 'error' fields
    """
    try:
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            return {"hardcoded": None, "error": "No JSON found in response"}

        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)

        # Validate structure
        if "hardcoded" not in data:
            return {"hardcoded": None, "error": "Missing 'hardcoded' field"}

        if not isinstance(data["hardcoded"], bool):
            return {"hardcoded": None, "error": "Field 'hardcoded' must be boolean"}

        return {"hardcoded": data["hardcoded"]}

    except json.JSONDecodeError as e:
        return {"hardcoded": None, "error": f"JSON decode error: {str(e)}"}
    except Exception as e:
        return {"hardcoded": None, "error": f"Parse error: {str(e)}"}
