# Placeholder-trace check of the A judge (paper Appendix E, "Placeholder traces")

Sampled from `output_deter/ontology/` (judge gemma_v11t) with seed 1 by the code in this file's header.
For each paragraph, mark whether it is solver-like (assigns, tests or rules out values of decision variables of this instance, here named by placeholders).
Result (Harry, 2026-11-01): part A 20/20 not SLB (the judge's none is right); part B 4/10 SLB (B2, B3, B5, B6), so the judge's SLB label is right on 4 of 10 placeholder paragraphs; the other 6 reason about the program or interpret a constraint.

## A. 20 paragraphs the judge labels none (of 6174 that mention a placeholder and a word like first/earliest)

### A1. `qwen/calendar/placeholder/calendar_scheduling_example_819#7` paragraph 19

```
This would choose earliest actual weekday if multiple. Is that better? The problem says day must be full weekday name. If allowed days are Day1-Day4, and actual values maybe not in order, a human might choose earliest in the week. But the text lists them in a set, not "from Day1 to Day4". The placeholder names Day1..Day4 may correspond to the order in the week? It says Day1, Day2, ... for weekdays; placeholder numbers carry no meaning? It specifically says "Placeholder numbers carry no meaning; in particular, T1, T2, ... are not in chronological order." It doesn't explicitly say Day1..Day4 not chronological, but likely also no meaning. It says "the values are the ones of an ordinary scheduling problem stated as written". If it says "on either Day1, Day2, Day3 or Day4", that's a set. Tie-break unspecified. If exact expected, their solver likely iterates in the order given (Day1..Day4). But if they wanted actual week order, they'd state "from Monday to ..." maybe. Since Day1-3 impossible, irrelevant. We can keep placeholder order to match text order.
```

Harry's label (2026-11-01): not SLB

### A2. `qwen/meeting/placeholder/meeting_planning_example_210#1` paragraph 2

```
Maybe the original problem from "Mini-SP" or "CSP" where goal is "meet as many friends as possible" and if multiple, maybe "meet each for the minimum required time"? The output statements include "for 60 minutes" likely exactly required. I'd choose minimize total meeting time (i.e., exactly D) to maximize count. Secondary: maximize count, then minimize total elapsed time (finish time), then lexicographic order? That yields concise schedule. But if hidden expects max total time, our output may be considered suboptimal? Let's infer from phrase "You'd like to meet Person1 for a minimum of D2 minutes." If you want to meet as many friends as possible, minimum is enough. If you have extra time, you could extend but not necessary. "optimize your goals" singular goal count. So min durations acceptable. But "for [minutes] minutes" in meet statement: if we meet exactly D, fine. If we wait until window end? no.
```

Harry's label (2026-11-01): not SLB

### A3. `qwen/calendar/placeholder/calendar_scheduling_example_625#6` paragraph 23

```
Could "Person2 would like to avoid more meetings on Day1. Day2 before T9." mean "avoid more meetings on Day1, [and] Day2 before T9" i.e., avoid Day1 and Day2 before T9. Yes.
```

Harry's label (2026-11-01): not SLB

### A4. `qwen/calendar/placeholder/calendar_scheduling_example_776#7` paragraph 4

```
But the sentence "Day2.
Day3." could mean avoid after T4 on Day2 and Day3 too.
Then preferred set should be start < T4 on any day.
If no Day1 before, a Day2 before is preferred over Day1 after.
If we fallback earliest, might fail hard.
Could we choose preferred set as start < T4 on any day, but if Day1 before exists, it's earliest anyway.
If no Day1 before, choose earliest start < T4 on any day (Day2/3) if exists, else earliest feasible.
This would honor all-days-after preference.
But violates literal avoid Day2/Day3.
Which is more plausible?
Let's evaluate punctuation: "on Day1 after T4.
Day2.
```

Harry's label (2026-11-01): not SLB

### A5. `qwen/calendar/placeholder/calendar_scheduling_example_185#11` paragraph 13

```
Could there be a constraint that Person2 would like to avoid more meetings before T1, but Person2 has no meetings, so if we schedule before T1, they will have one meeting before T1. If we schedule after, zero. Good.
```

Harry's label (2026-11-01): not SLB

### A6. `qwen/meeting/placeholder/meeting_planning_example_867#24` paragraph 25

```
Now, let's finalize code. But before final, let's consider if we should include a more robust tie-break using actual names. The path tuple of indices is okay. But if actual names are used in output, a lexicographic by actual names might be more natural for a human. However, if two friends have names "Alice" and "Bob", placeholder order might not match alphabetical. A solver that searches in text order would prefer Person1 then Person2, not alphabetical. Our index tie matches text order. Good.
```

Harry's label (2026-11-01): not SLB

### A7. `qwen/calendar/placeholder/calendar_scheduling_example_765#7` paragraph 21

```
Now, let's think about if there is a hidden constraint: "Person2 would rather not meet on Day1 before T3. Day3." Could mean Person2 would rather not meet on Day1 before T3, *and* the meeting should be on Day3. We handle.
```

Harry's label (2026-11-01): not SLB

### A8. `qwen/calendar/placeholder/calendar_scheduling_example_826#3` paragraph 27

```
"Person1 would rather not meet on Day3. Day4. You would like to schedule the meeting at their earlist availability." It states preference then earliest. If both are preferences, maybe choose earliest among all, but if there is a tie? No ties. So preference would be irrelevant unless it affects "earliest availability"? Maybe "their earliest availability" means earliest time Person1 is available AND willing? If Person1 would rather not meet on Day3/4, those days are not their availability? Could be.
```

Harry's label (2026-11-01): not SLB

### A9. `qwen/meeting/placeholder/meeting_planning_example_335#0` paragraph 16

```
Need consider waiting statements. Itinerary steps: start at location at time. Then for each action: travel to next location in X minutes and arrive at time. Wait until time if needed before meeting. Meet person for D minutes from start to end. If after last meeting, no need to travel home. If start time equals meeting start and no travel? Start at L1; if first friend at L1? But friends at L2-L5, distinct? L1 start, friends at L2-L5, so travel. But could location placeholder values duplicate? likely distinct. If travel time 0? Maybe not. Need handle if no travel (same loc) maybe skip travel? Rules each statement exactly one step (start, travel, wait, meet). If travel time 0? Could output "You travel to X in 0 minutes and arrive at time."? Maybe not needed if same location. But start location L1, friend locations L2-L5 distinct placeholders; values likely distinct. Between friends distinct. But safe: if current loc == next loc, no travel statement? But then if need wait, output wait. If no wait, meet. If travel time 0 but different loc? Could output travel in 0 minutes. Fine.
```

Harry's label (2026-11-01): not SLB

### A10. `qwen/calendar/placeholder/calendar_scheduling_example_579#0` paragraph 9

```
Need find a time (start) such that meeting of duration D1 within work hours T2 to T4, not overlapping busy intervals for each person, and start/end?
"Person2 can not meet on Day1 after T8." Need interpret: cannot meet after T8 means meeting must not be after T8?
Could mean no meeting start after T8, or no part of meeting after T8?
Usually "can not meet on Day1 after T8" means the meeting time must be before or at T8?
In scheduling, if someone can't meet after time X, the meeting must end by X (or start before?
Need decide).
The phrase: "Person2 can not meet on Day1 after T8." If meeting is an interval, being after T8 likely means any part after T8?
To be safe, require end <= T8?
```

Harry's label (2026-11-01): not SLB

### A11. `qwen/calendar/placeholder/calendar_scheduling_example_116#2` paragraph 14

```
Potential issue: The prompt says "Placeholder numbers carry no meaning; in particular, T1, T2, ... are not in chronological order. The values are the ones of an ordinary scheduling problem stated as written: every interval "Ta to Tb" ends after it starts, and all times lie within one day." This means for each interval in text, the first placeholder's value is earlier than second. So work hours T16 to T11: T16 < T11. Good.
```

Harry's label (2026-11-01): not SLB

### A12. `qwen/calendar/placeholder/calendar_scheduling_example_548#3` paragraph 41

```
Now, possible issue: Person2 busy intervals include T3 to T2. If T2 < T5 and T4 < T6. But T4 could be before T2? Overlap. Fine.
```

Harry's label (2026-11-01): not SLB

### A13. `qwen/meeting/placeholder/meeting_planning_example_444#1` paragraph 2

```
- Travel: "You travel to [location] in [minutes] minutes and arrive at [time]." Example: "You travel to Financial District in 22 minutes and arrive at 9:22AM." If travel time 0? Distinct locations maybe positive. If same location? Could be if consecutive friends same location? Here locations distinct L2-L6, start L1 distinct, but could values? Placeholders distinct locations? likely yes. But generic handle travel 0? Statement maybe "You travel to X in 0 minutes and arrive at time." But if same location, maybe no travel? The rules say each statement exactly one step (start, travel, wait, or meet). If moving from one location to another, include travel. If no travel needed (same loc), maybe skip? But if sequence includes same location (not here), we could just wait/meet. But for structure, locations are distinct. We can include travel if location changes; if same, no travel statement? But to keep chronological, if same loc and need wait, output wait. If no time gap, no wait.
```

Harry's label (2026-11-01): not SLB

### A14. `gpt/calendar/placeholder/calendar_scheduling_example_858#0` paragraph 3

```
But then they give placeholder explanation. Then they give an example task. However the actual task we need to solve is the one described in the prompt? It seems the actual task is the example: "TASK: You need to schedule a meeting for Person1 and Person2 for D1 between the work hours of T11 to T12 on either Day1, Day2, Day3 or Day4. ... Person1 would like to avoid more meetings on Day4. Find a time that works for everyone's schedule and constraints."
```

Harry's label (2026-11-01): not SLB

### A15. `qwen/calendar/placeholder/calendar_scheduling_example_858#11` paragraph 26

```
Let's consider if the meeting should be strictly before work_end, i.e. end < work_end. Usually "between work hours" inclusive. If strict, our solution might choose end at work_end and fail. But ordinary scheduling allows ending at work end. The prompt says "between the work hours of T11 to T12" and "every interval ends after starts". I think inclusive.
```

Harry's label (2026-11-01): not SLB

### A16. `qwen/calendar/placeholder/calendar_scheduling_example_555#6` paragraph 41

```
Now, maybe the meeting should be scheduled "between the work hours of T6 to T5" meaning start and end must be strictly inside, not equal endpoints? Usually between can include endpoints? Calendar work hours 9 to 5, meeting can start at 9 and end at 5. We allow. If strict, our output at endpoint might be invalid. But likely inclusive. If they wanted strict, they'd say after/before. Good.
```

Harry's label (2026-11-01): not SLB

### A17. `qwen/meeting/placeholder/meeting_planning_example_272#3` paragraph 20

```
Need maybe maximize number, then maximize total meeting time? But meeting durations fixed for met friends, so total meeting time = sum D of met. If count equal, same set? If count equal but different friends, sum D could differ. "meet as many friends as possible" primary; if same count, maybe prefer longer total meeting? But D are minimums, not desired total. Could be "You'd like to meet Person1 for a minimum of D1 minutes" means you want at least that, but if you can meet more, maybe not goal. If same count, maybe choose friends with larger D? Unlikely.
```

Harry's label (2026-11-01): not SLB

### A18. `gpt/calendar/placeholder/calendar_scheduling_example_710#0` paragraph 9

```
We need to find a day among Day1, Day2, Day3 (but Person1 cannot meet on Day3) where both participants are free for D1 minutes within work hours and not overlapping busy intervals.
```

Harry's label (2026-11-01): not SLB

### A19. `qwen/meeting/placeholder/meeting_planning_example_870#10` paragraph 9

```
If we want to be safe with a validator that checks only validity and count, any tie okay. If exact, no way. But we can choose a reasonable secondary: maximize count, then minimize final time, then lexicographically by actual person names (alphabetical) because output uses actual names. Or by input order? Which is more likely? The prompt's placeholders Person1, Person2 are just placeholders; actual names are real. "concise, plain chronological statements" no tie. I'd lean to input order because it's deterministic from structure and simpler. But actual names alphabetical might be more "natural" for final answer. However, if actual names are random, alphabetical may not correspond to Person order. The expected answer if generated by a reference solver might use the order of friends as listed (Person1..Person9) for tie-breaking. Many solvers iterate i from 0 to n-1 and keep first best, which yields lexicographically by index if they update only on > count, not on ties. Or they might use DP and choose first mask. Hard.
```

Harry's label (2026-11-01): not SLB

### A20. `qwen/calendar/placeholder/calendar_scheduling_example_765#0` paragraph 19

```
The task text: 
"Person2 would rather not meet on Day1 before T3. Day3. Find a time that works for everyone's schedule and constraints."
Could be two sentences: "Person2 would rather not meet on Day1 before T3." and "Day3." That doesn't make sense unless "Day3" is a standalone answer? Maybe it's a typo: "Person2 would rather not meet on Day1 before T3. Day3." Maybe they meant "Person2 would rather not meet on Day1 before T3. Day3." as in "Person2 would rather not meet on Day1 before T3. [Prefer] Day3." In natural language, a standalone day could mean "Day3" is a hard constraint? But if hard, they'd say "The meeting must be on Day3." However earlier says either Day1, Day2 or Day3.
```

Harry's label (2026-11-01): not SLB

## B. 10 paragraphs the judge labels SLB (of 333)

### B1. `qwen/calendar/placeholder/calendar_scheduling_example_36#2` paragraph 10

```
Could "Person3 do not want to meet on Day1 after T7" mean they don't want meetings that start after T7 *and end after T7?* Still impossible if start after T7. If free starts after T7, impossible.
```

Harry's label (2026-11-01): not SLB

### B2. `qwen/meeting/placeholder/meeting_planning_example_88#0` paragraph 8

```
Given only one friend.
But maybe generic enough?
The text says table TRAVEL for L1,L2 only.
Friends list likely one: Person1 at L2 T2-T3 D1.
Start L1 T1.
Need find schedule: start at L1 at T1.
Travel to L2 (maybe wait at L1, travel, wait at L2, meet).
Need meet Person1 for at least D1 minutes within their window [T2,T3].
Travel time from L1 to L2 = TRAVEL['L1']['L2'].
We can choose departure time from L1 >= T1, arrival L2 = depart + travel.
If arrival < T2, wait until T2.
Meet start = max(arrival, T2).
Need meet end = meet_start + D1 <= T3.
If feasible, output start, travel, wait if needed, meet.
If not feasible, what?
Could choose not to travel?
But goal meet as many as possible (0).
```

Harry's label (2026-11-01): SLB

### B3. `qwen/calendar/placeholder/calendar_scheduling_example_724#13` paragraph 19

```
If no after T13 candidate, that means T5-T14 covers from some T5 <= T13 to T14, or other intervals.
A spanning candidate starting before T13 and ending after would require a gap that crosses T13, but T3-T13 busy ends at T13, and T5-T14 starts at T5.
If T5 > T13, there is after gap T13-T5, so after candidate exists if duration fits.
If T5 <= T13, T5-T14 busy covers T13 onward, no spanning gap across T13 because busy T5-T14 and T3-T13 overlap/cover.
There could be a gap before T13 that ends at T13 (entirely before) and no spanning.
So fallback earliest likely entirely before.
Thus end-based vs start-based fallback not big.
```

Harry's label (2026-11-01): SLB

### B4. `qwen/calendar/placeholder/calendar_scheduling_example_776#10` paragraph 5

```
The preference filter has no effect on output!
Nice.
Unless we had preferred set including Day2 before T4, but we don't.
So output is earliest feasible by placeholder order.
That is canonical and safe.
It also satisfies preference if possible (because earliest feasible will be Day1 before T4 if any such exists).
If no Day1 before T4, preference infeasible under literal, output earliest.
Great.
```

Harry's label (2026-11-01): not SLB

### B5. `qwen/calendar/placeholder/calendar_scheduling_example_36#1` paragraph 7

```
Note T8 > T9 and T5 > T8, so P3 busy T8-T5. P1 busy T9-T8. Thus from T9 to T8 both P1 and P3 busy? P1 T9-T8, P3 T8-T5 starts at T8, so at T8 maybe no overlap if half-open. P1 free after T8. P3 busy until T5. P3 also busy T4-T6 and T1-T2. P1 busy T7-T6. Preference T7.
```

Harry's label (2026-11-01): SLB

### B6. `qwen/calendar/placeholder/calendar_scheduling_example_765#10` paragraph 26

```
Now, maybe if Day3 is infeasible due to Person1? Person1 free Day3. Person2 maybe free. If no, fallback.
```

Harry's label (2026-11-01): SLB

### B7. `qwen/calendar/placeholder/calendar_scheduling_example_70#4` paragraph 11

```
Could there be a case where earliest feasible start is not a boundary because of a busy interval that starts after work start but ends before? No, if work start is free, earliest work start. If work start overlaps a busy interval, earliest is that busy end (if <= work_end-duration). If multiple, max of overlapping busy ends. So boundary. Minute search okay.
```

Harry's label (2026-11-01): not SLB

### B8. `qwen/calendar/placeholder/calendar_scheduling_example_98#5` paragraph 17

```
Start-constraint allows start at T13, strict disallows (end > limit).
Is that possible and intended?
"cannot meet after T13" if start at T13, meeting is after T13, likely invalid.
But if they only constrain start, maybe allowed.
Would generator produce such?
Maybe not.
If they add busy interval from T13 to end, start at T13 would be invalid?
If busy interval [T13, end], meeting [T13, T13+D) overlaps if D>0, so invalid.
If they constrain start <= T13, start at T13 valid.
Natural language "after T13" excludes start after, but start at T13 not after.
However meeting occurs after.
Ambiguous.
```

Harry's label (2026-11-01): not SLB

### B9. `qwen/calendar/placeholder/calendar_scheduling_example_396#9` paragraph 1

```
Now, let's revisit the inconsistency possibility and whether our solver might fail to find a solution if the actual values are such that only a zero-duration meeting works. If D1=0, our range includes work_start to work_end. Feasibility with per-person merged intervals using strict overlap will allow start=end at a point not inside any busy interval. If the only free point is T14 where P5 busy [T1,T14] and P3 busy [T14,T3], strict overlap: start=14, end=14. P5 interval [T1,T14]: start < e? 14<14 false. P3 [T14,T3]: end > s? 14>14 false. So feasible. It would output earliest such point maybe work_start if free, else T14. If D1=0, output start=end. But meeting duration zero unusual. Our code supports.
```

Harry's label (2026-11-01): not SLB

### B10. `qwen/calendar/placeholder/calendar_scheduling_example_938#9` paragraph 2

```
Now, maybe the day placeholders Day1..Day5 are not in chronological order, but our preference order uses listed order. If checker validates, okay. If exact, maybe not. But as argued, only Day5/3 feasible, preference resolves. If Day5 infeasible, Day3. So day order irrelevant. Within day, earliest start. Good.
```

Harry's label (2026-11-01): not SLB
