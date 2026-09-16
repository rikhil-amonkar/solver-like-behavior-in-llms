# Solver-Like Reasoning Pattern Analysis

**Date**: 2026-09-16
**Analysis of**: Random sample of 20 solver-like chunks (5 per dataset) from all chunking outputs

## Overview

This document analyzes solver-like reasoning patterns observed across models (DeepSeek, GPT-OSS, Qwen), conditions (baseline, caution_a, caution_b), and datasets (blocksworld, calendar, meeting, zebralogic). Each chunk was labeled as "solver-like" by the Gemini judge, indicating the model performed computational work that should have been delegated to a constraint solver.

---

## Detailed Chunk Analysis

### 1. blocksworld / deepseek / blocksworld_p72_goal_constraint12 / chunk 12
- **Dataset**: blocksworld
- **Model**: deepseek (baseline)
- **Example ID**: blocksworld_p72_goal_constraint12
- **Chunk index**: 12 (of 19 chunks)
- **Token count**: 71
- **Label**: solver-like

**Pattern**: Manual execution tracing

**Analysis**: The model manually simulates actions ("If we put b down on table, then (on-table b) true, (clear b) true, arm empty") to verify plan correctness rather than encoding constraints.

**Reasoning chunk text**:
> Potential issue: Suppose initial holding b and clear a, but b not on table. If we put b down on table, then (on-table b) true, (clear b) true, arm empty. Then to build stack, pickup b and stack on a. If we could stack b on a directly, no need put down. Good.

---

### 2. blocksworld / deepseek / blocksworld_p26_action_constraint10 / chunk 17
- **Dataset**: blocksworld
- **Model**: deepseek (caution_a)
- **Example ID**: blocksworld_p26_action_constraint10
- **Chunk index**: 17 (of 24 chunks)
- **Token count**: 483
- **Label**: solver-like

**Pattern**: Step-by-step state simulation

**Analysis**: Exhaustive manual simulation of each action's effects ("Action putdown blue: pre holding blue. effect on-table blue, clear blue, arm-empty..."). The model is executing the plan mentally rather than letting a solver verify it.

**Reasoning chunk text**:
> Let's test plan with our domain: Initial: holding blue, clear red, red table, green table, yellow on green clear yellow. Action putdown blue: pre holding blue. effect on-table blue, clear blue, arm-empty, not holding. State: red on table clear red, blue on table clear blue, green table, yellow on green clear yellow, arm-empty. Action unstack yellow green: pre on yellow green, clear yellow, arm-empty. effect holding yellow, clear green, not on yellow green, not clear yellow, not arm-empty. State: red table clear red, blue table clear blue, green table clear green, holding yellow, arm-empty false. Action putdown yellow: pre holding yellow. effect on-table yellow, clear yellow, arm-empty, not holding. State: red table clear red, blue table clear blue, green table clear green, yellow table clear yellow, arm-empty. Action pickup green: pre on-table green, clear green, arm-empty. effect holding green, not on-table green, not clear green, not arm-empty. State: red table clear red, blue table clear blue, yellow table clear yellow, holding green. Action stack green red: pre holding green, clear red. effect on green red, clear green, arm-empty, not holding green, not clear red. State: red table, green on red clear green, blue table clear blue, yellow table clear yellow, arm-empty. Action pickup yellow: pre on-table yellow, clear yellow, arm-empty. effect holding yellow, not on-table yellow, not clear yellow, not arm-empty. State: red table, green on red clear green, blue table clear blue, holding yellow. Action stack yellow green: pre holding yellow, clear green. effect on yellow green, clear yellow, arm-empty, not holding yellow, not clear green. State: red table, green on red, yellow on green clear yellow, blue table clear blue, arm-empty. Action pickup blue: pre on-table blue, clear blue, arm-empty. effect holding blue, not on-table blue, not clear blue, not arm-empty. State: red table, green red, yellow green clear yellow, holding blue. Action stack blue yellow: pre holding blue, clear yellow. effect on blue yellow, clear blue, arm-empty, not holding blue, not clear yellow. Goal satisfied. Good.

---

### 3. blocksworld / deepseek / blocksworld_p56_baseline_constraint56 / chunk 5
- **Dataset**: blocksworld
- **Model**: deepseek (baseline)
- **Example ID**: blocksworld_p56_baseline_constraint56
- **Chunk index**: 5 (of 7 chunks)
- **Token count**: 627
- **Label**: solver-like

**Pattern**: Manual syntax verification + ground truth comparison

**Analysis**: The model obsessively checks syntactic details ("Did I include (on block2 block7) before (clear block2), yes") and compares against ground truth line-by-line instead of expressing constraints declaratively.

