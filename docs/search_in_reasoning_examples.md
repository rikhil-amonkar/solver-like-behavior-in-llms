# Examples: reasoning that performs the search itself (2026-10-22)

Each trace below carries out the search over candidate solutions in prose (trying orders, case splits, slot-by-slot checks), even though the program it then writes performs the same search. There are two flavours: **searching to find the answer** before writing code (DeepSeek and GPT-OSS Meeting, Qwen ZebraLogic) and **searching to verify** the answer while or after writing solver code (GPT-OSS ZebraLogic, DeepSeek ZebraLogic under caution_a, Qwen Calendar).

Candidates were found by counting search markers in every pre-code trace (case/option N, try another, contradiction, fails, suppose, backtrack) and reading the densest windows. Excerpts are verbatim windows from `reasoning_before_code`.

**Judge scores are not quoted.** The stored Gemini chunking outputs are attached to the wrong examples (see the note at the end), so their solver-like fractions for these traces are meaningless.

## deepseek / meeting / baseline / `meeting_planning_example_974`

Trace length: 212,634 characters. Tries friend orders one after another in shorthand (W-D-R-J-K, J-R-D-W-K, ...), computes each arrival and marks the order as failing. The trace is 212k characters, much of it this kind of search; the program then searches with `itertools.permutations`.

```text
D? J12-12:45, W? Richmond->RH13 arr12:58, W12:58-14:58, R? RH->NH5 arr15:03, R15:03-16:33, D? NH->NB8 arr16:41 too late.
W before R before D? Start W12:30-14:30, R14:35-16:05, D? NH->NB8 arr16:13, D16:13-17:28 >16:30 fail. Need D before R? W-D-R we had W12:30-14:30, D14:35-15:50, R15:58-17:28. Then J/K/Karen late maybe? Let's see:
W 12:30-14:30 at RH, D14:35-15:50 at NB, R15:58-17:28 at NH.
After R, need J (45), K(75), Karen(60), Nancy, Brian, Joshua. J at Richmond start by18:30; K by18:30; Karen by19:45.
Order after R17:28:
- J: NH->Richmond14 arr17:42, J17:42-18:27.
- K: Richmond->Marina9 arrive18:36, K18:36-19:51 >19:45 fail by6. Could K before J? NH->Marina11 arr17:39, K17:39-18:54; J? Marina->Richmond11 arrive19:05, J19:05-19:50 >19:15 fail. Could J before W? Earlier J-W-D-R failed due R late? Actually J12-12:45, W12:58-14:58, D15:03-16:18, R16:25-17:55 fail. no.
Could order W-J-D-R? W12:30-14:30, J? RH->Richmond14 arr14:44, J14:44-15:29, D? Richmond->NB17 arr15:46, D15:46-17:01 fail. no.
Order W-D-J-R? W12:30-14:30, D14:35-15:50, J? NB->Richmond18 arr16:08, J16:08-16:53, R? Richmond->NH17 arr17:10, R17:10-18:40 fail. no.
Order W-D-R-J-K? R15:58-17:28, J17:42-18:27, K18:36-19:51 fail. Thus J and K together after R impossible if either after. Unless J before R and R before K etc? Try J-R-K? J12-12:45, R13:15-14:45, K? NH->Marina11 arr14:56, K14:56-16:11, W? Marina->RH8 arr16:19, W16:19-18:19, D? RH->NB5 arr18:24 too late. Need D before W maybe: J-R-D-W-K? J12-12:45, R13:15-14:45, D14:53-16:08, W16:13-18:13, K? W->Marina7 arr18:20, K18:20-19:35, Karen? Marina->Emb14 arr19:49 fail. If K before W: D16:08, NB->Marina9 arr16:17, K16:17-17:32, W? Marina->RH8 arr17:40, W17:40-19:40 fail. So after J-R-D, W and K and Karen no.

Maybe meet Karen before K after D? D16:08, NB->Emb6 arrive16:14, Karen16:14-17:14, W? Emb->RH8 arrive17:22 fail; K? Emb->Marina12 arrive17:26, K17:26-18:41, W? Marina->RH8 arrive18:49 fail. So Karen after D conflicts with W.

Maybe W before R/D etc. Need W earlier, and J/R/D all? Could be W12:30-14:30, R14:35-16:05, D? NH->NB8 arr16:13, D16:13-17:28 fail. W12:30-14:30, D14:35-15:50, R15:58-17:28. This seems the only way to include W,R,D. Then J/K late problem with K. What if after R, K first then J? K17:39-18:54, J? Marina->Richmond11 arrive19:05, J 45 end19:50 >19:15 fail. J first K fail. So W-D-R-J-K impossible. If D before R but R17:28
```

