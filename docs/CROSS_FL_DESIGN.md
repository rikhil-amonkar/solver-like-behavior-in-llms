# Cross-FL runs: separating dataset from formal language

Each dataset was tied to one FL (Calendar, Meeting = Python; ZebraLogic = Z3-Python;
BlocksWorld = PDDL), so differences in SLB could come from either. The cross-FL runs give every
dataset a second FL:

|             | Python (stdlib) | Z3-Python | PDDL   |
|-------------|-----------------|-----------|--------|
| Calendar    | native          | **new**   | -      |
| Meeting     | native          | **new**   | -      |
| ZebraLogic  | **new**         | native    | -      |
| BlocksWorld | **new**         | -         | native |

Hypothesis (Harry, 2026-10-30): an imperative FL (Python) causes more SLB than a declarative one
(Z3, PDDL). BlocksWorld→Python tests it on a planning task, where Python must implement the search
that the planner does for PDDL.

## Prompts
The FL part of a prompt is the prefix (`prompts/prefix/universal_csp_prefix_<fl>.txt`) and, for
Z3, the "Required imports / Your code should" block that the native ZebraLogic format has. The
native Python formats give no coding steps. New formats (native prompts are unchanged):
- `calendar_output_format_z3.txt`, `meeting_output_format_z3.txt`: native format plus a Z3 block
  written like ZebraLogic's.
- `zebralogic_output_format_python.txt`: native format with the Z3 block removed.
- `blocksworld_output_format_python.txt`: the program prints a plan, one `(action block ...)`
  per line, or `No plan`. Unlike the native PDDL prompt, it does not include the reference
  problem PDDL (which for 53 instances omits the constraint); the NL problem states the same
  initial and goal states.

## Running and scoring
`python src/run_inference.py --task calendar --fl z3 ...`; a non-native `--fl` writes to
`output_crossfl/` (kept out of `output/`, which the judges and tables read). Execution records
`fl`, `z3_used` and `fl_compliance` per program. A Python BlocksWorld program's printed plan is
checked with VAL against the golden domain and problem, as the planner's plan is for PDDL;
`No plan` on an unsolvable instance counts as correct (as a proven-unsolvable planner run does).
- `scripts/run_crossfl_gpu7.sh`: Qwen and GPT-OSS × four pairings × three conditions (`GPU=`,
  `MODELS=`; default GPU 7). Since 2026-10-30: Qwen on GPU 2 (tmux `crossfl-qwen`), GPT-OSS on
  GPU 3 (`crossfl-gpt`), started by `scripts/switch_judges_01_crossfl_23.sh` (tmux `judge-switch`),
  which moves the judges to GPUs 0 and 1.
- `scripts/run_crossfl_deepseek.sh`: DeepSeek over the API (tmux `crossfl-deepseek`,
  `crossfl-deepseek-bw`, `crossfl-deepseek-meeting`; `PAIRS=` picks pairings).

## FL compliance (decided: flag and report)
`scripts/fl_compliance_report.py` flags programs not written in the FL asked for (Python: only
standard-library imports; Z3: imports z3 and calls `check()`), on native and cross-FL runs.
Results: docs/results/2026-10-30_FL_COMPLIANCE.md.

## Hardcoding (decided: look at the programs before choosing a checker)
The B judge (gemma_b5t) prompt covers Python, Z3 and PDDL. Its reliability on Z3 rests on one
program Harry labelled (bprec2-00) and three in Claude's blind set. The static checker covers
Meeting only. First look at DeepSeek Calendar-Z3 (133 programs): no literal answers or
`start == <answer>` pins; decisions pinned as constraints (`s.add(day == 2)` when the problem
only rules out Monday; in one case the pin is wrong and the program misses the answer); Python
loops that use Z3 only as a feasibility check. ZebraLogic-Python: 1 of 100 prints a literal grid;
the rest search with permutations.

## Meeting golden accuracy is a formatting artefact (checked 2026-10-30)
DeepSeek Meeting-Z3 golden (exact-string) accuracy is .14/.12/.17 vs .29/.50/.37 native, but
constraint-based accuracy (which already fails itineraries that meet fewer friends than the
golden one) is similar. The prompt's rule gives `You meet [person] from [time] to [time].`
while its example has `You meet Betty for 60 minutes from ...`; golden strings use the example's
form. 39-48 of the correct Z3 itineraries per run follow the rule, so they cannot match. With
` for N minutes` stripped from both sides: DeepSeek Z3 .30/.25/.27, native .30/.53/.38. The rest
are equally good itineraries in another order or with other friends (Z3 returns any model).
Native GPT-OSS Meeting has the same problem (85-90 of 100 omit the phrase; .02 -> .29/.46/.46).
The paper uses constraint-based accuracy for Meeting, so its numbers are unaffected.
Fixed (Harry, 2026-10-30): `normalize_for_golden` in `src/run_evaluation.py` drops ` for N minutes`
from Meeting meet lines on both sides before the golden comparison. All Meeting runs (native
and cross-FL) were rescored; only `matches_expected` and golden accuracy changed. Golden now:
DeepSeek .30/.53/.38, Qwen .31/.32/.32, GPT-OSS .29/.46/.46, DeepSeek Z3 .30/.25/.27.
