"""Parsing utilities for extracting code blocks and output."""

import ast
import re
from typing import Optional, Tuple, List


# Regex patterns for code extraction
# Matches: ```python\n CODE \n``` OR ```python\n CODE```
# (closing ``` may or may not have newline before it)
FENCED_CODE_PATTERN = re.compile(
    r"```(?:python)?\s*\n(.*?)(?:\n)?```",
    re.DOTALL | re.IGNORECASE
)


def looks_like_code(code: str) -> bool:
    """
    Check if a string looks like intended Python code (even if syntactically invalid).

    Uses heuristics to distinguish actual code from prose wrapped in code blocks.
    Does NOT require valid syntax - we want to extract buggy code too!

    Heuristics for "looks like code":
    - Contains Python keywords/patterns (def, class, import, for, if, etc.)
    - Contains assignments (=)
    - Contains function calls with ()
    - Has code-like structure (indentation, colons, brackets)
    - NOT just prose sentences

    Args:
        code: String to validate

    Returns:
        True if this looks like intended code (even if buggy), False if prose
    """
    if not code or not code.strip():
        return False

    stripped = code.strip()

    # Filter out trivial placeholders
    if stripped in ('...', 'pass', 'None'):
        return False

    # Filter out extremely short snippets (< 50 chars, unlikely to be solutions)
    if len(stripped) < 50:
        return False

    lines = stripped.split('\n')

    # Count lines with code-like patterns
    code_indicators = 0
    prose_indicators = 0
    has_print_statement = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            continue

        # Strong code indicators
        if any(line_stripped.startswith(kw) for kw in ['def ', 'class ', 'import ', 'from ', 'return ', 'yield ']):
            code_indicators += 3
        if any(kw in line_stripped for kw in ['for ', 'while ', 'if ', 'elif ', 'else:', 'try:', 'except', 'with ']):
            code_indicators += 2
        if '=' in line_stripped and not line_stripped.startswith('='):  # Assignment
            code_indicators += 2
        if line_stripped.startswith('print(') or ' print(' in line_stripped:  # Print statement (strong indicator of solution)
            code_indicators += 3
            has_print_statement = True
        elif '(' in line_stripped and ')' in line_stripped:  # Function call/def
            code_indicators += 1
        if line_stripped.endswith(':'):  # Block start
            code_indicators += 1
        if line.startswith('    ') or line.startswith('\t'):  # Indented
            code_indicators += 1
        if any(c in line_stripped for c in ['{', '}', '[', ']']):  # Brackets
            code_indicators += 1

        # Prose indicators
        if line_stripped.endswith('.') and len(line_stripped.split()) > 5:  # Sentence
            # Don't count as prose if it looks like travel/location data (e.g., "A to B: 15.")
            # or other structured data patterns common in CSP problems
            if not re.match(r'.+ to .+: \d+\.?$', line_stripped):
                prose_indicators += 2
        if line_stripped.startswith(('Need ', 'Let', 'We ', 'This ', 'Could ', 'Should ', 'The ', 'But ', 'If ')):
            prose_indicators += 2
        if ' maybe ' in line_stripped or ' perhaps ' in line_stripped:
            prose_indicators += 1

    # Lowered threshold from 10 to 4-6 to catch simple solutions
    # If has print statement (common in CSP solutions), use lower threshold
    threshold = 4 if has_print_statement else 6
    return code_indicators >= threshold and code_indicators > prose_indicators * 2


def extract_code_block(reasoning_trace: str) -> str:
    """
    Extract Python code from fenced code block in model output.

    Finds all fenced code blocks, uses heuristics to identify actual code
    (vs prose), and returns the largest code-like block.

    Does NOT require syntactically valid code - extracts buggy code too!

    Args:
        reasoning_trace: Full model output text

    Returns:
        Extracted code string, or empty string if no code-like blocks found
    """
    if not reasoning_trace:
        return ""

    matches = FENCED_CODE_PATTERN.findall(reasoning_trace)

    if not matches:
        return ""

    # Filter to only code-like blocks (not prose in code fences)
    code_blocks = [code.strip() for code in matches if looks_like_code(code.strip())]

    if not code_blocks:
        return ""

    # Return longest code-like block (most likely the actual solution)
    return max(code_blocks, key=len)


def split_reasoning_and_code(reasoning_trace: str) -> Tuple[str, str]:
    """
    Split model output into reasoning before code and extracted code.

    Extracts the LARGEST code-like block (using heuristics, not syntax validation).
    This avoids grabbing:
    - Small code snippets mentioned in reasoning
    - Prose/reasoning text mistakenly wrapped in code blocks

    But DOES extract buggy/invalid code if it looks like intended solution code.

    Args:
        reasoning_trace: Full model output text

    Returns:
        Tuple of (reasoning_before_code, extracted_code)
    """
    if not reasoning_trace:
        return "", ""

    # Find all code blocks
    matches = list(FENCED_CODE_PATTERN.finditer(reasoning_trace))

    if not matches:
        # No code found, entire trace is reasoning
        return reasoning_trace.strip(), ""

    # Filter to only code-like blocks (not prose)
    code_matches = [
        match for match in matches
        if looks_like_code(match.group(1).strip())
    ]

    if not code_matches:
        # No code-like blocks found
        return reasoning_trace.strip(), ""

    # Find the LARGEST code-like block (most likely the actual solution)
    largest_match = max(code_matches, key=lambda m: len(m.group(1)))

    # Split at the largest code block boundary
    reasoning_before_code = reasoning_trace[:largest_match.start()].strip()
    extracted_code = largest_match.group(1).strip()

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


def parse_zebralogic_grid_output(stdout: str, headers: List[str]) -> Tuple[Optional[dict], Optional[str]]:
    """
    Parse zebralogic grid output from Z3 code.

    Expected format:
        House 1: Peter, desert, white
        House 2: Alice, cherry, green
        ...

    Args:
        stdout: Standard output from Z3 code execution
        headers: Expected headers like ["House", "Name", "Smoothie", "Color"]

    Returns:
        Tuple of (parsed_solution, error_message)
        parsed_solution is dict with {"header": [...], "rows": [[...]]} or None if parsing failed
    """
    if not stdout or not stdout.strip():
        return None, "empty stdout"

    lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]

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
            house_num = house_str.replace("House", "").strip()
        except ValueError:
            continue

        # Parse attributes (comma-separated values)
        attr_values = [v.strip() for v in attrs_str.split(',') if v.strip()]

        # Build row: [house_num, value1, value2, ...]
        row = [house_num] + attr_values
        rows.append(row)

    if not rows:
        return None, "no house rows found in output"

    # Sort by house number
    rows.sort(key=lambda r: int(r[0]) if r[0].isdigit() else 0)

    # Return in golden solution format
    solution = {
        "header": headers,
        "rows": rows
    }

    return solution, None
