# Prompt Architecture for Multi-Language CSP Tasks

## Overview

The prompting system uses a **two-part modular design**:
1. **Universal CSP Prefix** (language-specific)
2. **Task-Specific Output Format** (task + language pairing)

This separation allows clean extension to new tasks and languages without duplication.

---

## Universal CSP Prefixes

These set the overall framing and language constraints. Choose based on the target language:

### 1. Python Standard Library (`universal_csp_prefix_python.txt`)
**Use for:** Calendar Scheduling, Meeting Planning, Trip Planning

**Key Points:**
- Restricts to Python standard library only
- No external packages allowed
- Direct constraint solving in Python

**Tasks using this:**
- `calendar_scheduling`
- `meeting_planning`
- `trip_planning`

---

### 2. Z3-Python (`universal_csp_prefix_z3.txt`)
**Use for:** Logic grid puzzles, symbolic constraint problems

**Key Points:**
- Allows `from z3 import *`
- Enables SMT solver capabilities
- Still Python syntax, but with Z3 primitives

**Tasks using this:**
- `zebralogic_grid`

---

### 3. PDDL (`universal_csp_prefix_pddl.txt`)
**Use for:** Planning problems with sequential actions

**Key Points:**
- NOT Python - uses PDDL (Lisp-like) syntax
- Defines domain (actions) + problem (states)
- Requires external PDDL planner to execute

**Tasks using this:**
- `blocksworld`

---

## Task-Specific Output Formats

These specify the exact output structure and domain-specific requirements.

### Python Standard Library Tasks

#### `calendar_output_format.txt`
**Output:** `['Monday', '13:30', '14:00']`
- Python list of 3 strings
- Day (full weekday name), start time (HH:MM), end time (HH:MM)
- Zero-padded 24-hour format

#### `meeting_output_format.txt`
**Output:** Itinerary list of meeting steps
- Python list of event dictionaries
- Includes locations, times, travel

---

### Z3-Python Tasks

#### `zebralogic_output_format.txt`
**Output:** Grid table showing attribute assignments
```
House 1: Peter, desert, white
House 2: Alice, cherry, green
House 3: Arnold, watermelon, yellow
House 4: Eric, dragonfruit, red
```

**Code Requirements:**
- Import: `from z3 import *`
- Declare Z3 variables (Int, Bool, or custom sorts)
- Add distinctness constraints
- Encode clue constraints
- Solve with `solver.check()` and `solver.model()`
- Print formatted grid

**Evaluation:**
- Check that solution satisfies all clues
- Verify distinctness (each attribute used exactly once)
- Validate grid completeness

---

### PDDL Tasks

#### `blocksworld_output_format.txt`
**Output:** PDDL domain + problem definitions
```lisp
(define (domain blocksworld)
  (:requirements :strips)
  (:predicates ...)
  (:action pickup ...)
  (:action putdown ...)
  (:action stack ...)
  (:action unstack ...)
)

(define (problem blocksworld-problemX)
  (:domain blocksworld)
  (:objects block1 block2 ...)
  (:init ...)
  (:goal ...)
)
```

**Code Requirements:**
- Valid PDDL syntax (s-expressions)
- Define all 4 standard actions (unless constraints require modification)
- Encode additional constraints via predicates/preconditions
- Mark constraint modifications with comments

**Evaluation:**
- Parse domain and problem PDDL
- Run external planner (Fast Downward, Metric-FF, etc.)
- Check if plan achieves goal from init state
- Validate constraint satisfaction

---

## Dataset Formats

### ZebraLogic (`data/problems/zebralogic_grid_100.json`)

**Structure:**
```json
{
  "zebralogic_grid_lgp-test-4x3-25": {
    "problem": "There are 4 houses... [natural language clues]",
    "golden_solution": {
      "header": ["House", "Name", "Smoothie", "Color"],
      "rows": [
        ["1", "Peter", "desert", "white"],
        ["2", "Alice", "cherry", "green"],
        ...
      ]
    },
    "headers": ["House", "Name", "Smoothie", "Color"],
    "id": "lgp-test-4x3-25",
    "size": "4*3"
  }
}
```

**Key Fields:**
- `problem`: Natural language puzzle description with clues
- `golden_solution`: Reference solution as table
- `headers`: Attribute categories
- `size`: Grid dimensions (houses × attributes)

---

### BlocksWorld (`data/problems/blocksworld_100.json`)