## gpt / meeting / baseline / `meeting_planning_example_225`

Trace length: 8,894 characters. Tries alternative orders for Brian, Sarah and Jeffrey, rules each out by arithmetic, and concludes in prose that at most two friends can be met. The program then searches with `itertools.permutations` (133 lines).

```text
rrive 5:30. Jeffrey available until 10pm, need 75 min, we can meet 5:30-6:45 (75 min). That works.

Now Sarah at North Beach window 4:00-6:15, need 60 min. Need to fit with others. After Brian we are at Alamo Square until 5:15, then travel to North Beach? Let's check travel times:

Alamo Square to North Beach = 15 min (given). Actually Alamo to North Beach: 15 min. So after meeting Brian until 5:15, travel 15 min arrive 5:30 at North Beach. Sarah available until 6:15, need 60 min, but from 5:30 to 6:15 is only 45 min, insufficient. So can't meet Sarah after Brian.

Alternative order: meet Sarah and Brian overlapping? Could try schedule where we meet Sarah earlier, then Brian, then Jeffrey. Let's examine.

We need 60 min with Sarah between 4:00-6:15. Suppose we meet Sarah 4:00-5:00 at North Beach. Then travel to Alamo Square for Brian: North Beach to Alamo = 16 min (given). Arrive 5:16. Brian window ends 5:30, need 75 min -> impossible.

What about meeting Sarah later, after Brian? Brian ends 5:15, then travel to North Beach 15 min arrive 5:30, only 45 min left. Not enough.

What about meeting Sarah before Brian, but we need 60 min; could start 4:30-5:30 (but Brian also 4:00-5:30). Overlap.

Maybe we can't meet all three due to time windows and travel. Let's try alternative: meet Jeffrey first, then Sarah, then maybe Brian not possible. Since Brian's window is limited.

Let's test meeting Sarah and Jeffrey both. Could we meet Sarah 4:00-5:00 at North Beach, then travel to Union Square 7 min (North Beach to Union Square = 7). Arrive 5:07, need 75 min meeting until 6:22, within Jeffrey's window (3-10). That works, meeting 5:07-6:22, that's 75 min. So we meet Sarah and Jeffrey, not Brian.

Could we also fit Brian earlier before 4pm? No, Brian's window starts 4pm.

Thus max friends possibly 2. Need to check also travel from start location to first meeting: start at Sunset District 9am, we can wait until appropriate time and travel.

We need to produce itinerary for best schedule (2 friends). Could there be schedule meeting Brian and Jeffrey (2 friends) as earlier scenario: Brian 4:00-5:15 (75 min), travel to Union Square 15 min arrive 5:30, meet Jeffrey 5:30-6:45 (75 min). That's 2 friends (Brian, Jeffrey). That's feasible. Which pair yields earlier finish? Both pairs finish similarly. Need not optimize finish, just maximize count. Both give 2 friends. Could we meet all three by splitting meeting times? Each need minimum continuous? It says "meet for a minimum of 60 minutes" could be cumulative? likely continuous. We'll assume continuous.

Thus best is 2 frie
```

## qwen / zebralogic / baseline / `zebralogic_grid_lgp-test-5x3-38`

Trace length: 17,358 characters. A full case split (G=2, 3, 4, ... with sub-cases), eliminating branches by contradiction until the unique solution is found. The program is a Z3 model.

