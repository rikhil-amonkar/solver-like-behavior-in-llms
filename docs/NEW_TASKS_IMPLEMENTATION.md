# New Tasks Implementation Guide

## Overview

The pipeline now supports **four task types** across **three programming languages**:

| Task | Language | Solver | Status |
|------|----------|--------|--------|
| Calendar Scheduling | Python stdlib | Direct solving | ✅ Fully implemented |
| Meeting Planning | Python stdlib | Direct solving | ✅ Fully implemented |
| ZebraLogic Grid | Z3-Python | SMT solver | ✅ Implemented |
| BlocksWorld | PDDL | Planning | ✅ Implemented |

---

## Architecture

### Modular Design

```
Task → Language → Executor → Evaluator
```

**1. Task Configuration** (`src/general/prompt_utils.py`):
```python
task_config = {
    "calendar": ("python", "calendar_output_format.txt"),
    "meeting": ("python", "meeting_output_format.txt"),
    "zebralogic": ("z3", "zebralogic_output_format.txt"),
    "blocksworld": ("pddl", "blocksworld_output_format.txt"),
}
```

**2. Language Routing** (`src/inference/code_executor.py`):
```python
def get_language_from_task(task: str) -> str:
    return task_to_language.get(task, "python")

def execute_code_by_language(code, language, **kwargs):
    if language == "python":
        return run_code(code)
    elif language == "z3":
        return run_z3_code(code)
    elif language == "pddl":
        return run_pddl_code(code, planner_path=kwargs.get("planner_path"))
```

**3. Task-Specific Evaluation** (`src/run_evaluation.py`):
```python
def evaluate_solution(task, constraints, solution):
    if task == "calendar":
        return evaluate_calendar_solution(constraints, solution)
    elif task == "zebralogic":
        return evaluate_zebralogic_solution(constraints, solution)
    # ... etc
```

---

## File Structure

### New Files Created

```
src/
├── inference/
│   ├── code_executor_z3.py          # Z3-Python execution
│   └── code_executor_pddl.py        # PDDL extraction/validation
├── evaluation/
│   ├── zebralogic_eval.py           # Z3 grid validation
│   └── blocksworld_eval.py          # PDDL plan validation
└── general/
    └── prompt_utils.py              # Updated task mappings

prompts/
├── universal_csp_prefix_python.txt  # Python stdlib prompting
├── universal_csp_prefix_z3.txt      # Z3-Python prompting
├── universal_csp_prefix_pddl.txt    # PDDL prompting
├── zebralogic_output_format.txt     # Z3 grid output spec
└── blocksworld_output_format.txt    # PDDL structure spec
```

### Modified Files

```
requirements.txt                      # Added z3-solver, PDDL notes
src/inference/code_executor.py        # Added routing logic
src/run_inference.py                  # Added zebralogic, blocksworld
src/run_evaluation.py                 # Added new evaluators
```

---

## Usage

### 1. ZebraLogic (Z3-Python)

**Run Inference:**
```bash
python src/run_inference.py \
  --task zebralogic \
  --model deepseek \
  --n 10
```

**What Happens:**
1. Loads problem from `data/problems/zebralogic_grid_100.json`
2. Builds prompt: `universal_csp_prefix_z3.txt` + problem + `zebralogic_output_format.txt`
3. Model generates Z3-Python code with `from z3 import *`
4. Executes code via `run_z3_code()` (allows z3 imports)
5. Captures stdout (grid table)
6. Saves to `output/deepseek/zebralogic/inference.json`

**Run Evaluation:**
```bash
python src/run_evaluation.py \
  --input output/deepseek/zebralogic/inference.json
```

**What Happens:**
1. Parses Z3 grid from stdout
2. Validates distinctness (each attribute used exactly once)
3. Checks against golden solution
4. Saves to `output/deepseek/zebralogic/evaluation.json`

---

### 2. BlocksWorld (PDDL)

