"""Code extraction utilities for execution stage."""

import re
import json
from typing import Optional, Tuple, List


def split_reasoning_and_code(reasoning_trace: str) -> Tuple[str, Optional[str]]:
    """
    Split reasoning trace into reasoning before code and extracted code.

    Robustly handles:
    - Multiple code blocks (extracts the largest/most complete one)
    - Language tags (python, z3, pddl, or no tag)
    - Malformed backticks (missing closing, extra backticks)
    - Code blocks with inline backticks
    - Nested or escaped backticks
    - Whitespace variations
    - Direct JSON output (for blocksworld/PDDL with assistantfinal marker)

    Args:
        reasoning_trace: Full reasoning trace from model

    Returns:
        Tuple of (reasoning_before_code, extracted_code)
        - reasoning_before_code: Text before first valid code block
        - extracted_code: Code within triple backticks, or None if no code found
    """
    if not reasoning_trace:
        return "", None

    # Special case: Check for direct JSON output (blocksworld/PDDL format)
    # Pattern: assistantfinal{...} or similar markers
    json_code = extract_direct_json(reasoning_trace)
    if json_code:
        # Find where JSON starts to split reasoning
        json_start_marker = find_json_start_marker(reasoning_trace)
        if json_start_marker >= 0:
            reasoning_before_code = reasoning_trace[:json_start_marker].strip()
            return reasoning_before_code, json_code
        else:
            # Fallback: use the whole trace as reasoning
            return reasoning_trace.strip(), json_code

    # Find all potential code blocks
    code_blocks = extract_all_code_blocks(reasoning_trace)

    if not code_blocks:
        return reasoning_trace.strip(), None

    # Prefer code from the final answer over drafts inside the thinking section
    answer_start = find_answer_start(reasoning_trace)
    selected_block = None
    if answer_start >= 0:
        answer_blocks = [b for b in code_blocks if b["start"] >= answer_start]
        selected_block = select_best_code_block(answer_blocks, reasoning_trace)

    # Otherwise select the best code block (first, longest, or most complete)
    if not selected_block:
        selected_block = select_best_code_block(code_blocks, reasoning_trace)

    if not selected_block:
        return reasoning_trace.strip(), None

    # Split at the position of the selected block
    code_start = selected_block["start"]
    reasoning_before_code = reasoning_trace[:code_start].strip()
    extracted_code = selected_block["code"]

    return reasoning_before_code, extracted_code


# Markers that end a model's thinking section and start its final answer
ANSWER_MARKERS = ["</think>", "<|channel|>final<|message|>", "assistantfinal"]


def find_answer_start(text: str) -> int:
    """
    Return the index where the final answer starts (just after the last
    end-of-thinking marker), or -1 if the trace has no such marker.
    """
    best = -1
    for marker in ANSWER_MARKERS:
        idx = text.rfind(marker)
        if idx >= 0:
            best = max(best, idx + len(marker))
    return best


