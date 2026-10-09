# Robust Code Extraction

## Overview

The execution stage uses a highly robust code extraction system that can handle various markdown code block formats, malformed blocks, and edge cases commonly produced by LLM reasoning traces.

## Features

### Multi-Pattern Matching

The extractor uses **4 different regex patterns** to catch code blocks:

1. **Standard format**: `` ```python\ncode\n``` ``
2. **No final newline**: `` ```python\ncode``` ``
3. **Malformed closing**: `` ```python\ncode`` (missing closing backticks)
4. **Single line**: `` ```python code``` ``

### Language Tag Support

Recognizes and prioritizes code blocks with explicit language tags:

**Python variants:**
- `python`, `py`, `python3`, `python2`

**Z3/SMT variants:**
- `z3`, `z3-smt`, `smt`, `smt2`

**PDDL variants:**
- `pddl`, `lisp`

### Intelligent Block Selection

When multiple code blocks are found, the system selects the best one using:

1. **Priority languages**: Blocks with recognized language tags (python, z3, pddl)
2. **Any language tag**: Blocks with any tag over no tag
3. **Longest code**: Significantly longer blocks are preferred
4. **First block**: Default to first encountered

### Code Cleaning

Automatically cleans extracted code:
- Removes leading/trailing whitespace
- Removes blank lines at start/end
- Strips any stray backticks
- Preserves internal formatting

### Code Validation

Basic sanity checks (not syntax validation):

**Python:**
- Must contain keywords: `def`, `class`, `if`, `for`, `while`, `import`, `return`, `print`
- Or common operators: `=`, `(`, `)`, `[`, `]`

**Z3/SMT:**
- Must contain: `(`, `)`, `declare`, `assert`, `check-sat`, `get-model`
- Or type keywords: `Int`, `Bool`, `Real`

**PDDL:**
- Must contain: `(define`, `(domain`, `(problem`, `(:action`, `(:predicates`

## Usage

### Basic Extraction

```python
from execution.code_extractor import split_reasoning_and_code

reasoning_trace = """
Let me solve this problem.

```python
def solve():
    return [1, 2, 3]
print(solve())
```

That's my solution.
"""

reasoning_before_code, extracted_code = split_reasoning_and_code(reasoning_trace)
```

### Language-Specific Extraction

```python
from execution.code_extractor import extract_code_block

# Extract only Python code
code = extract_code_block(text, language="python")

# Extract Z3 code
code = extract_code_block(text, language="z3")
```

### With Cleaning and Validation

```python
from execution.code_extractor import (
    split_reasoning_and_code,
    clean_extracted_code,
    validate_code_extraction
)

reasoning, code = split_reasoning_and_code(trace)

if code:
    # Clean the code
    code = clean_extracted_code(code)

    # Validate it looks reasonable
    if validate_code_extraction(code, "python"):
        print("Code looks valid!")
```

## Examples

### Example 1: Standard Python

**Input:**
```
Here's my solution:

```python
from datetime import datetime

def solve():
    return datetime.now()
```

This works because...
```

**Output:**
- `reasoning_before_code`: `"Here's my solution:"`
- `extracted_code`: `"from datetime import datetime\n\ndef solve():\n    return datetime.now()"`

### Example 2: Multiple Blocks

**Input:**
```
First attempt (wrong):

```python
# This doesn't work
pass
```

Correct solution:

```python
def correct_solve():
    return "answer"
```
```

**Output:**
- Extracts the **first** block (prioritizing first encounter)
- `extracted_code`: `"# This doesn't work\npass"`

### Example 3: No Language Tag

**Input:**
```
Solution:

```
x = 5
y = 10
print(x + y)
```
```

**Output:**
- Successfully extracts code even without language tag
- `extracted_code`: `"x = 5\ny = 10\nprint(x + y)"`

### Example 4: Malformed Closing

**Input:**
```
Here's the code:

```python
def solve():
    return 42
```

**Output:**
- Detects malformed closing and salvages code
- `extracted_code`: `"def solve():\n    return 42"`

### Example 5: Z3 Code

**Input:**
```
Z3 formalization:

```z3
(declare-const x Int)
(assert (> x 0))
(check-sat)
(get-model)
```
```

**Output:**
- Recognizes Z3 language tag
- `extracted_code`: `"(declare-const x Int)\n(assert (> x 0))\n(check-sat)\n(get-model)"`
- Validation passes for Z3 constructs

## Edge Cases Handled

✅ **Inline backticks**: Ignores single backticks like `datetime` in text
✅ **Extra whitespace**: Handles `  ```  python  \n  code  \n  ```  `
✅ **Missing final newline**: Extracts from `` ```python\ncode``` `` (no `\n` before closing)
✅ **No closing backticks**: Attempts salvage with fallback patterns
✅ **Empty code blocks**: Returns `None` for `` ```\n\n``` ``
✅ **Code with backticks**: Handles code containing `` ` `` characters
✅ **Multiple languages**: Selects by priority (python > z3 > other)

## Implementation Details

### File: `src/execution/code_extractor.py`

**Main functions:**

1. `split_reasoning_and_code(reasoning_trace)` - Primary entry point
2. `extract_all_code_blocks(text)` - Finds all possible code blocks
3. `select_best_code_block(blocks)` - Chooses the best block
4. `extract_code_block(text, language)` - Language-specific extraction
5. `clean_extracted_code(code)` - Cleans extracted code
6. `validate_code_extraction(code, language)` - Basic validation

### Integration

Used by `src/run_execution.py`:

```python
# Split reasoning and extract code
reasoning_before_code, extracted_code = split_reasoning_and_code(
    reasoning_trace
)

# Clean and validate
if extracted_code:
    extracted_code = clean_extracted_code(extracted_code)

    if not validate_code_extraction(extracted_code, language):
        print(f"⚠ Warning: Extracted code may be malformed")
```

## Testing

Comprehensive tests cover:

- Standard code blocks with various languages
- Multiple code blocks in one trace
- Malformed backticks
- Missing closing markers
- Extra whitespace
- Inline vs block backticks
- Language tag variations
- Empty/invalid blocks

Run tests:
```bash
python -m pytest tests/test_code_extractor.py
```

## Design Principles

1. **Fail gracefully**: Return `None` rather than crash
2. **Be permissive**: Try to extract something useful even from malformed input
3. **Prioritize correctness**: Prefer tagged, complete blocks
4. **Don't validate syntax**: Just check if it looks like code
5. **Clean automatically**: Users get clean code without extra steps

## Future Enhancements

Potential improvements:

- [ ] Handle code blocks with different quote styles (`'''`, `"""`)
- [ ] Support for language aliases (e.g., `py3` → `python3`)
- [ ] Heuristic scoring for ambiguous cases
- [ ] Extract code from plain text (no backticks) as last resort
- [ ] Language detection from code content (AST parsing)