**Run Inference:**
```bash
python src/run_inference.py \
  --task blocksworld \
  --model gpt \
  --n 5
```

**What Happens:**
1. Loads problem from `data/problems/blocksworld_100.json`
2. Builds prompt: `universal_csp_prefix_pddl.txt` + problem + `blocksworld_output_format.txt`
3. Model generates PDDL domain + problem definitions
4. Executes via `run_pddl_code()`:
   - Extracts domain and problem PDDL
   - Validates syntax (balanced parens, required sections)
   - Optionally runs planner (if configured)
5. Saves to `output/gpt/blocksworld/inference.json`

**Run Evaluation:**
```bash
python src/run_evaluation.py \
  --input output/gpt/blocksworld/inference.json
```

**What Happens:**
1. Checks PDDL syntax validity
2. Verifies required actions (pickup, putdown, stack, unstack)
3. Validates constraint encoding (comments, predicates)
4. Optionally checks plan validity
5. Saves to `output/gpt/blocksworld/evaluation.json`

---

## Implementation Details

### Z3-Python Execution (`code_executor_z3.py`)

**Key Features:**
- Allows `from z3 import *` and `import z3`
- Detects z3 usage automatically
- Enhanced error messages for missing z3-solver
- Parses grid table output from stdout

**Example Output:**
```
House 1: Peter, desert, white
House 2: Alice, cherry, green
House 3: Arnold, watermelon, yellow
House 4: Eric, dragonfruit, red
```

---

### PDDL Execution (`code_executor_pddl.py`)

**Key Features:**
- Extracts domain and problem from code blocks or raw S-expressions
- Validates PDDL syntax:
  - Balanced parentheses
  - Required sections (`:predicates`, `:action`, `:init`, `:goal`)
  - Domain-problem consistency
- Optional planner integration (requires external binary)

**PDDL Structure:**
```lisp
(define (domain blocksworld)
  (:requirements :strips)
  (:predicates (on ?x ?y) (clear ?x) ...)
  (:action pickup ...)
  (:action putdown ...)
  (:action stack ...)
  (:action unstack ...)
)

(define (problem blocksworld-p1)
  (:domain blocksworld)
  (:objects block1 block2 block3)
  (:init (on-table block1) ...)
  (:goal (on block2 block1))
)
```

---

### ZebraLogic Evaluation (`zebralogic_eval.py`)

**Validation Steps:**
1. **Parse grid** from stdout (handles formats with/without attribute names)
2. **Check structure**: Correct number of houses
3. **Validate distinctness**: Each attribute used exactly once
4. **Compare to golden**: Exact match to reference solution

**Supported Output Formats:**
- `House 1: Peter, desert, white` (positional)
- `House 1: Name=Peter, Smoothie=desert, Color=white` (key-value)

---

### BlocksWorld Evaluation (`blocksworld_eval.py`)

**Validation Steps:**
1. **Syntax check**: Domain and problem extracted and valid
2. **Action check**: All required actions defined
3. **Structure check**: Required sections present
4. **Constraint check**: Additional constraints properly encoded (via comments)
5. **Plan check** (optional): Plan exists and uses defined actions

**Constraint Encoding Examples:**
```pddl
;; CONSTRAINT Block 1 is fragile
(:predicates
  (fragile ?x)
  ...
)

;; BEGIN ADD
(fragile block1)
;; END ADD
```

---

## Dependencies

### Required

```bash
pip install z3-solver>=4.13.0
```

### Optional (PDDL Planning)

**Option 1: Fast Downward** (recommended, faster):
```bash
# Install separately from https://www.fast-downward.org/
```

**Option 2: Pyperplan** (pure Python, slower):
```bash
pip install pyperplan>=2.1
```

---

## Data Formats

### ZebraLogic Input (`zebralogic_grid_100.json`)