def extract_all_code_blocks(text: str) -> List[dict]:
    """
    Extract all code blocks from text with their positions and metadata.

    Handles:
    - Standard format: ```python\ncode\n```
    - No language: ```\ncode\n```
    - Missing final newline: ```python\ncode```
    - Extra whitespace: ```  python  \n  code  \n  ```
    - Multiple language tags: python, py, z3, pddl, smt, etc.

    Args:
        text: Text potentially containing code blocks

    Returns:
        List of dicts with keys: code, start, end, language, raw_match
    """
    if not text:
        return []

    blocks = []

    # Pattern 1: Standard code block with optional language tag
    # Matches: ```python\ncode\n``` or ```\ncode\n```
    pattern1 = r'```\s*([a-zA-Z0-9_+-]*)\s*\n(.*?)(?:\n```|```)'
    for match in re.finditer(pattern1, text, re.DOTALL):
        language = match.group(1).strip() if match.group(1) else None
        code = match.group(2)
        blocks.append({
            "code": code.strip(),
            "start": match.start(),
            "end": match.end(),
            "language": language,
            "raw_match": match.group(0),
            "pattern": "standard"
        })

    # Pattern 2: Code block without final closing newline
    # Matches: ```python\ncode``` (missing \n before closing)
    pattern2 = r'```\s*([a-zA-Z0-9_+-]*)\s*\n(.*?)```'
    for match in re.finditer(pattern2, text, re.DOTALL):
        # Skip if already captured by pattern1
        if any(b["start"] == match.start() and b["end"] == match.end() for b in blocks):
            continue

        language = match.group(1).strip() if match.group(1) else None
        code = match.group(2)
        blocks.append({
            "code": code.strip(),
            "start": match.start(),
            "end": match.end(),
            "language": language,
            "raw_match": match.group(0),
            "pattern": "no_final_newline"
        })

    # Pattern 3: Malformed - opening backticks but no proper closing
    # Try to salvage code that starts with ``` but doesn't close properly
    if not blocks:
        pattern3 = r'```\s*([a-zA-Z0-9_+-]*)\s*\n(.*?)(?=\n\n|\n#|\Z)'
        for match in re.finditer(pattern3, text, re.DOTALL):
            language = match.group(1).strip() if match.group(1) else None
            code = match.group(2)

            # Only use this as fallback if code looks substantial
            if len(code.strip()) > 10:
                blocks.append({
                    "code": code.strip(),
                    "start": match.start(),
                    "end": match.end(),
                    "language": language,
                    "raw_match": match.group(0),
                    "pattern": "malformed_closing"
                })

    # Pattern 4: Code block with language on same line (rare but possible)
    # Matches: ```python code here``` (all on one line)
    pattern4 = r'```\s*([a-zA-Z0-9_+-]+)\s+(.*?)```'
    for match in re.finditer(pattern4, text):
        # Skip if already captured
        if any(b["start"] == match.start() for b in blocks):
            continue

        language = match.group(1).strip()
        code = match.group(2).strip()

        # Only for short snippets
        if len(code.split('\n')) <= 3:
            blocks.append({
                "code": code,
                "start": match.start(),
                "end": match.end(),
                "language": language,
                "raw_match": match.group(0),
                "pattern": "single_line"
            })

    return blocks


def select_best_code_block(blocks: List[dict], full_text: str = "") -> Optional[dict]:
    """
    Select the most appropriate code block from multiple candidates.

    Selection criteria (in order of priority):
    1. Filter out placeholder/trivial blocks (e.g., "...")
    2. First substantial code block with explicit language tag matching expected languages
    3. Longest substantial code block (by character count)
    4. First substantial code block encountered

    Args:
        blocks: List of code block dicts from extract_all_code_blocks
        full_text: Original text for context

    Returns:
        Selected code block dict or None
    """
    if not blocks:
        return None

    # Filter out placeholder/trivial code blocks
    substantial_blocks = []
    for b in blocks:
        code = b["code"].strip()

        # Skip if too short
        if len(code) < 10:
            continue

        # Skip if it's just ellipsis or placeholder
        if code in ["...", "…", "# ...", "pass", "# TODO", "# Code here"]:
            continue

        # Skip if it's only ellipsis/dots with minimal whitespace
        if re.match(r'^[\.\s…]+$', code):
            continue

        # Skip if contains natural language prose markers (likely incomplete extraction)
        # Check for question marks followed by reasoning/commentary
        prose_markers = [
            r'\?\s*(Actually|Wait|Maybe|But|However|Since|Note|Because)',  # "? Actually" or "? Wait"
            r'\{\.\.\.}',  # {...} placeholder
            r'\[\.\.\.}',  # [...] placeholder with typo
        ]
        if any(re.search(pattern, code, re.IGNORECASE) for pattern in prose_markers):
            continue

        # Check for ellipsis as placeholder in actual code (not comments)
        # Pattern: "..., " or "...)" outside of comments
        # Split by lines and check non-comment parts
        has_ellipsis_placeholder = False
        for line in code.split('\n'):
            # Remove comments
            code_part = line.split('#')[0] if '#' in line else line
            # Check if ellipsis appears in actual code (not just docstrings)
            if re.search(r'\.{3,}\s*[,\)]', code_part):
                has_ellipsis_placeholder = True
                break

        if has_ellipsis_placeholder:
            continue

        # Skip if contains natural language reasoning words in suspicious contexts
        # These patterns indicate prose/reasoning leaked into the code block
        # The word must not be used as code: Meeting programs often name a variable `wait`
        as_code = r'(?!\s*(?:[-+*/%]?=|\(|\[|\.|,|:|\)))'
        reasoning_patterns = [
            r'^\s*maybe\b' + as_code, r'^\s*actually\b' + as_code, r'^\s*wait\b' + as_code,  # Line starts with reasoning
        ]

        # Check for lines starting with reasoning words (non-comment)
        if any(re.search(pattern, code, re.IGNORECASE | re.MULTILINE) for pattern in reasoning_patterns):
            continue

        # Check for excessive reasoning-style comments (multiple instances)
        # A single comment with "let's" or "need to" is fine (normal code comments)
        # But multiple such comments suggest leaked reasoning
        reasoning_comment_patterns = [r'#.*\blet\'s\b', r'#.*\bneed\s+to\b']
        reasoning_comment_count = sum(
            len(re.findall(pattern, code, re.IGNORECASE | re.MULTILINE))
            for pattern in reasoning_comment_patterns
        )

        # Only filter if there are 3+ reasoning-style comments (likely prose)
        if reasoning_comment_count >= 3:
            continue

        substantial_blocks.append(b)

    if not substantial_blocks:
        # If all blocks filtered out, return None (better than returning placeholder)
        return None

    if len(substantial_blocks) == 1:
        return substantial_blocks[0]

    # Priority languages for different tasks
    priority_languages = {
        'python', 'py', 'python3',
        'z3', 'z3-smt', 'smt', 'smt2',
        'pddl', 'lisp'
    }

    # 1. Prefer blocks with priority language tags (and substantial)
    tagged_blocks = [b for b in substantial_blocks if b.get("language") and b["language"].lower() in priority_languages]
    if tagged_blocks:
        # Among tagged blocks, prefer the longest (not first, to avoid placeholders)
        return max(tagged_blocks, key=lambda b: len(b["code"]))

    # 2. Prefer blocks with ANY language tag over no tag
    any_tagged = [b for b in substantial_blocks if b.get("language")]
    if any_tagged:
        return max(any_tagged, key=lambda b: len(b["code"]))

    # 3. Return longest substantial block
    return max(substantial_blocks, key=lambda b: len(b["code"]))


