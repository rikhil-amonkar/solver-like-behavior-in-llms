"""Parsing utilities for extracting code blocks and output."""

import re
from typing import Optional, Tuple


# Regex patterns for code extraction
FENCED_CODE_PATTERN = re.compile(
    r"```(?:python)?\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE
)


def extract_code_block(reasoning_trace: str) -> str:
    """
    Extract Python code from fenced code block in model output.

    Finds all fenced code blocks and returns the largest one
    (assumption: largest block is the main solution).

    Args:
        reasoning_trace: Full model output text

    Returns:
        Extracted code string, or empty string if no code found
    """
    if not reasoning_trace:
        return ""

    matches = FENCED_CODE_PATTERN.findall(reasoning_trace)

    if not matches:
        return ""

    # Return longest match (most likely the actual solution)
    return max(matches, key=len).strip()


def split_reasoning_and_code(reasoning_trace: str) -> Tuple[str, str]:
    """
    Split model output into reasoning before code and extracted code.

    Args:
        reasoning_trace: Full model output text

    Returns:
        Tuple of (reasoning_before_code, extracted_code)
    """
    if not reasoning_trace:
        return "", ""

    # Find first code block
    match = FENCED_CODE_PATTERN.search(reasoning_trace)

    if not match:
        # No code found, entire trace is reasoning
        return reasoning_trace.strip(), ""

    # Split at code block boundary
    reasoning_before_code = reasoning_trace[:match.start()].strip()
    extracted_code = match.group(1).strip()

    return reasoning_before_code, extracted_code


def parse_code_output(stdout: str) -> Tuple[Optional[any], Optional[str]]:
    """
    Parse stdout from code execution.

    Attempts to parse the last non-empty line as a Python literal.

    Args:
        stdout: Standard output from code execution

    Returns:
        Tuple of (parsed_value, error_message)
        parsed_value is None if parsing failed
    """
    import ast

    if not stdout or not stdout.strip():
        return None, "empty stdout"

    lines = [line for line in stdout.splitlines() if line.strip()]

    if not lines:
        return None, "no non-empty lines in stdout"

    # Try to parse last line as Python literal
    last_line = lines[-1].strip()

    try:
        parsed = ast.literal_eval(last_line)
        return parsed, None
    except (ValueError, SyntaxError) as e:
        return None, f"parse failed: {str(e)}"