```json
{
  "zebralogic_grid_lgp-test-4x3-25": {
    "problem": "There are 4 houses... [clues]",
    "golden_solution": {
      "header": ["House", "Name", "Smoothie", "Color"],
      "rows": [
        ["1", "Peter", "desert", "white"],
        ["2", "Alice", "cherry", "green"],
        ...
      ]
    },
    "headers": ["House", "Name", "Smoothie", "Color"],
    "size": "4*3"
  }
}
```

### BlocksWorld Input (`blocksworld_100.json`)

```json
{
  "blocksworld_p86_initial_constraint6": {
    "problem": "Blocksworld puzzle... [description]
                Additional constraint: You start by holding block2.",
    "golden_solution": {
      "domain_pddl": "(define (domain blocksworld) ...)",
      "problem_pddl": "(define (problem blocksworld-p86) ...)"
    },
    "action_heads": "(pickup block)\n(putdown block)...",
    "plan_exists": true
  }
}
```

---

## Testing

### Verify Z3 Installation

```bash
python -c "from z3 import *; print('Z3 OK')"
```

### Test Z3 Executor

```python
from inference.code_executor_z3 import run_z3_code

code = '''
from z3 import *

solver = Solver()
x = Int('x')
solver.add(x > 0, x < 10)

if solver.check() == sat:
    print(f"Solution: x = {solver.model()[x]}")
'''

result = run_z3_code(code)
print(result["stdout"])  # Should print "Solution: x = ..."
```

### Test PDDL Extractor

```python
from inference.code_executor_pddl import run_pddl_code

pddl = '''
(define (domain test)
  (:predicates (p ?x))
  (:action act :parameters () :precondition () :effect ())
)
(define (problem test-p1)
  (:domain test)
  (:objects a b)
  (:init (p a))
  (:goal (p b))
)
'''

result = run_pddl_code(pddl)
print(f"Syntax valid: {result['syntax_valid']}")
print(f"Domain extracted: {bool(result['domain_pddl'])}")
```

---

## Extending to New Tasks

### Adding a New Python Task

1. **Create output format**: `prompts/formats/newtask_output_format.txt`
2. **Update task config** in `src/general/prompt_utils.py`:
   ```python
   task_config = {
       ...
       "newtask": ("python", "prompts/formats/newtask_output_format.txt"),
   }
   ```
3. **Create evaluator**: `src/evaluation/newtask_eval.py`
4. **Register evaluator** in `src/run_evaluation.py`
5. **Add task to choices** in `src/run_inference.py` and `run_evaluation.py`

### Adding a New Z3 Task

Same as above, but use `"z3"` language and create Z3-specific output format

### Adding a New PDDL Task

Same as above, but use `"pddl"` language and create PDDL-specific output format

---

## Common Issues

### "ModuleNotFoundError: No module named 'z3'"

```bash
pip install z3-solver
```

### "Planner not found" (BlocksWorld)

PDDL planning requires an external planner. Either:
1. Install pyperplan: `pip install pyperplan`
2. Install Fast Downward and configure path
3. Skip planner execution (validation only)

### Evaluation fails with "unknown task"

Ensure task is registered in `evaluate_solution()` dispatch function in `run_evaluation.py`

---

## Design Principles

✅ **Modular**: Each language has its own executor
✅ **Extensible**: Adding new tasks requires minimal changes
✅ **DRY**: Common logic in base executor, language-specific in submodules
✅ **Fail-safe**: Invalid code doesn't crash pipeline
✅ **Documented**: Clear separation of concerns

---

## Summary

| Component | Python | Z3 | PDDL |
|-----------|--------|-----|------|
| **Executor** | `run_code()` | `run_z3_code()` | `run_pddl_code()` |
| **Import restrictions** | stdlib only | `from z3 import *` | N/A (Lisp syntax) |
| **Output format** | List/Dict | Grid table | Domain + Problem |
| **Validation** | Task-specific | Grid distinctness | Syntax + Actions |
| **Example task** | Calendar | ZebraLogic | BlocksWorld |

The architecture is designed to be **clean, modular, and easy to extend** while maintaining backward compatibility with existing tasks.