def extract_code_block(text: str, language: Optional[str] = None) -> Optional[str]:
    """
    Extract code from markdown code block with specific language.

    More flexible wrapper around extract_all_code_blocks for language-specific extraction.

    Args:
        text: Text containing code block
        language: Optional language identifier to match (e.g., 'python', 'z3')

    Returns:
        Extracted code or None if no code block found
    """
    if not text:
        return None

    blocks = extract_all_code_blocks(text)

    if not blocks:
        return None

    if language:
        # Find first block matching the language
        language_lower = language.lower()
        for block in blocks:
            if block.get("language") and block["language"].lower() == language_lower:
                return block["code"]

        # Fallback: check if language is a variant (e.g., 'py' for 'python')
        language_variants = {
            'python': ['py', 'python3', 'python2'],
            'z3': ['z3-smt', 'smt', 'smt2'],
            'pddl': ['lisp'],
        }

        for variant in language_variants.get(language_lower, []):
            for block in blocks:
                if block.get("language") and block["language"].lower() == variant:
                    return block["code"]

        # No matching language found
        return None

    # No language specified, return first/best block
    best = select_best_code_block(blocks, text)
    return best["code"] if best else None


def clean_extracted_code(code: str) -> str:
    """
    Clean extracted code by removing common artifacts.

    Handles:
    - Leading/trailing whitespace
    - Extra blank lines at start/end
    - Common markdown artifacts that slip through
    - Inline backticks that aren't code delimiters

    Args:
        code: Extracted code string

    Returns:
        Cleaned code string
    """
    if not code:
        return code

    # Remove leading/trailing whitespace
    code = code.strip()

    # Remove leading/trailing blank lines
    lines = code.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    code = '\n'.join(lines)

    # Remove any stray backticks at start/end (shouldn't happen but just in case)
    code = re.sub(r'^`+', '', code)
    code = re.sub(r'`+$', '', code)

    return code