```text
=2; C=5 -> T=4.
G-1 values: G=2->1;3->2;4->3;5->4.
K values 1..4.
P values 2..5.

Need all five child positions distinct. Let's enumerate by G and C.

Case G=2: F=2, M=1.
C cannot? C=2 conflict F? child T=1 conflict M=1. C=3 T=2 conflict F=2. C=5 T=4 ok. So C=5. Children used {1,2,4}. K must not 1,2,4 and K<Ph. K can 3. Then B=3. Ph >3 and distinct from hobbies: P? Hobbies used G=2, C=5, K=3. Remaining P,Ph in {1,4}. P cannot 1, so P=4, Ph=1. But K=3 < Ph=1 false. So no.

Case G=3: F=3, M=2.
C options: C=2 T=1 ok (children {1,2,3}); C=3 T=2 conflict M=2; C=5 T=4 ok.
- Subcase C=2: used {1,2,3}. K can 4 (not 1,2,3) or? K=4, Ph >4 -> Ph=5. Hobbies used G=3,C=2,K=4,Ph=5, remaining P=1 but P cannot 1. No.
- Subcase C=5: T=4, used {2,3,4}. K can 1. Ph >1. Hobbies used G=3,C=5,K=1. Remaining P,Ph in {2,4}. P can 2 or4, Ph other. Need K=1 < Ph true for both. Need names: P=2 or4.
   * P=2: S=2 (but M=2? Wait child S=P=2, but M=2 conflict! We didn't include P in children distinct. Need P not in {M,F,T,K}. For G=3,C=5 used child positions M=2,F=3,T=4,K=1. P cannot 2,3,4,1 => P=5. But P=5 not in remaining {2,4}. So no.
Actually all child positions distinct includes P. For G=3,C=5,K=1 used {1,2,3,4}, P must 5. But hobby Ph >1 and distinct from G=3,C=5,K=1, P=5 => Ph=2. Hobbies: P=5, Ph=2, K=1, G=3, C=5 conflict P and C both 5? Wait C=5, P=5 conflict. So no. Let's systematically: Hobbies distinct: P cannot G=3,C=5,K=1. P in 2..5 => P=2 or4. But child S=P cannot equal M=2 or T=4 or F=3 or K=1. So P=2 conflict M, P=4 conflict T. No.
Thus G=3 no.

Case G=4: F=4, M=3.
C options: C=2 T=1 ok; C=3 T=2 ok; C=5 T=4 conflict F=4.
- C=2: used {1,3,4}. K can 2 or5? K 1..4 not used => K=2. (K=5 not allowed). B=2. Ph >2. Hobbies used G=4,C=2,K=2? Wait C=2 and K=2 conflict hobbies! K=2 equals C=2, impossible. So no.
- C=3: T=2, used {2,3,4}. K can 1. Ph >1. Hobbies used G=4,C=3,K=1. Remaining P,Ph in {2,5}. P can 2 or5. Child S=P cannot equal T=2,M=3,F=4,K=1. So P=5. Then Ph=2. K=1<Ph=2 ok. Hobbies: H1=K, H2=Ph, H3=C, H4=G, H5=P. Children: H1=B, H2=T, H3=M, H4=F, H5=S.
Names: P=5 => Eric at P-1=4. Bob left Alice, Bob not H2, b in {1,3,4}? b !=2. Eric at 4, so Bob cannot 4? Names distinct, Bob at b, Alice b+1. b possibilities 1,3 (4 not because Eric; 2 disallowed). If b=1: Bob H1, Alice H2. Peter not H3. Remaining names Arnold,Peter for H3,H5? H4 Eric. Peter not H3 => Peter H5, Arnold H3. Valid. If b=3: Bob H3, Alice H4 but H4 Eric conflict. So only b=1. Solution: H1 Bob, child Bella, hobby knitting; H2 Alice, child Timothy, photography; H3 Arnold, child Meredith, cooking; H4 Eric,
```

## gpt / zebralogic / baseline / `zebralogic_grid_lgp-test-4x2-32`

Trace length: 8,301 characters. After writing the Z3 constraints it says "we could solve to verify", then enumerates Case 1–4 of (Arnold, Peter) positions by hand.

