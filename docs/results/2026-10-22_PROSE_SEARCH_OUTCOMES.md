# Does search in the reasoning reach the answer? (2026-10-22)

Scripts: `scripts/analyze_prose_search_outcome.py` (classification) and `scripts/analyze_prose_search_answer_position.py` (where the answer first appears). Tasks: Calendar, Meeting, ZebraLogic; all 3 models × 3 conditions (2,700 traces).

**Definitions**
- **Search-heavy:** the pre-code reasoning rejects at least 3 concrete candidates. That is, a line containing a time (Calendar/Meeting) or a house assignment (ZebraLogic) next to a rejection word (fail, impossible, too late, contradiction, conflict, cannot, …).
- **Completed:** the answer the program later prints already appears in the reasoning.
  - Meeting: at least 80% of the itinerary's derived times (those not in the problem).
  - Calendar: the answer's start–end pair.
  - ZebraLogic: at least 80% of houses with all but at most one attribute on one line.
- **Half-baked:** search-heavy, but the printed answer never appears in the reasoning, so the program found it.
- **Completed only after drafting code:** the answer first appears after the first `def`/`import`/`s.add(` line, i.e. the model hand-runs its own program.

**Results (all conditions pooled)**

| Model | Task | Search-heavy | Completed | …only after drafting code | Half-baked | No printed answer |
|---|---|---|---|---|---|---|
| DeepSeek | Calendar | 211/300 | 206 | 7 | 0 | 5 |
| DeepSeek | Meeting | 285/300 | 241 | 76 | 25 | 19 |
| DeepSeek | ZebraLogic | 218/300 | 207 | 34 | 4 | 7 |
| GPT-OSS | Calendar | 22/300 | 19 | 0 | 3 | 0 |
| GPT-OSS | Meeting | 51/300 | 24 | 0 | 22 | 5 |
| GPT-OSS | ZebraLogic | 43/300 | 38 | 0 | 3 | 2 |
| Qwen | Calendar | 97/300 | 94 | 4 | 1 | 2 |
| Qwen | Meeting | 233/300 | 161 | 56 | 39 | 33 |
| Qwen | ZebraLogic | 154/300 | 90 | 13 | 0 | 64 |
| **Total** | | **1,314/2,700** | **1,080** | **190** | **97** | **137** |

- Of the 1,177 search-heavy traces whose program printed an answer, **1,080 (92%) reach that answer in prose** and 97 (8%) are half-baked.
- **Half-baked searches are almost all Meeting (86 of 97)**, the task with the largest search space (up to 10 friends). They typically try orders, find the space too large ("10! too many", "Maybe max could be 8?"), and hand over to permutations or DP in the code.
- **190 completed traces reach the answer only after drafting code**, mostly DeepSeek and Qwen on Meeting. They write the program, then run its search by hand ("Let's test mentally", DP tables in prose).
- **GPT-OSS is rarely search-heavy (116 of 900)** because it seldom explores alternatives. Its blatant case is straight-line solving that gets pasted into the code (RQ4), which this rejection-based filter does not count.
- **"No printed answer" (137)** means the program crashed or printed nothing, so completion can't be checked. This is mostly Qwen ZebraLogic, which crashes in 119 of 300 runs.

**Checks:** I read 6 random half-baked traces and 9 completed ones (before and after drafting code), and all fit their label. The thresholds (3 rejections, 80%) are judgement calls, not tuned.