def validate_code_extraction(code: str, language: Optional[str] = None) -> bool:
    """
    Validate that extracted code looks reasonable.

    Basic sanity checks (not syntax validation):
    - Not empty
    - Has actual content (not just whitespace/comments)
    - For Python: has some recognizable Python constructs
    - For Z3: has some recognizable Z3/SMT constructs

    Args:
        code: Extracted code
        language: Optional language hint

    Returns:
        True if code looks valid, False otherwise
    """
    if not code or not code.strip():
        return False

    # Must have some non-whitespace content
    if len(code.strip()) < 3:
        return False

    # Language-specific basic checks
    if language:
        lang_lower = language.lower()

        if lang_lower in ['python', 'py', 'python3']:
            # Python should have some keywords, operators, or constructs
            python_indicators = [
                r'\bdef\b', r'\bclass\b', r'\bif\b', r'\bfor\b', r'\bwhile\b',
                r'\bimport\b', r'\bfrom\b', r'\breturn\b', r'\bprint\b',
                r'=', r'\(', r'\)', r'\[', r'\]'
            ]
            return any(re.search(pattern, code) for pattern in python_indicators)

        elif lang_lower in ['z3', 'smt', 'smt2']:
            # Z3/SMT should have parentheses and some SMT constructs
            smt_indicators = [
                r'\(', r'\)', r'\bdeclare\b', r'\bassert\b', r'\bcheck-sat\b',
                r'\bget-model\b', r'\bInt\b', r'\bBool\b', r'\bReal\b'
            ]
            return any(re.search(pattern, code, re.IGNORECASE) for pattern in smt_indicators)

        elif lang_lower in ['pddl', 'lisp']:
            # PDDL should have parentheses and some PDDL constructs
            pddl_indicators = [
                r'\(define', r'\(domain', r'\(problem', r'\(:action', r'\(:predicates'
            ]
            return any(re.search(pattern, code, re.IGNORECASE) for pattern in pddl_indicators)

    # Generic check: has at least one line with substantial content
    lines = [line.strip() for line in code.split('\n')]
    substantial_lines = [line for line in lines if len(line) > 5 and not line.startswith('#')]
    return len(substantial_lines) > 0


def extract_direct_json(text: str) -> Optional[str]:
    """
    Extract JSON output directly from text (for blocksworld/PDDL format).

    Some models output JSON directly with markers like 'assistantfinal{...}'
    instead of using code blocks. This function extracts such JSON.

    Args:
        text: Text potentially containing direct JSON output

    Returns:
        Extracted JSON string, or None if not found
    """
    if not text:
        return None

    # Pattern 1: assistantfinal{...} marker (common in blocksworld)
    # Look for this marker followed by JSON
    match = re.search(r'assistantfinal\s*(\{.*\})\s*$', text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        # Validate it's actual JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

    # Pattern 2: Final JSON object in text (no marker)
    # Find the last {...} that looks like JSON
    # Look for balanced braces at the end of text
    json_match = extract_final_json_object(text)
    if json_match:
        return json_match

    return None


def find_json_start_marker(text: str) -> int:
    """
    Find the position where direct JSON output starts.

    Args:
        text: Text containing JSON

    Returns:
        Position of JSON start, or -1 if not found
    """
    # Look for assistantfinal marker
    match = re.search(r'assistantfinal\s*\{', text)
    if match:
        return match.start()

    # Look for final JSON object
    # Find the last opening brace that starts a valid JSON object
    # This is a heuristic - find last { that has matching }
    last_brace = text.rfind('{')
    if last_brace >= 0:
        # Check if there's a matching closing brace
        if text[last_brace:].count('}') >= text[last_brace:].count('{'):
            return last_brace

    return -1


def extract_final_json_object(text: str) -> Optional[str]:
    """
    Extract the final JSON object from text using brace matching.

    Args:
        text: Text potentially ending with JSON object

    Returns:
        JSON string if found and valid, None otherwise
    """
    if not text:
        return None

    # Find all opening braces
    positions = []
    for i, char in enumerate(text):
        if char == '{':
            positions.append(i)

    # Try from last opening brace backwards
    for start_pos in reversed(positions):
        # Extract from this position to end
        candidate = text[start_pos:].strip()

        # Try to parse as JSON
        try:
            json.loads(candidate)
            # Valid JSON found
            return candidate
        except json.JSONDecodeError:
            continue

    return None