```text
Name, pet

Format: "House 1: Peter, dog" etc.

The problem example includes only name and other attributes; here we need name and pet. They said "show all attributes in the order specified by the problem headers." Headers are probably House, Name, Pet. So each row: "House i: Name, pet". That matches format.

Edge Cases: Ensure solution unique.

Let's compute manually: we could solve to verify. Use constraints.

We know Arnold has fish. So p_Arnold is fish house.

We have Abs(p_Arnold - p_Peter) == 2. So Peter is two houses away from Arnold.

Positions 1-4, distinct.

Also Eric is bird (pet bird) and not house 1. Alice not house 1. So p_Eric ≠1, p_Alice≠1.

Also dog is right of Alice.

Let's enumerate possibilities quickly.

We need distinct pet assignments: Arnold fish (1), Eric bird (0). Remaining pets for Peter and Alice: dog and cat in some order.

Now dog must be right of Alice. If Alice has dog then dog not right of Alice. So Alice cannot have dog. So Alice must have cat, and Peter must have dog. Good.

Thus pet assignments: Peter dog, Alice cat.

Now we need dog right of Alice: house(Peter) > house(Alice). Since Peter has dog.

Also distinct houses for names.

Now p_Arnold fish house. Let's consider possibilities for positions.

We need Abs(p_Arnold - p_Peter) == 2.

And p_Peter > p_Alice.

Also p_Eric not 1, p_Alice not 1.

Let's list all permutations of distinct positions 1-4 for Arnold, Peter, Eric, Alice.

Let’s denote A = p_Arnold, P = p_Peter, E = p_Eric, L = p_Alice (use L for Alice). Conditions:

- A != P, etc all distinct.
- |A - P| = 2.
- P > L.
- E != 1.
- L != 1.

Now consider possible pairs (A,P) with distance 2:

Possible (A,P): (1,3), (2,4), (3,1), (4,2). Since order matters (A first). Let's consider each.

Case1: A=1, P=3. Then remaining houses {2,4} for E and L. Need L !=1 (satisfied) and E !=1 (satisfied). Also P > L => 3 > L, so L can be 2 (since 4 would not satisfy). Choose L=2, then E=4. Check distinctness ok. Also L not 1, fine. So solution: Arnold house1, Peter house3, Alice house2, Eric house4.

Check clue: dog right of Alice => Peter house3 > Alice house2 OK.

All constraints satisfied.

Case2: A=2, P=4. Remaining houses {1,3} for E and L. Need L !=1, so L cannot be 1, thus L=3, E=1. But E cannot be 1 (Eric not first) -> violates. So discard.

Case3: A=3, P=1. But then Peter house1, but dog must be right of Alice, need P > L, i
```

## deepseek / zebralogic / caution_a / `zebralogic_grid_lgp-test-6x3-15`

Trace length: 72,272 characters. Under the cautionary prompt it still runs a case analysis (Peter=4 with Bob=1 or Bob=6, ...) and proves the solution unique, then notes "Code likely returns that."

```text
house1 doctor.
- Clue 9 Alice at2 left of cat: cat position >2. Cat cannot? Pet positions include dog4, rabbit3, fish at Bob, remaining positions for hamster,cat,bird among houses 1,5,6 and Bob's fish. If Bob=1, fish at1, cat must be >2 and could be5 or6 (3 rabbit,4 dog,1 fish). If Bob=6, fish at6, cat >2 could be? positions 3 rabbit,4 dog,6 fish, so only5? or1? no >2; so cat=5. Let's check.
- Hamster left of Eric, hamster not4. Need consider Bob/Eric order.

Case Peter=4, Bob=1, Eric=6, Alice=2? Names: Bob1, Alice2, Carol3, Peter4, Arnold5, Eric6. Fish at1. Pets remaining houses 2,3,4,5,6: dog4, rabbit3, fish1, plus hamster,cat,bird. Cat >2. Hamster left of Eric=6, not4, so hamster ∈? positions 1 fish,2,3 rabbit,4 dog,5; less than6 and not4 => 2 or5 (1 fish). Also lawyer=hamster.
  Occupations: teacher2, artist5. Doctor adjacent teacher at1 or3. Need see possible.
  If hamster=2, occ at2 would be lawyer, but occ at2 teacher, impossible. Thus hamster=5. Then cat? Remaining pets at2,6? Wait with fish1, dog4, rabbit3, hamster5, remaining cat,bird at2,6. Cat >2, so cat=6? But Eric at6 owns cat? no constraint. Then bird=2. Good. Occupation: if hamster at5, lawyer at5, but artist at5 (due Peter dog) conflict! Wait Peter=4 dog directly left artist -> occ_pos["artist"]=5. If hamster at5, lawyer=hamster -> occ at5=lawyer. Same house can't be artist and lawyer. Thus hamster cannot be5. Therefore Peter=4, Bob=1 impossible due occupations. What if cat at? no, hamster directly conflict. Good.
Case Peter=4, Bob=6, Eric=1, Alice=2? Names: Eric1, Alice2, Carol3, Peter4, Arnold5, Bob6. Fish at6. Pets: dog4, rabbit3, fish6, remaining cat,bird,hamster at1,2,5. Hamster not4, and left of Eric=1 impossible (hamster<1 none). So no.
Case Peter=4, Bob=6, Eric=?? if Bob=6, remaining Eric/Alice at1,2; Eric cannot2? Eric nurse, house2 teacher (clue teacher at2) so Eric not2; thus Eric=1, Alice=2 impossible due hamster left of Eric no. If Bob=1? no. So Peter=4 no solution. Thus only solution Peter=2, Bob=1, etc. It matches earlier.

Let's see if Peter=4 possible with Bob=6 and Eric? If Eric=1 no; if Eric=2 impossible. Thus none.
Thus unique solution as found. Code likely returns that.

Need maybe consider "doctor and teacher next to each other" could be interpreted as "doctor is next to teacher" not necessarily exactly adjacent? In logic puzzles "next to each other" means adjacent, ye
```

