# Cross-FL runs: separating dataset from formal language

Each dataset was tied to one FL (Calendar, Meeting = Python; ZebraLogic = Z3-Python;
BlocksWorld = PDDL), so differences in SLB could come from either. Two new cells cross them:

|            | Python (stdlib) | Z3-Python |
|------------|-----------------|-----------|
| Calendar   | native          | **new**   |
| ZebraLogic | **new**         | native    |

BlocksWorld stays PDDL-only; Meeting → Z3 is optional and not run.

## Prompts
The FL part of a prompt is the prefix (`prompts/prefix/universal_csp_prefix_<fl>.txt`) and, for
Z3, the "Required imports / Your code should" block that the native ZebraLogic format has. The
new formats follow that rule:
- `prompts/formats/calendar_output_format_z3.txt`: native Calendar format plus a Z3 block
  written like ZebraLogic's (variables, domain constraints, participant constraints,
  `solver.check()`, print).
- `prompts/formats/zebralogic_output_format_python.txt`: native ZebraLogic format with the Z3
  block removed (the native Python formats give no coding steps).
Native prompts are unchanged.

## Running
`python src/run_inference.py --task calendar --fl z3 ...`; a non-native `--fl` writes to
`output_crossfl/` (kept out of `output/`, which the judges and tables read). Execution parses
output by task as before, records `fl` and a per-example `z3_used`. Evaluation is unchanged.
`scripts/run_crossfl_gpu7.sh` runs Qwen and GPT-OSS × both cells × three conditions on GPU 7.

## Open
- DeepSeek: there is no `DEEPSEEK_API_KEY` on the server, so its cells are not run.
- Judging: the B (program) judge and `src/hardcoded/static_checker.py` were built for Python
  programs; a Z3 program can hardcode the answer through constraints such as
  `s.add(start == 810)`. Needs a definition and a reliability check before judging.
- Compliance: `z3_used` shows whether Calendar-Z3 programs call the solver and whether
  ZebraLogic-Python programs avoid it; non-compliant traces need a rule (drop or report).
