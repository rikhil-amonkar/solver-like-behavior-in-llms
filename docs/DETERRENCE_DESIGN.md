# Deterring SLB: batched problems and placeholders (paper §6, second method)

Cautionary prompts (§6) lower the solver-like ratio by about 0.05. Two methods that looked
effective in Harry's preliminary experiments are tested here, as candidate deterrents that must
not cost accuracy ("whatever works works").

## Decisions (Harry, 2026-10-31)
- Batching returns **K separate programs**, not one program parametrized over problems.
- Placeholders: the model **never sees the values**; the program gets them at run time.
- Models: Qwen and GPT-OSS (no DeepSeek: its API model drifted, see CROSS_FL_DESIGN.md).
- K sweep {2, 5, 10}; K = 5 is the main setting.
- BlocksWorld in PDDL is dropped: it has little SLB to deter (ratio 0.04, 51% of traces with
  values; Python > Z3 and Python > PDDL on the same problems, H2). BlocksWorld stays in via Python.
  Batching therefore covers 7 cells (Calendar, Meeting, ZebraLogic × Python/Z3; BlocksWorld ×
  Python); Python cells first if compute is short.
- A symbolic decision made in prose (e.g. "meet Person2 before Person3", "slot T3-T4") counts as
  solver-like: A1 *values*, and B2/B3 if the program inherits it.

## Method 1: batching (`--batch-k K`, condition `batch_k<K>`)
- The selected problems are shuffled with seed 20261031 and cut into groups of K
  (`src/deter/batching.py`), the same for every model and FL; `--n` counts problems.
- Prompt: `prompts/deter/batch_prefix_<python|z3>.txt` (the universal prefix made plural: one
  code block per problem), the K problems as `### Problem i`, the task's output format, and
  `prompts/deter/batch_suffix.txt` (K blocks, each starting `# Problem i`). The per-problem
  answer cues ("SOLUTION:", "Your response should start with 'SOLUTION:'.", "SOLUTION CODE:")
  are dropped inside a batch.
- An inference record is a group (`member_ids`). `src/run_execution_deter.py` takes the block
  headed `# Problem i` from the final answer for each member (unheaded blocks are used by order
  only when there are exactly K), and writes one execution record per problem with a `batch`
  field, so `run_evaluation.py` scores it unchanged. The shared reasoning is the text before the
  answer's first program.
- PDDL (BlocksWorld native) is not supported (dropped, see Decisions); its prompt carries each
  instance's own reference problem PDDL, so a batch would need one per problem section.

## Method 2: placeholders (`--placeholder`, condition `placeholder`)
- `scripts/build_placeholders.py` → `data/placeholders/<task>_placeholders.json` for Calendar and
  Meeting Planning (`src/deter/placeholders.py`). Calendar: Person<i>, Day<i>, T<i> (times),
  D1 (duration); Meeting: Person<i>, L<i>, T<i>, D<i> (minimum minutes), and the travel table
  replaced by `TRAVEL[a][b]`. One placeholder per distinct value; T and D numbers are shuffled so
  their order means nothing. Checks on all 100 problems of each task: restoring the surfaces gives
  the original text exactly, and no value is left in the placeholder text.
- Prompt: the usual prompt, with the problem preceded by `prompts/deter/placeholder_note_<task>.txt`
  (what each placeholder kind is, value types, and that a dict VALUES is defined at run time).
- Execution prepends `VALUES = {...}` (real values) to the program; `extracted_code` stays the
  model's code. The output is scored with the real values by the usual evaluator.
- ZebraLogic (names only, already symbols) is the planned control; BlocksWorld is skipped.

## Running
`GPU=<free> MODEL=<qwen|gpt> N=<problems> ROOT=<root> CELLS="task:fl:k5 task:fl:ph ..." scripts/run_deter.sh`
runs inference, execution and evaluation per cell in tmux `deter-<model>-<root>`. The project
dashboard shows these sessions (`deter_job` in scripts/project_dashboard_snapshot.py).
Outputs: `output_deter/` (native FL), `output_deter_crossfl/` (second FL), `output_deter_pilot/`.

Full runs (Harry, 2026-11-01: as many GPUs as allowed): `scripts/deter_dispatch.py` (tmux
`deter-dispatch`, log logs/deter-dispatch.log, state output_deter/dispatch_state.json) holds the
job list (Python cells first, then Z3, then the GPT-OSS K sweep {2, 10} on Calendar and Meeting
in Python, then the A judge per root) and starts each job on a free GPU while we hold at most 4
and one flex GPU stays idle. Qwen and GPT-OSS, 100 problems per cell.

## Pilot (2026-10-31)
20 problems (the first 20 of each dataset, i.e. 4 groups of K = 5), Calendar and Meeting in
Python, both methods, Qwen (GPU 3) and GPT-OSS (GPU 4); `ROOT=output_deter_pilot`. Check by hand:
extraction (missing `# Problem i` blocks), truncation, VALUES use, accuracy and solver-like prose,
against the baseline traces of the same 20 problems.

## Still to do after the pilot
- Judges: A1 for batching must also say which problem a paragraph is about (per-problem ratio);
  judges get the placeholder problem text and must count symbolic decisions as values. Check the
  new attribution on ~30 paragraphs.
- Full runs: both methods × both FLs × Qwen, GPT-OSS; K sweep {2, 10} on one model and dataset.