## qwen / calendar / baseline / `calendar_scheduling_example_206`

Trace length: 17,811 characters. After writing a slot-scanning program, it checks each half-hour slot against every participant by hand ("Let's manually list intervals").

```text
), (to_min(10,30), to_min(11,0)), (to_min(11,30), to_min(12,30)), (to_min(13,0), to_min(13,30)), (to_min(14,0), to_min(14,30)), (to_min(16,30), to_min(17,0))],
}

def conflicts(start, end):
    for iv in busy.values():
       for bs, be in iv:
          if start < be and bs < end:
             return False
    return True

solution = None
for s in range(max(work_start, margaret_earliest), work_end - duration + 1):
    e = s + duration
    if conflicts(s,e):
       solution = (day, to_str(s), to_str(e))
       break

print([solution[0], solution[1], solution[2]])
```

This prints. Need if no solution? guaranteed. Could avoid error. Fine.

But maybe they expect the code to parse the task text? The prompt says "You are given a constraint satisfaction problem (CSP) expressed in natural language... Formalize the variables and constraints from the text, then write a Python program that solves it directly rather than solving it yourself in prose." In these benchmark tasks, they expect code that encodes the specific problem and prints answer. Hardcoding is okay. But could there be hidden tests? They will run code? likely only this one. Need ensure exact final answer. Let's double-check all constraints.

Meeting duration half an hour between work hours 9:00 to 17:00. Usually can schedule at :00 and :30 only? If search minute, still earliest valid 15:30. If schedule can start at any minute, same. If only :00 or :30, same.

Check if "Margaret do not want to meet on Monday before 14:30" could mean the meeting must be entirely after 14:30, i.e. start >=14:30. If start 14:30 would end 15:00. If "before 14:30" as any part before, start >=14:30. OK.

Check if "existing schedule of each participant" includes all participants. Yes.

Let's manually list intervals:
9-9:30 Jacob, Margaret busy.
9:30-10:00? Jacob free, Margaret free, Mason busy 9-10, Stephen free, Shirley free -> Mason conflict.
10-10:30 Jacob busy 10-10:30, Mason free? Mason busy 9-10, 10:30-11, so free; etc.
10:30-11:00 Shirley busy, Jacob free? Jacob busy 10-10:30, 11-11:30, so free 10:30-11, but Mason busy 10:30-11, so conflict.
11-11:30 Jacob busy, Stephen free? Stephen busy 11:30-12, so 11-11:30 OK but Jacob conflict.
11:30-12 Stephen busy, Mason busy 11:30-12:30, Jacob busy? 11-11:30 only. Conflict.
12-12:30 Shirley busy, Mason busy, Stephen free? Stephen busy 12:30-13. Conflict.
12:30-13 Jacob busy 12:30-13:30, Stephen busy 12:30-13, Mason busy until 12:30, Margaret busy 10:30-12:30 ends. Conflict.
13-13:30 Jacob busy, Margaret busy 13-13:30, Mason busy 13-13:30, conflict.
13:30-14 all free? Jacob bus
```

## Note: misaligned judge outputs

`src/run_chunking.py` and `src/hardcoded/batch_judge.py` match Vertex batch results to examples by position, assuming the output keeps input order. It does not. In the stored `*_chunking.json` files, a 150-character passage from an example's chunks matches exactly one trace in 3,337 of 3,600 cases, and that trace is a different example's in 3,288 of them. So per-example solver-like fractions, and per-example hardcoded-judge verdicts, belong to other examples. Means over each 100-example file are unaffected, because the mix-up stays within a file. The local vLLM re-judge (`src/run_chunking_local.py`) zips outputs with their requests in order and is not affected.