**Structure:**
```json
{
  "blocksworld_p86_initial_constraint6": {
    "problem": "Blocksworld is a puzzle... [natural language description]",
    "golden_solution": {
      "domain_pddl": "(define (domain blocksworld) ...)",
      "problem_pddl": "(define (problem blocksworld-p86) ...)"
    },
    "action_heads": "(pickup block)\n(putdown block)\n...",
    "plan_exists": true,
    "domain": "blocksworld",
    "problem_id": "p86"
  }
}
```

**Key Fields:**
- `problem`: Natural language description of initial/goal states + constraints
- `golden_solution.domain_pddl`: Reference domain definition
- `golden_solution.problem_pddl`: Reference problem definition
- `action_heads`: Available action signatures
- `plan_exists`: Whether a valid plan exists

**Constraint Types:**
- **Initial constraints**: Modify starting state (e.g., "start holding block2")
- **Action constraints**: Modify action preconditions/effects (e.g., "block1 is fragile")
- **State constraints**: Limit intermediate states (e.g., "max 3 stacks at once")

---

## Prompt Construction

### How prompts are built at runtime:

```python
full_prompt = f"{universal_prefix}\n\n{problem_text}\n\n{output_format}"
```

**Example for Calendar Scheduling:**
```
universal_csp_prefix_python.txt  (generic Python CSP framing)
+ problem text from calendar_scheduling_100.json
+ calendar_output_format.txt  (specific output requirements)
```

**Example for ZebraLogic:**
```
universal_csp_prefix_z3.txt  (Z3-specific CSP framing)
+ problem text from zebralogic_grid_100.json
+ zebralogic_output_format.txt  (Z3 grid output requirements)
```

**Example for BlocksWorld:**
```
universal_csp_prefix_pddl.txt  (PDDL-specific CSP framing)
+ problem text from blocksworld_100.json
+ blocksworld_output_format.txt  (PDDL format requirements)
```

---

## Adding New Tasks

### To add a new Python standard library task:
1. Create problem dataset: `data/problems/newtask_100.json`
2. Create output format: `prompts/newtask_output_format.txt`
3. Use existing: `prompts/universal_csp_prefix_python.txt`
4. Implement evaluator: `src/evaluation/newtask_eval.py`

### To add a new Z3 task:
1. Create problem dataset with logic clues
2. Create output format specifying Z3 variable structure
3. Use existing: `prompts/universal_csp_prefix_z3.txt`
4. Implement evaluator that checks constraint satisfaction

### To add a new PDDL task:
1. Create problem dataset with initial/goal states
2. Create output format specifying PDDL structure
3. Use existing: `prompts/universal_csp_prefix_pddl.txt`
4. Implement evaluator with PDDL planner integration

---

## Language-Specific Execution

### Python Standard Library
```python
# src/inference/code_executor.py
subprocess.run(['python', code_file], capture_output=True)
```

### Z3-Python
```python
# Requires z3-solver package
# pip install z3-solver
subprocess.run(['python', code_file], capture_output=True)
```

### PDDL
```python
# Different approach - extract and validate PDDL
# 1. Parse code to extract domain and problem PDDL
# 2. Write to .pddl files
# 3. Call external planner: fast-downward, metric-ff, etc.
# 4. Parse and return plan
```

---

## Current Status

### Fully Implemented:
- ✅ Python Standard Library (Calendar, Meeting)
- ✅ Prompts created for Z3 and PDDL

### Needs Implementation:
- ⚠️ Z3 code executor (allow z3 import)
- ⚠️ Z3 evaluator for ZebraLogic
- ⚠️ PDDL parser/extractor
- ⚠️ PDDL planner integration
- ⚠️ PDDL evaluator for BlocksWorld

---

## Design Rationale

**Why separate universal prefix from output format?**
- Reuse common CSP framing across tasks
- Easy to add new tasks (just create output format file)
- Language-specific prefixes handle different constraint languages

**Why language-specific universal prefixes?**
- Python, Z3, and PDDL have fundamentally different syntax
- Allows clear specification of allowed libraries/imports
- Maintains consistent CSP problem-solving philosophy

**Why task-specific output formats?**
- Each task has unique output structure
- Evaluation depends on output format
- Provides clear examples to models

This architecture balances **reusability** (universal prefixes) with **specificity** (output formats), making it easy to extend to new tasks and languages.