**Reasoning chunk text**:
> Before final, one more thought: The problem file string in final has (:goal (and then line after last (on block9 block11) is )) (two closings) and then ) for problem. But in the string I propose, right after (on block9 block11)\n ))\n)\n, yes. However, opening (:goal (and means the (and list is not closed until the first of the two closings. The second closes (:goal. Then problem define closes. Good. What about the first line (define (problem blocksworld-p42) already has the close of the problem name list; but the define is open. At end, ) closes define. Good. No line (:goal (and maybe includes two opens; yes.
> Let's maybe double-check problem init in final string:
> - I need include (on block14? Actually on block8 block14). yes. - Did I accidentally switch block5 and block10? Groundtruth: (on block10 block5), yes. In final I wrote (on block10 block5)? Let's look at final problem string in final draft: I need ensure I didn't write (on block6 block9) before (on block11 block6)? Groundtruth list:
> (on block8 block14)
> (on block3 block8)
> (on block5 block3)
> (on block10 block5)
> (on block9 block10)
> (on block6 block9)
> (on block11 block6)
> (on block7 block11)
> (on block2 block7)
> I will keep exactly. In final draft earlier, yes.
> - Did I include (on block2 block7) before (clear block2), yes. - Did I include (clear block12) before table14? yes. Goal final:
> (on-table block15)
> (on block12 block15)
> (on-table block4)
> (on-table block14)
> (on block6 block14)
> (on block3 block6)
> (on block2 block3)
> (on-table block1)
> (on block7 block1)
> (on block10 block7)
> (on-table block13)
> (on block5 block13)
> (on block8 block5)
> (on-table block11)
> (on block9 block11)
> Groundtruth exactly. Good.
> Let's think if problem-specific goal "Block 15, Block 4, Block 14, and Block 1 directly on table" includes Block4 maybe no stack on block15? It says stack Block12 on Block15, yes. We include on-table block15 and on block12 block15. Good. "Block 14 direct table, Block6 on Block14, Block3 on Block6, Block2 on Block3": yes. "Block1 direct table, Block7 on Block1, Block10 on Block7": yes. "Block13 table, Block5 on Block13, Block8 on Block5": yes. "Block11 table, Block9 on Block11": yes. Good.

---

### 4. blocksworld / deepseek / blocksworld_p71_baseline_constraint71 / chunk 2
- **Dataset**: blocksworld
- **Model**: deepseek (caution_a)
- **Example ID**: blocksworld_p71_baseline_constraint71
- **Chunk index**: 2 (of 15 chunks)
- **Token count**: 72
- **Label**: solver-like

**Pattern**: Contradiction detection through informal reasoning

**Analysis**: Identifies logical impossibility ("If all blocks start on the table... we must pick up some blocks... it acquires the (never-putdown ?b) property... cannot be placed back") through narrative reasoning rather than constraint encoding.

**Reasoning chunk text**:
> This presents a contradiction. If all blocks start on the table, and the goal is to have them all on the table in a different order, we must pick up some blocks. Once a block is picked up, it acquires the (never-putdown ?b) property. This means it cannot be placed back on the table to satisfy the goal.

---

### 5. blocksworld / qwen / blocksworld_p18_state_constraint14 / chunk 8
- **Dataset**: blocksworld
- **Model**: qwen (caution_a)
- **Example ID**: blocksworld_p18_state_constraint14
- **Chunk index**: 8 (of 10 chunks)
- **Token count**: 128
- **Label**: solver-like

**Pattern**: Manual state construction

**Analysis**: Enumerates state facts one-by-one ("(on-table block3)", "(on block6 block3)", etc.) and derives additional facts ("(clear block2) (since it's the top of the tower)") through manual inference.

**Reasoning chunk text**:
> Let's write that out in PDDL:
> - (on-table block3)
> - (on block6 block3)
> - (on block5 block6)
> - (on block4 block5)
> - (on block1 block4)
> - (on block2 block1)
> - (clear block2) (since it's the top of the tower)
> - (arm-empty)
> The goal state is:
> - (on-table block1)
> - (on-table block2)
> - (on block6 block2)
> - (on-table block4)
> - (on block3 block4)
> - (on-table block5)

---

### 6. calendar / deepseek / calendar_scheduling_example_812 / chunk 54
- **Dataset**: calendar
- **Model**: deepseek (caution_b)
- **Example ID**: calendar_scheduling_example_812
- **Chunk index**: 54 (of 72 chunks)
- **Token count**: 451
- **Label**: solver-like

**Pattern**: Exhaustive slot enumeration with conflict checking

**Analysis**: Tests every possible time slot manually ("12:00-12:30? Emily: free. Mason: free. Maria: free?... Carl busy 10:30-12:30, so conflict. no.") rather than expressing availability as constraints.

**Reasoning chunk text**:
> Need maybe "between work hours" includes start and end within, not necessarily covering; yes.
> Let's think if an alternative valid slot is 12:00-12:30? Let's re-evaluate carefully: Emily: free. Mason: free. Maria: free? Maria busy 10:30-11:00,14:00-14:30; free. Carl busy 10:30-12:30, so conflict. no. 12:30-13:00? Carl busy until 12:30, maybe free at 12:30, David/Frank busy 12:30-13:30, conflict. 13:00-13:30? David/Frank busy 12:30-13:30 conflict. Carl free? busy starts 13:30; yes. no. 13:30-14:00? Carl busy 13:30-14, conflict; David/Frank free after 13:30? David busy 12:30-13:30 => free at 13:30, Frank free; Carl busy. 14:00-14:30? Maria busy, David busy. no. 15:30-16:00? Frank busy 14:30-17, Carl busy 14:30-15:30 (ends at 15:30, if half-open free at 15:30-16:00), David free? David busy 14-15,16-17, so free 15:30-16, Emily free? Emily busy 16-16:30, so free 15:30-16, Maria free? busy 14-14:30, free. Frank conflict. no. 16:00-16:30? Emily busy, Carl busy, David busy, Frank busy. no. 16:30-17:00? Emily free after 16:30? Actually Emily busy 16:00-16:30, so free starting 16:30, meeting 16:30-17:00; Maria free; Carl busy 16-17; David busy 16-17; Frank busy 14:30-17. no. Thus 9:00.

---

### 7. calendar / qwen / calendar_scheduling_example_479 / chunk 11
- **Dataset**: calendar
- **Model**: qwen (caution_a)
- **Example ID**: calendar_scheduling_example_479
- **Chunk index**: 11 (of 17 chunks)
- **Token count**: 376
- **Label**: solver-like

**Pattern**: Hypothesis generation about selection heuristics

**Analysis**: Speculates about how the "correct" answer was chosen ("Maybe they merge intervals... choose the first free interval that is >=30 and also not after 15?") instead of solving the constraint problem.

**Reasoning chunk text**:
> Let's consider if the meeting duration half an hour, work hours 9-17. Existing schedules. If one simply looks for a common free slot, the first obvious maybe 13:30 because after lunch and before 15. Humans might skip 9:30 because it's only 30 min and right after start; but valid. The example output 13:30 may be arbitrarily chosen. If exact expected, likely they have a reference that chooses the first slot in a list maybe sorted by start? That would 9:30. Unless their candidate generation starts at 12:00? Why? Maybe they merge intervals and compute free intervals, then choose the first free interval that is >=30 and also not after 15? Free intervals:
> 9:30-10:00, 11:00-11:30, 13:30-15:00 (combined? Let's merge common free: common free intervals: 9:30-10:00, 11:00-11:30, 13:30-15:00? Check 13:30-15:00: R free 13:30-15, B free 13-16:30, D free 13-14, 14:30-16? Wait Donald busy 14:00-14:30, so common free 13:30-14:00 and 14:30-15:00, not continuous. Actually Donald busy 14-14:30, so split. So free intervals: 9:30-10, 11-11:30, 13:30-14, 14:30-15, 15:30-16. If choose first interval that can fit and preference, 9:30. If choose interval after 13? 13:30.

---

### 8. calendar / deepseek / calendar_scheduling_example_476 / chunk 3
- **Dataset**: calendar
- **Model**: deepseek (caution_b)
- **Example ID**: calendar_scheduling_example_476
- **Chunk index**: 3 (of 15 chunks)
- **Token count**: 245
- **Label**: solver-like

**Pattern**: Edge case exploration and granularity speculation

**Analysis**: Questions problem assumptions ("could start at e.g. 9:10? Usually scheduling constraints... assume all times exact half-hour?") rather than formalizing the constraint space.

**Reasoning chunk text**:
> To be correct generally, "between work hours 9:00 to 17:00" with no minute granularity, a half-hour meeting could start at e.g. 9:10? Usually scheduling constraints given in HH:MM and duration, assume all times exact half-hour? In such benchmark tasks, likely expected answer at half-hour increments. They didn't specify "at most", but "existing schedules" times at half-hour increments, meeting duration half-hour. Need choose a time that works. The exact output format examples use half-hour. We can search continuous minute slots to be more general. It might find same earliest slot; no issue. But if start at arbitrary minute, there are many solutions (e.g., 9:00-9:30 only? Actually Tuesday before 10:30 with Albert busy 9-? Albert free 9:00-9:30, Shirley free 9:00-9:30; no continuous interval longer than 30 before 10:30? Albert busy from 9:30-11, so only 9:00-9:30 exactly. Shirley busy 9:30-10. yes. Monday impossible. Discrete enough.

---

### 9. calendar / qwen / calendar_scheduling_example_548 / chunk 3
- **Dataset**: calendar
- **Model**: qwen (baseline)
- **Example ID**: calendar_scheduling_example_548
- **Chunk index**: 3 (of 13 chunks)
- **Token count**: 47
- **Label**: solver-like

**Pattern**: Quick manual elimination

**Analysis**: Brief manual check ("9:15-9:45: Melissa busy 9:30-10:00 overlaps, so not possible") to eliminate options.

**Reasoning chunk text**:
> 9:15-9:45: Melissa busy 9:30-10:00 overlaps, so not possible. 9:30-10:00 Melissa busy. So only 9:00. Thus no difference.

---

### 10. calendar / deepseek / calendar_scheduling_example_778 / chunk 14
- **Dataset**: calendar
- **Model**: deepseek (caution_a)
- **Example ID**: calendar_scheduling_example_778
- **Chunk index**: 14 (of 33 chunks)
- **Token count**: 1122
- **Label**: solver-like

**Pattern**: Interval arithmetic and intersection computation

**Analysis**: Manually computes free intervals ("Timothy Monday unavailable: 9:30-10:00 blocked... So free 9:00-9:30, 10:00-10:30...") and intersects them ("Intersection with Judith: 9:00-9:30 free both? Length 30 min, not enough").

**Reasoning chunk text**:
> Let's compute manually to ensure code output allows any valid one; my code will choose one, so no need final precomputed but need know valid. But to verify, we can compute.
> Schedules: Judith:
> - Monday 12:00-12:30 blocked
> - Wednesday 11:30-12:00 blocked
> Timothy:
> - Monday 9:30-10:00, 10:30-11:30, 12:30-14:00, 15:30-17:00
> - Tuesday 9:30-13:00, 13:30-14:00, 14:30-17:00
> - Wednesday 9:00-9:30, 10:30-11:00, 13:30-14:30, 15:00-15:30, 16:00-16:30 Work 9-17. Need 1-hour meeting.
> Availability per day: Monday: Judith available 9-12, 12:30-17 (minus? yes only blocked 12-12:30). Timothy Monday unavailable: 9:00-9:30? 9:30-10 blocked. Actually schedule: 9:30-10:00 blocked, 10:30-11:30 blocked, 12:30-14 blocked, 15:30-17 blocked. So free 9:00-9:30, 10:00-10:30, 11:30-12:30, 14:00-15:30. Intersection with Judith:
> - 9:00-9:30 free both? Judith free, Timothy free 9-9:30. Length 30 min, not enough.
> - 10:00-10:30 free both length 30 min.
> - 11:30-12:30? Judith blocked 12-12:30, Timothy free 11:30-12:30. So free both 11:30-12:00 only 30 min.
> - 14:00-15:30 free both full? Judith free, Timothy free 14-15:30. Length 1.5h. So Monday possible start 14:00-14:30? Meeting 14:00-15:00, 14:30-15:30 valid. But Judith prefers avoid Monday, so maybe not.
> Tuesday: Judith no blocked. Timothy Tuesday blocks 9:30-13:00, 13:30-14:00, 14:30-17:00. Free: 9:00-9:30 (30m), 13:00-13:30 (30m), 14:00-14:30 (30m). No 1-hour free? Wait also 9:00-9:30 only 30; 13:00-13:30; 14:00-14:30. There is no one-hour continuous free time. Thus Tuesday no possible meeting. Hmm maybe because Judith/Timothy? Did I parse Timothy Tuesday blocked until 13, then 13:30-14 blocked, 14:30-17 blocked. Free 13-13:30 and 14-14:30 no hour. So no solution. If no solution Tuesday, then if avoid Monday and Wednesday before 12 maybe still Wednesday possible after 12? Need compute.
> Wednesday: Judith blocked 11:30-12:00. Timothy Wednesday blocks: 9:00-9:30, 10:30-11:00, 13:30-14:30, 15:00-15:30, 16:00-16:30. Timothy free: 9:30-10:30 (1h), 11:00-13:30 (2.5h), 14:30-15:00 (0.5h), 15:30-16:00 (0.5h), 16:30-17:00 (0.5h). Intersection with Judith:
> - 9:30-10:30 free both length 1h. Can start 9:30. But if preference Wednesday before 12:00 to avoid? If "avoid Wednesday before 12:00", this invalid. If "Wednesday before 12:00" maybe needed? But "Judith would like to avoid more meetings on Monday. Wednesday before 12:00." Actually maybe
> "Wednesday before 12:00" could mean she would like to avoid meetings on Wednesday before 12:00, so invalid.
> - 11:00-11:30 free both? Judith free; Timothy free 11-11:30; then Judith blocked 11:30-12, so 11:00-12:00 invalid due 11:30-12. Start 11:00 ends 12:00 overlaps block; invalid. 11:30-12:00 Judith blocked.
> - 12:00-13:30 free both? Judith free after 12; Timothy free 11-13:30. Length 1.5h, valid start 12:00, 12:30? 12:00-13:00, 12:30-13:30. But if Judith wants avoid Wednesday before 12, after 12 OK. So Wednesday after 12 possible.

---

### 11. meeting / deepseek / meeting_planning_example_728 / chunk 18
- **Dataset**: meeting
- **Model**: deepseek (baseline)
- **Example ID**: meeting_planning_example_728
- **Chunk index**: 18 (of 48 chunks)
- **Token count**: 197
- **Label**: solver-like

**Pattern**: Timeline feasibility checking

**Analysis**: Manually traces travel times and meeting windows ("leaving GG 9:45 to Union Square 22 min arrive 10:07, but Deborah until 22?... Deborah available 5:30PM to 10:00PM; can meet until 10:00 only").

**Reasoning chunk text**:
> Since min 105, avail 105. Need meet 8:00-9:45 if only exactly full interval. Must arrive by 8 and stay until 9:45. Then no friends after 9:45. But could meet Deborah until 22? no after leaving GG 9:45 to Union Square 22 min arrive 10:07, but Deborah until 22? Wait Deborah available 5:30PM to 10:00PM; can meet until 10:00 only, cannot start at 10:07. Since meet duration 60 must start by 9:00 to end 10:00. But Jessica occupies 8-9:45, cannot meet Deborah after. Could meet Deborah before Jessica, then travel to GG by 8. This seems possible if Deborah 6:30-7:30 or 7-8, then travel to GG 22, arrive before 8. But need also others.

---

### 12. meeting / deepseek / meeting_planning_example_962 / chunk 31
- **Dataset**: meeting
- **Model**: deepseek (baseline)
- **Example ID**: meeting_planning_example_962
- **Chunk index**: 31 (of 71 chunks)
- **Token count**: 448
- **Label**: solver-like

**Pattern**: Permutation ordering analysis

**Analysis**: Manually predicts which permutation the solver will try first ("After trying 7th Elizabeth with 8th Paul and 8th Rebecca (both fail), then 7th Paul; the 8th choices... Elizabeth before Rebecca").

**Reasoning chunk text**:
> Let's think if the schedule D,F,A,B,C,E,G,H sequence in
> permutations(names,8) will be found before D,F,A,B,C,E,H,G? It will try D,F,A,B,C,E,Elizabeth,... first; fail. Then D,F,A,B,C,E,Paul,Rebecca? Is 7th element after Elizabeth fails maybe it tries 7th Paul, 8th Rebecca. What about
> D,F,A,B,C,E,Paul,Elizabeth? If 7th Paul and 8th Elizabeth, sequence includes D,F,A,B,C,E,Paul,Elizabeth. It omits Rebecca. Would this be lexicographically before D,F,A,B,C,E,Paul,Rebecca? Remaining after D,F,A,B,C,E are [Elizabeth, Paul, Rebecca]. After trying 7th Elizabeth with 8th Paul and 8th Rebecca (both fail), then 7th Paul; the 8th choices among remaining [Elizabeth, Rebecca] in original order: Elizabeth before Rebecca. It will try D,F,A,B,C,E,Paul,Elizabeth before D,F,A,B,C,E,Paul,Rebecca. Does this sequence fail? After Paul ends7:30, travel Haight->Sunset? Wait remaining after using Paul (7th) and Elizabeth (8th) would require travel from Haight to Sunset (15) arrive7:45, Elizabeth window ended9:45, fail. So it fails. Then D,F,A,B,C,E,Paul,Rebecca succeeds. Good. So first feasible indeed after trying two extra failures. Fine. What about D,F,A,B,C,E,Elizabeth,Paul failing; D,F,A,B,C,E,Elizabeth,Rebecca failing; D,F,A,B,C,E,Paul,Elizabeth failing; D,F,A,B,C,E,Paul,Rebecca success. Good. No issue.
> Potential issue: If after D,F,A,B,C,E,Paul,Rebecca, the schedule includes meeting Rebecca from7:41-8:26, but if Elizabeth omitted. Good.
> Potential issue: If permutations(names,8) finds D,F,A,B,C,E,Paul,Rebecca; yes.

---

### 13. meeting / deepseek / meeting_planning_example_66 / chunk 120
- **Dataset**: meeting
- **Model**: deepseek (baseline)
- **Example ID**: meeting_planning_example_66
- **Chunk index**: 120 (of 161 chunks)
- **Token count**: 85
- **Label**: solver-like

**Pattern**: Algorithm output speculation

**Analysis**: Speculates about tie-breaking ("If two schedules with same travel and earlier final, output maybe valid") rather than formalizing optimization criteria.

**Reasoning chunk text**:
> Let's think if if there is any issue with end_time variable in best_key if a route with same travel and earlier final maybe chooses earlier. If two schedules with same travel and earlier final, output maybe valid. okay. Potential issue: If route with travel67 final18:30, no. Potential issue: If route with travel70 final18:30, travel key picks67. okay.

---

### 14. meeting / deepseek / meeting_planning_example_912 / chunk 56
- **Dataset**: meeting
- **Model**: deepseek (caution_a)
- **Example ID**: meeting_planning_example_912
- **Chunk index**: 56 (of 114 chunks)
- **Token count**: 62
- **Label**: solver-like

**Pattern**: Route construction with time arithmetic

**Analysis**: Builds a specific route manually ("Rebecca at Nob Hill before James at Chinatown because travel NobHill->Chinatown6, if Rebecca 3:15-5:00, James 5:06-7:06; feasible").

**Reasoning chunk text**:
> Now, maybe the path could include "Rebecca at Nob Hill" before "James at Chinatown" because travel NobHill->Chinatown6, if Rebecca 3:15-5:00, James 5:06-7:06; feasible. Rebecca min105. Good.

---

### 15. meeting / qwen / meeting_planning_example_479 / chunk 4
- **Dataset**: meeting
- **Model**: qwen (caution_b)
- **Example ID**: meeting_planning_example_479
- **Chunk index**: 4 (of 11 chunks)
- **Token count**: 234
- **Label**: solver-like

**Pattern**: Manual schedule verification

**Analysis**: Verifies a complete schedule step-by-step ("9:00+13=9:13 wait 10:15 meet 11:15. +8=11:23 meet 12:23...") to confirm optimality.

**Reasoning chunk text**:
> Now, let's verify the manual all-9 schedule with our travel data: PH->Financial 13 yes. Financial->Nob 8 yes. Nob->Presidio 17 yes. Presidio->Castro 21 yes. Castro->Richmond 16 yes. Richmond->Mission 20 yes. Mission->Marina 19 yes. Marina->Russian 8 yes. Russian->Alamo 15 yes. Times: 9:00+13=9:13 wait 10:15 meet 11:15. +8=11:23 meet 12:23. +17=12:40 meet 13:55. +21=14:16 wait 14:45 meet 15:15. +16=15:31 meet 16:01. +20=16:21 meet 16:51. +19=17:10 wait 18:00 meet 18:30. +8=18:38 meet 19:53. +15=20:08 wait 21:00 meet 21:15. All good. So optimum 9.

---

### 16. zebralogic / deepseek / zebralogic_grid_lgp-test-3x4-10 / chunk 47
- **Dataset**: zebralogic
- **Model**: deepseek (baseline)
- **Example ID**: zebralogic_grid_lgp-test-3x4-10
- **Chunk index**: 47 (of 52 chunks)
- **Token count**: 66
- **Label**: solver-like

**Pattern**: Solution validation against clues

**Analysis**: Checks a proposed solution against constraints ("If output 'House 4: Arnold, cherry, associate, tesla model 3' but 'Carol is not in fourth house' because Carol house1; yes").

**Reasoning chunk text**:
> Potential issue: If output "House 4: Arnold, cherry, associate, tesla model 3" but "Carol is not in fourth house" because Carol house1; yes.
> Potential issue: If "The person who owns a Toyota Camry is not in the first house" because Toyota house2; yes.

---

### 17. zebralogic / deepseek / zebralogic_grid_lgp-test-6x6-0 / chunk 8
- **Dataset**: zebralogic
- **Model**: deepseek (caution_b)
- **Example ID**: zebralogic_grid_lgp-test-6x6-0
- **Chunk index**: 8 (of 45 chunks)
- **Token count**: 3
- **Label**: solver-like

**Pattern**: Uniqueness confirmation

**Analysis**: Minimal chunk confirming uniqueness ("So unique.") after manual deduction.

**Reasoning chunk text**:
> So unique.

---

### 18. zebralogic / qwen / zebralogic_grid_lgp-test-2x4-39 / chunk 3
- **Dataset**: zebralogic
- **Model**: qwen (caution_b)
- **Example ID**: zebralogic_grid_lgp-test-2x4-39
- **Chunk index**: 3 (of 4 chunks)
- **Token count**: 1253
- **Label**: solver-like

**Pattern**: Case analysis with constraint propagation

**Analysis**: Extensive manual case splitting ("Assume Arnold is in house 3. Then April must be in house 4... Eric is to the right of Arnold (house 3), so Eric is in house 4 or 5...") and backtracking when contradictions arise.

**Reasoning chunk text**:
> We need to ensure all clues are encoded correctly. There are several interactions between clues. For example, from clues 1, 2, 14, and 22, we can deduce that Bob is the engineer, drinks root beer, enjoys camping, and his birthday is in January. This means all these attributes belong to the same house. Let's trace some deductions:
> - Bob = root beer = engineer = camping = January.
> - Arnold = coffee = February = beach.
> - April = water = artist.
> - Tea = mountain.
> Positional constraints:
> - Arnold (coffee) is not in house 1 or 2. Since Eric is to his right, Arnold is not in house 5 either. So Arnold is in house 3 or 4.
> - April (water, artist) is not in house 2 or 5. Since a cruise is to the left of April, April is not in house 1. So April is in house 3 or 4.
> - Arnold and April must be in different houses. So one is in house 3 and the other in house 4.
> - Tea (mountain) is to the left of camping (Bob). So Bob is not in house 1. - Mountain is not in house 2. So the tea drinker is not in house 2.
> Let's test a case. Assume Arnold is in house 3. Then April must be in house 4.
> - House 3: Arnold, coffee, February, beach. Occupation is not engineer or artist.
> - House 4: April, water, artist. Name is not Arnold.
> - Eric is to the right of Arnold (house 3), so Eric is in house 4 or 5. But house 4 has the April person. If Eric is the April person, then his birthday is in April. - Cruise is to the left of April (house 4). So cruise is in house 1, 2, or 3. House 3 is beach, so cruise is in house 1 or 2.
> - Bob (camping, engineer, root beer, January) is not in house 1 (tea is left of him), not in house 3 (Arnold), not in house 4 (April). So Bob is in house 2 or 5.
> - Tea (mountain) is left of Bob (camping).
> - If Bob is in house 2, then tea must be in house 1.
> - H1 vacation is mountain.
> - H2 vacation is camping.
> - This means cruise cannot be in H1 or H2. Contradiction. So, the initial assumption (Arnold in house 3) must be wrong. Let's try Arnold in house 4.
> - Then April must be in house 3.
> - House 4: Arnold, coffee, February, beach.
> - House 3: April, water, artist.
> - Eric is to the right of Arnold (house 4), so Eric must be in house 5. - Bob (camping, etc.) is not in house 1, 3, 4, 5. So Bob must be in house 2. - This leads to the same contradiction as before: Tea must be in house 1.
> Cruise must be left of April (house 3), so in house 1 or 2. But house 1 is mountain and house 2 is camping. This is a contradiction. My deduction that Arnold is in H3 or H4 must be flawed.
> Let me re-read the clues. Ah, I made a mistake. Clue 1: Bob = root beer. Clue 2: Bob = engineer. So Bob = root beer = engineer. Clue 14: engineer = camping. So Bob = root beer = engineer = camping. Clue 22: January = root beer. So Bob = root beer = engineer = camping = January. This group is correct.
> Clue 17: Arnold = coffee. Clue 18: coffee = February. So Arnold = coffee = February. Clue 8: February = beach. So Arnold = coffee = February = beach. This group is correct.
> Clue 21: April = water. Clue 15: artist = April. So April = water = artist. This group is correct.
> Clue 10: tea = mountain. This group is correct.
> Let's re-evaluate positions.
> - Arnold (house 3 or 4).
> - April (house 3 or 4).
> - They are in different houses.
> Case 1: Arnold in house 3, April in house 4.
> - H3: Arnold, coffee, Feb, beach.
> - H4: April, water, artist.
> - Eric is right of Arnold(3) -> Eric is in H4 or H5. H4 is the 'April' person. Can Eric be this person? Yes. Let's assume Eric is in H5.
> - Bob (camping) is not in H1 (tea left), not H3 (Arnold), not H4 (April). So Bob is in H2 or H5. But H5 is Eric. So Bob must be in H2.
> - If Bob is in H2, tea (mountain) must be in H1.
> - H1: tea, mountain.
> - H2: Bob, root beer, Jan, engineer, camping.
> - H3: Arnold, coffee, Feb, beach.
> - H4: April, water, artist.
> - H5: Eric.
> - Cruise is left of April (H4). So cruise is in H1, H2, or H3. But H1=mountain, H2=camping, H3=beach. This is a contradiction. My deduction that Arnold is in H3 or H4 must be flawed.
> Let's restart the manual solve, it's getting complicated and error-prone. This is exactly what solver-like reasoning is. I'm doing the work the code should do.

---

### 19. zebralogic / qwen / zebralogic_grid_lgp-test-2x3-5 / chunk 4
- **Dataset**: zebralogic
- **Model**: qwen (caution_a)
- **Example ID**: zebralogic_grid_lgp-test-2x3-5
- **Chunk index**: 4 (of 9 chunks)
- **Token count**: 39
- **Label**: solver-like

**Pattern**: Clue interpretation verification

**Analysis**: Checks interpretation of positional clues ("If tea=mountain, and camping=Bob. Mountain left Bob. Good.").

**Reasoning chunk text**:
> Potential issue: "The tea drinker is somewhere to the left of the person who enjoys camping trips." If tea=mountain, and camping=Bob. Mountain left Bob. Good.

---

### 20. zebralogic / gpt / zebralogic_grid_lgp-test-6x3-8 / chunk 7
- **Dataset**: zebralogic
- **Model**: gpt (caution_b)
- **Example ID**: zebralogic_grid_lgp-test-6x3-8
- **Chunk index**: 7 (of 11 chunks)
- **Token count**: 66
- **Label**: solver-like

**Pattern**: Constraint encoding speculation

**Analysis**: Thinks about how to encode implications ("If name[i]==1 then car[i]==0... but we know each person has unique car") rather than directly encoding them.

**Reasoning chunk text**:
> Add implication: For all i, If name[i]==1 then car[i]==0, and If name[i]==0 then car[i]==1 maybe not given; but we know each person has unique car, so if Arnold has Ford, Eric must have Tesla. But distinctness of car plus each person distinct ensures that.

---

## General Solver-Like Behavior Categories

### Category 1: **Manual State Simulation**
**Description**: The model mentally executes actions or events step-by-step, tracking state changes rather than declaring constraints and letting a solver find valid states.

**Key Characteristics**:
- Explicit state transitions ("Action X: pre... effect...")
- Mental execution of plans or schedules
- Timeline tracing with arithmetic
- Route construction with cumulative time calculations

**Examples**:
- **Chunk 2** (blocksworld_p26_action_constraint10): Complete action-by-action state trace through entire plan
- **Chunk 5** (blocksworld_p18_state_constraint14): Manual state fact enumeration with derived facts
- **Chunk 11** (meeting_planning_example_728): Timeline feasibility tracing through travel times
- **Chunk 14** (meeting_planning_example_912): Route construction with precise time arithmetic
- **Chunk 15** (meeting_planning_example_479): Step-by-step schedule verification ("9:00+13=9:13 wait 10:15 meet 11:15...")

**Why This is Solver-Like**: The model is performing the execution engine's job rather than expressing state constraints and transitions declaratively.

---

### Category 2: **Exhaustive Enumeration and Elimination**
**Description**: The model generates and tests candidates one-by-one, manually checking constraints for each rather than expressing constraints declaratively for a solver to filter.

**Key Characteristics**:
- Systematic slot/option testing
- Manual conflict checking per candidate
- Interval computation and intersection
- Case-by-case analysis with backtracking

**Examples**:
- **Chunk 6** (calendar_scheduling_example_812): Testing every time slot ("12:00-12:30? Emily: free. Mason: free... Carl busy 10:30-12:30, so conflict. no.")
- **Chunk 9** (calendar_scheduling_example_548): Quick manual elimination of invalid time slots
- **Chunk 10** (calendar_scheduling_example_778): Manual interval computation and intersection across multiple participants
- **Chunk 18** (zebralogic_grid_lgp-test-2x4-39): Extensive case splitting with backtracking ("Assume Arnold is in house 3... Contradiction. Let's try Arnold in house 4...")

**Why This is Solver-Like**: The model is implementing a search algorithm manually instead of letting a SAT/CSP solver perform the search.

---

### Category 3: **Manual Constraint Propagation**
**Description**: The model manually derives consequences of constraints through informal reasoning chains rather than encoding them for automatic propagation.

**Key Characteristics**:
- Chained logical deductions
- Explicit implication following
- Derived fact computation
- Narrative contradiction detection

**Examples**:
- **Chunk 4** (blocksworld_p71_baseline_constraint71): Narrative contradiction detection ("If all blocks start on the table... we must pick up some blocks... it acquires the (never-putdown ?b) property... cannot be placed back")
- **Chunk 5** (blocksworld_p18_state_constraint14): Deriving "(clear block2) (since it's the top of the tower)" manually
- **Chunk 18** (zebralogic_grid_lgp-test-2x4-39): "From clues 1, 2, 14, and 22, we can deduce that Bob is the engineer, drinks root beer, enjoys camping, and his birthday is in January"
- **Chunk 19** (zebralogic_grid_lgp-test-2x3-5): Manual clue interpretation and implication following

**Why This is Solver-Like**: The model is performing constraint propagation that a solver's inference engine would do automatically.

---

### Category 4: **Post-hoc Verification and Checking**
**Description**: The model has already mentally solved the problem and checks a proposed solution against constraints manually rather than letting a solver validate.

**Key Characteristics**:
- Solution-to-constraints validation
- Ground truth comparison
- Syntax/format verification
- Uniqueness confirmation

**Examples**:
- **Chunk 1** (blocksworld_p72_goal_constraint12): Checking if a specific action sequence would work
- **Chunk 3** (blocksworld_p56_baseline_constraint56): Obsessive line-by-line ground truth comparison ("Did I include (on block2 block7) before (clear block2), yes")
- **Chunk 16** (zebralogic_grid_lgp-test-3x4-10): Validating output against original clues
- **Chunk 17** (zebralogic_grid_lgp-test-6x6-0): Minimal confirmation after solving ("So unique.")

**Why This is Solver-Like**: The model is acting as a solution validator instead of expressing constraints and letting the solver find and verify solutions.

---

### Category 5: **Meta-reasoning About Solution Methods**
**Description**: The model speculates about how the answer was obtained, what heuristics were used, or how the code will behave, rather than formalizing and solving the problem.

**Key Characteristics**:
- Heuristic speculation
- Tie-breaking analysis
- Algorithm behavior prediction
- Constraint encoding uncertainty

**Examples**:
- **Chunk 7** (calendar_scheduling_example_479): "Maybe they merge intervals... choose the first free interval that is >=30 and also not after 15?"
- **Chunk 8** (calendar_scheduling_example_476): Questioning granularity assumptions ("could start at e.g. 9:10? Usually scheduling constraints... assume all times exact half-hour?")
- **Chunk 12** (meeting_planning_example_962): Predicting permutation search order ("After trying 7th Elizabeth with 8th Paul and 8th Rebecca (both fail), then 7th Paul...")
- **Chunk 13** (meeting_planning_example_66): Speculating about tie-breaking ("If two schedules with same travel and earlier final, output maybe valid")
- **Chunk 20** (zebralogic_grid_lgp-test-6x3-8): Thinking about constraint encoding ("If name[i]==1 then car[i]==0... but we know each person has unique car")

**Why This is Solver-Like**: The model is uncertain about the formalization and tries to reverse-engineer the solution method instead of cleanly expressing the problem.

---

### Category 6: **Interval Arithmetic and Temporal Reasoning**
**Description**: The model manually computes time intervals, travel durations, and schedule feasibility through arithmetic rather than temporal constraint formalization.

**Key Characteristics**:
- Explicit time arithmetic
- Travel duration calculations
- Schedule feasibility checks
- Interval intersection computation

**Examples**:
- **Chunk 10** (calendar_scheduling_example_778): "Free: 9:00-9:30, 10:00-10:30, 11:30-12:30, 14:00-15:30. Intersection with Judith..."
- **Chunk 11** (meeting_planning_example_728): "leaving GG 9:45 to Union Square 22 min arrive 10:07, but Deborah until 22?"
- **Chunk 14** (meeting_planning_example_912): "travel NobHill->Chinatown6, if Rebecca 3:15-5:00, James 5:06-7:06; feasible"
- **Chunk 15** (meeting_planning_example_479): "9:00+13=9:13 wait 10:15 meet 11:15. +8=11:23 meet 12:23. +17=12:40 meet 13:55..."

**Why This is Solver-Like**: The model is performing temporal constraint arithmetic manually instead of using temporal constraint networks or interval algebra.

---

## Summary Statistics

**Category Distribution** (some chunks exhibit multiple patterns):

1. **Manual State Simulation**: 5 chunks (25%)
2. **Exhaustive Enumeration**: 4 chunks (20%)
3. **Manual Constraint Propagation**: 4 chunks (20%)
4. **Post-hoc Verification**: 4 chunks (20%)
5. **Meta-reasoning**: 5 chunks (25%)
6. **Interval Arithmetic**: 4 chunks (20%)

**Domain-Specific Trends**:
- **Blocksworld**: Heavy on manual state simulation and post-hoc verification
- **Calendar**: Dominated by exhaustive enumeration and interval arithmetic
- **Meeting**: Mix of state simulation, interval arithmetic, and meta-reasoning
- **Zebralogic**: Strong showing of manual constraint propagation and case analysis

**Key Insight**: All chunks show the model doing computational work that should be delegated to a constraint solver. Instead of expressing the problem declaratively (as constraints, state transitions, temporal relations), the model manually performs search, inference, validation, and arithmetic—acting as both the problem encoder AND the solver itself.
