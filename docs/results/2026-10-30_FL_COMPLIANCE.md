# FL compliance (2026-10-30)

Programs not written in the FL the prompt asked for. Python: imports only standard-library modules. Z3: imports z3 and calls a solver's check(). Programs that do not parse are counted separately (mostly prose captured as code). PDDL is not checked. Per-example flags: output/fl_compliance.json, output_crossfl/fl_compliance.json. Regenerate with scripts/fl_compliance_report.py; cross-FL rows fill in as runs finish.

Native runs: 3 non-compliant programs, all truncated Z3 sketches with no check().

| Root | Model | Task | FL | Condition | Programs | Not valid Python | Non-compliant | Rate | Reasons |
|---|---|---|---|---|---|---|---|---|---|
| output | deepseek | calendar | python | baseline | 97 | 3 | 0 | 0.00 |  |
| output | deepseek | calendar | python | caution_a | 100 | 0 | 0 | 0.00 |  |
| output | deepseek | calendar | python | caution_b | 100 | 0 | 0 | 0.00 |  |
| output | deepseek | meeting | python | baseline | 97 | 3 | 0 | 0.00 |  |
| output | deepseek | meeting | python | caution_a | 96 | 4 | 0 | 0.00 |  |
| output | deepseek | meeting | python | caution_b | 97 | 3 | 0 | 0.00 |  |
| output | deepseek | zebralogic | z3 | baseline | 98 | 2 | 0 | 0.00 |  |
| output | deepseek | zebralogic | z3 | caution_a | 98 | 2 | 0 | 0.00 |  |
| output | deepseek | zebralogic | z3 | caution_b | 100 | 0 | 1 | 0.01 | z3 imported but no check() (1) |
| output | gpt | calendar | python | baseline | 99 | 0 | 0 | 0.00 |  |
| output | gpt | calendar | python | caution_a | 98 | 0 | 0 | 0.00 |  |
| output | gpt | calendar | python | caution_b | 99 | 0 | 0 | 0.00 |  |
| output | gpt | meeting | python | baseline | 99 | 0 | 0 | 0.00 |  |
| output | gpt | meeting | python | caution_a | 100 | 0 | 0 | 0.00 |  |
| output | gpt | meeting | python | caution_b | 97 | 2 | 0 | 0.00 |  |
| output | gpt | zebralogic | z3 | baseline | 99 | 1 | 0 | 0.00 |  |
| output | gpt | zebralogic | z3 | caution_a | 100 | 0 | 0 | 0.00 |  |
| output | gpt | zebralogic | z3 | caution_b | 100 | 0 | 0 | 0.00 |  |
| output | qwen | calendar | python | baseline | 100 | 0 | 0 | 0.00 |  |
| output | qwen | calendar | python | caution_a | 100 | 0 | 0 | 0.00 |  |
| output | qwen | calendar | python | caution_b | 99 | 1 | 0 | 0.00 |  |
| output | qwen | meeting | python | baseline | 98 | 1 | 0 | 0.00 |  |
| output | qwen | meeting | python | caution_a | 97 | 3 | 0 | 0.00 |  |
| output | qwen | meeting | python | caution_b | 99 | 0 | 0 | 0.00 |  |
| output | qwen | zebralogic | z3 | baseline | 98 | 2 | 0 | 0.00 |  |
| output | qwen | zebralogic | z3 | caution_a | 97 | 3 | 2 | 0.02 | z3 imported but no check() (2) |
| output | qwen | zebralogic | z3 | caution_b | 100 | 0 | 0 | 0.00 |  |
