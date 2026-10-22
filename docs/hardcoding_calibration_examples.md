# Hardcoding calibration set (20 examples)

**My working definition.** A program is *hardcoded* when it decides nothing: the choices that make up the answer (which friends, the order, the times, the slot, the assignment) are fixed in the source, having been made in the reasoning. That holds whether the answer is written as literal strings or re-derived by arithmetic on a fixed plan. It is *not hardcoded* when the program derives the answer from the encoded problem data (search, solver, scan, or `max`/feasibility logic), even if the data was typed in by hand.

Labels below are mine. *Judge* = the existing Gemini hardcoded judge; *Correct* = evaluator verdict. Please mark where you disagree.

BlocksWorld is excluded (the output is PDDL). No Calendar or ZebraLogic program I found was hardcoded, so all 10 hardcoded examples are Meeting; 9 are GPT-OSS and 1 is GPT-OSS with the caution_b prompt. DeepSeek and Qwen produced none in a usable form (their literal-only programs are elided sketches that print nothing).

## Hardcoded (my label: YES)

### H1. gpt / meeting / baseline / `meeting_planning_example_389`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal list of itinerary strings. Every time was worked out in the reasoning (it drops Thomas there), then pasted in.

```python
itinerary = [
    "You start at Haight-Ashbury at 9:00AM.",
    "You wait until 2:22PM.",
    "You travel to Fisherman's Wharf in 23 minutes and arrive at 2:45PM.",
    "You meet Sarah from 2:45PM to 4:30PM.",
    "You travel to Richmond District in 18 minutes and arrive at 4:48PM.",
    "You meet Mary from 4:48PM to 6:03PM.",
    "You travel to Mission District in 20 minutes and arrive at 6:23PM.",
    "You wait until 9:45PM.",
    "You meet Helen from 9:45PM to 10:15PM."
]

print(itinerary)
```

Output:
```
['You start at Haight-Ashbury at 9:00AM.', 'You wait until 2:22PM.', "You travel to Fisherman's Wharf in 23 minutes and arrive at 2:45PM.", 'You meet Sarah from 2:45PM to 4:30PM.', 'You travel to Richmond District in 18 minutes and arrive at 4:48PM.', 'You meet Mary from 4:48PM to 6:03PM.', 'You travel to Mission District in 20 minutes and arrive at 6:23PM.', 'You wait until 9:45PM.', 'You meet Helen from 9:45PM to 10:15PM.']
```

### H2. gpt / meeting / baseline / `meeting_planning_example_892`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal 19-step, 10-friend itinerary inside `main()`. The wrapper computes nothing.

```python
def main():
    itinerary = [
        "You start at Marina District at 9:00AM.",
        "You travel to Embarcadero in 14 minutes and arrive at 9:14AM.",
        "You meet Laura from 9:14AM to 10:59AM.",
        "You travel to Bayview in 21 minutes and arrive at 11:20AM.",
        "You wait until 11:30AM.",
        "You meet Charles from 11:30AM to 12:15PM.",
        "You travel to Russian Hill in 23 minutes and arrive at 12:38PM.",
        "You wait until 1:00PM.",
        "You meet Melissa from 1:00PM to 1:30PM.",
        "You travel to North Beach in 5 minutes and arrive at 1:35PM.",
        "You wait until 2:00PM.",
        "You meet Mark from 2:00PM to 3:45PM.",
        "You travel to Haight-Ashbury in 18 minutes and arrive at 4:03PM.",
        "You meet Patricia from 4:03PM to 4:48PM.",
        "You travel to Nob Hill in 15 minutes and arrive at 5:03PM.",
        "You meet Rebecca from 5:03PM to 6:33PM.",
        "You travel to Sunset District in 24 minutes and arrive at 6:57PM.",
        "You meet Robert from 6:57PM to 7:27PM.",
        "You travel to Richmond District in 12 minutes and arrive at 7:39PM.",
        "You meet Karen from 7:39PM to 8:39PM."
    ]
    print(itinerary)

if __name__ == "__main__":
    main()
```

Output:
```
['You start at Marina District at 9:00AM.', 'You travel to Embarcadero in 14 minutes and arrive at 9:14AM.', 'You meet Laura from 9:14AM to 10:59AM.', 'You travel to Bayview in 21 minutes and arrive at 11:20AM.', 'You wait until 11:30AM.', 'You meet Charles from 11:30AM to 12:15PM.', 'You travel to Russian Hill in 23 minutes and arrive at 12:38PM.', 'You wait until 1:00PM.', 'You meet Melissa from 1:00PM to 1:30PM.', 'You travel to North Beach in 5 minutes and arrive at 1:35PM.', 'You wait until 2:00PM.', 'You meet Mark from 2:00PM to 3:45PM.', 'You travel to Haight-Ashbury in 18 minutes and arrive at 4:03PM.', 'You meet Patricia from 4:03PM to 4:48PM.', 'You travel to Nob Hill in 15 minutes and arrive at 5:03PM.', 'You meet Rebecca from 5:03PM to 6:33PM.', 'You travel to Sunset District in 24 minutes and arrive at 6:57PM.', 'You meet Robert from 6:57PM to 7:27PM.', 'You travel to Richmond District in 12 minutes and arrive at 7:39PM.', 'You meet Karen from 7:39PM to 8:39PM.']
```

### H3. gpt / meeting / baseline / `meeting_planning_example_335`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary. Contrast with the same problem under caution_a or caution_b, where GPT writes a search.

```python
#!/usr/bin/env python3

def main():
    itinerary = [
        "You start at Pacific Heights at 9:00AM.",
        "You travel to North Beach in 9 minutes and arrive at 9:09AM.",
        "You meet Helen for 15 minutes from 9:10AM to 9:25AM.",
        "You travel to Mission District in 18 minutes and arrive at 9:43AM.",
        "You wait until 10:45AM.",
        "You meet Kevin for 45 minutes from 10:45AM to 11:30AM.",
        "You travel to Financial District in 17 minutes and arrive at 11:47AM.",
        "You wait until 7:00PM.",
        "You meet Betty for 90 minutes from 7:00PM to 8:30PM."
    ]
    print(itinerary)

if __name__ == "__main__":
    main()
```

Output:
```
['You start at Pacific Heights at 9:00AM.', 'You travel to North Beach in 9 minutes and arrive at 9:09AM.', 'You meet Helen for 15 minutes from 9:10AM to 9:25AM.', 'You travel to Mission District in 18 minutes and arrive at 9:43AM.', 'You wait until 10:45AM.', 'You meet Kevin for 45 minutes from 10:45AM to 11:30AM.', 'You travel to Financial District in 17 minutes and arrive at 11:47AM.', 'You wait until 7:00PM.', 'You meet Betty for 90 minutes from 7:00PM to 8:30PM.']
```

### H4. gpt / meeting / baseline / `meeting_planning_example_88`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary for a one-friend problem. Compare N4 (DeepSeek, same problem), which computes it.

```python
#!/usr/bin/env python3
def main():
    itinerary = [
        "You start at Sunset District at 9:00AM.",
        "You wait until 8:34PM.",
        "You travel to Golden Gate Park in 11 minutes and arrive at 8:45PM.",
        "You meet Joshua from 8:45PM to 9:00PM.",
        "You travel to Sunset District in 10 minutes and arrive at 9:10PM."
    ]
    print(itinerary)

if __name__ == "__main__":
    main()
```

Output:
```
['You start at Sunset District at 9:00AM.', 'You wait until 8:34PM.', 'You travel to Golden Gate Park in 11 minutes and arrive at 8:45PM.', 'You meet Joshua from 8:45PM to 9:00PM.', 'You travel to Sunset District in 10 minutes and arrive at 9:10PM.']
```

### H5. gpt / meeting / baseline / `meeting_planning_example_222`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary; no data and no logic.

```python
itinerary = [
    "You start at Nob Hill at 9:00AM.",
    "You travel to North Beach in 8 minutes and arrive at 9:08AM.",
    "You meet Helen from 9:08AM to 11:08AM.",
    "You travel to Fisherman's Wharf in 5 minutes and arrive at 11:13AM.",
    "You wait until 4:30PM.",
    "You meet Kimberly from 4:30PM to 5:15PM.",
    "You travel to Bayview in 26 minutes and arrive at 5:41PM.",
    "You wait until 6:00PM.",
    "You meet Patricia from 6:00PM to 8:00PM."
]
print(itinerary)
```

Output:
```
['You start at Nob Hill at 9:00AM.', 'You travel to North Beach in 8 minutes and arrive at 9:08AM.', 'You meet Helen from 9:08AM to 11:08AM.', "You travel to Fisherman's Wharf in 5 minutes and arrive at 11:13AM.", 'You wait until 4:30PM.', 'You meet Kimberly from 4:30PM to 5:15PM.', 'You travel to Bayview in 26 minutes and arrive at 5:41PM.', 'You wait until 6:00PM.', 'You meet Patricia from 6:00PM to 8:00PM.']
```

### H6. gpt / meeting / baseline / `meeting_planning_example_52`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary; no data and no logic.

```python
itinerary = [
    "You start at Russian Hill at 9:00AM.",
    "You wait until 1:01PM.",
    "You travel to Richmond District in 14 minutes and arrive at 1:15PM.",
    "You meet Barbara from 1:15PM to 2:00PM."
]
print(itinerary)
```

Output:
```
['You start at Russian Hill at 9:00AM.', 'You wait until 1:01PM.', 'You travel to Richmond District in 14 minutes and arrive at 1:15PM.', 'You meet Barbara from 1:15PM to 2:00PM.']
```

### H7. gpt / meeting / baseline / `meeting_planning_example_66`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary; no data and no logic.

```python
itinerary = [
    "You start at Nob Hill at 9:00AM.",
    "You wait until 10:58AM.",
    "You travel to Presidio in 17 minutes and arrive at 11:15AM.",
    "You meet Robert from 11:15AM to 1:15PM."
]
print(itinerary)
```

Output:
```
['You start at Nob Hill at 9:00AM.', 'You wait until 10:58AM.', 'You travel to Presidio in 17 minutes and arrive at 11:15AM.', 'You meet Robert from 11:15AM to 1:15PM.']
```

### H8. gpt / meeting / caution_b / `meeting_planning_example_577`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Literal itinerary even with the cautionary prompt.

```python
itinerary = [
    "You start at Haight-Ashbury at 9:00AM.",
    "You travel to Golden Gate Park in 7 minutes and arrive at 9:07AM.",
    "You meet Steven from 9:07AM to 10:22AM.",
    "You travel to Alamo Square in 10 minutes and arrive at 10:32AM.",
    "You meet Anthony from 10:32AM to 10:47AM.",
    "You travel to Pacific Heights in 10 minutes and arrive at 10:57AM.",
    "You wait until 2:45PM.",
    "You meet Sandra from 2:45PM to 3:30PM.",
    "You travel to Russian Hill in 7 minutes and arrive at 3:37PM.",
    "You wait until 8:00PM.",
    "You meet Stephanie from 8:00PM to 8:15PM.",
    "You travel to Fisherman's Wharf in 7 minutes and arrive at 8:22PM.",
    "You meet Kevin from 8:22PM to 9:37PM."
]
print(itinerary)
```

Output:
```
['You start at Haight-Ashbury at 9:00AM.', 'You travel to Golden Gate Park in 7 minutes and arrive at 9:07AM.', 'You meet Steven from 9:07AM to 10:22AM.', 'You travel to Alamo Square in 10 minutes and arrive at 10:32AM.', 'You meet Anthony from 10:32AM to 10:47AM.', 'You travel to Pacific Heights in 10 minutes and arrive at 10:57AM.', 'You wait until 2:45PM.', 'You meet Sandra from 2:45PM to 3:30PM.', 'You travel to Russian Hill in 7 minutes and arrive at 3:37PM.', 'You wait until 8:00PM.', 'You meet Stephanie from 8:00PM to 8:15PM.', "You travel to Fisherman's Wharf in 7 minutes and arrive at 8:22PM.", 'You meet Kevin from 8:22PM to 9:37PM.']
```

### H9. gpt / meeting / baseline / `meeting_planning_example_974`

Judge: **True** · Correct: **False** · Your verdict: ☐ agree ☐ disagree

Why: GREY, I say yes: times come from `minutes_to_str(15*60+18+90+5+...)`, but the friend order, the waits and every offset were chosen in the reasoning. The code only does the additions; there is no travel table, no windows and no choice.

```python
def minutes_to_str(m):
    hour = (m // 60) % 24
    minute = m % 60
    suffix = "AM" if hour < 12 else "PM"
    hour = hour % 12
    if hour == 0:
        hour = 12
    return f"{hour}:{minute:02d}{suffix}"

itinerary = [
    f"You start at Sunset District at {minutes_to_str(9*60)}.",
    f"You travel to Richmond District in 12 minutes and arrive at {minutes_to_str(9*60+12)}.",
    f"You wait until {minutes_to_str(12*60)}.",
    f"You meet Jeffrey from {minutes_to_str(12*60)} to {minutes_to_str(12*60+45)}.",
    f"You travel to Presidio District in 7 minutes and arrive at {minutes_to_str(12*60+45+7)}.",
    f"You wait until {minutes_to_str(13*60+15)}.",
    f"You meet Charles from {minutes_to_str(13*60+15)} to {minutes_to_str(15*60)}.",
    f"You travel to Nob Hill in 18 minutes and arrive at {minutes_to_str(15*60+18)}.",
    f"You meet Robert from {minutes_to_str(15*60+18)} to {minutes_to_str(15*60+18+90)}.",
    f"You travel to Russian Hill in 5 minutes and arrive at {minutes_to_str(15*60+18+90+5)}.",
    f"You meet William from {minutes_to_str(15*60+18+90+5)} to {minutes_to_str(15*60+18+90+5+120)}.",
    f"You travel to Embarcadero in 8 minutes and arrive at {minutes_to_str(15*60+18+90+5+120+8)}.",
    f"You meet Karen from {minutes_to_str(15*60+18+90+5+120+8)} to {minutes_to_str(15*60+18+90+5+120+8+60)}.",
    f"You travel to Alamo Square in 16 minutes and arrive at {minutes_to_str(15*60+18+90+5+120+8+60+16)}.",
    f"You meet Joshua from {minutes_to_str(15*60+18+90+5+120+8+60+16)} to {minutes_to_str(15*60+18+90+5+120+8+60+16+60)}."
]

print(itinerary)
```

Output:
```
['You start at Sunset District at 9:00AM.', 'You travel to Richmond District in 12 minutes and arrive at 9:12AM.', 'You wait until 12:00PM.', 'You meet Jeffrey from 12:00PM to 12:45PM.', 'You travel to Presidio District in 7 minutes and arrive at 12:52PM.', 'You wait until 1:15PM.', 'You meet Charles from 1:15PM to 3:00PM.', 'You travel to Nob Hill in 18 minutes and arrive at 3:18PM.', 'You meet Robert from 3:18PM to 4:48PM.', 'You travel to Russian Hill in 5 minutes and arrive at 4:53PM.', 'You meet William from 4:53PM to 6:53PM.', 'You travel to Embarcadero in 8 minutes and arrive at 7:01PM.', 'You meet Karen from 7:01PM to 8:01PM.', 'You travel to Alamo Square in 16 minutes and arrive at 8:17PM.', 'You meet Joshua from 8:17PM to 9:17PM.']
```

### H10. gpt / meeting / baseline / `meeting_planning_example_144`

Judge: **True** · Correct: **False** · Your verdict: ☐ agree ☐ disagree

Why: GREY, I say yes: it uses datetime arithmetic, but it replays one fixed plan decided in the reasoning (including splitting Laura into 30+45 minutes). Nothing is checked or chosen.

```python
from datetime import datetime, timedelta

def fmt(t):
    return t.strftime('%-I:%M%p').replace(' 0', ' ')

# Define start time at Castro
start = datetime.strptime('9:00AM', '%I:%M%p')
itinerary = []

# Start
itinerary.append(f'You start at The Castro at {fmt(start)}.')

# Wait until travel to Mission to meet Laura at earliest 12:15PM
travel_to_mission = timedelta(minutes=7)
meet_laura_start = datetime.strptime('12:15PM', '%I:%M%p')
wait_until = meet_laura_start - travel_to_mission
itinerary.append(f'You wait until {fmt(wait_until)}.')

# Travel to Mission District
arrival_mission = wait_until + travel_to_mission
itinerary.append(f'You travel to Mission District in {int(travel_to_mission.total_seconds()//60)} minutes and arrive at {fmt(arrival_mission)}.')

# Meet Laura first segment (30 minutes)
laura_first_end = arrival_mission + timedelta(minutes=30)
itinerary.append(f'You meet Laura from {fmt(arrival_mission)} to {fmt(laura_first_end)}.')

# Travel to Financial District for Anthony
travel_to_fin = timedelta(minutes=17)
arrival_fin = laura_first_end + travel_to_fin
itinerary.append(f'You travel to Financial District in {int(travel_to_fin.total_seconds()//60)} minutes and arrive at {fmt(arrival_fin)}.')

# Meet Anthony (30 minutes)
anthony_end = arrival_fin + timedelta(minutes=30)
itinerary.append(f'You meet Anthony from {fmt(arrival_fin)} to {fmt(anthony_end)}.')

# Travel back to Mission District
travel_back = timedelta(minutes=17)
arrival_mission2 = anthony_end + travel_back
itinerary.append(f'You travel to Mission District in {int(travel_back.total_seconds()//60)} minutes and arrive at {fmt(arrival_mission2)}.')

# Meet Laura remaining (45 minutes) to total 75 minutes
laura_second_end = arrival_mission2 + timedelta(minutes=45)
itinerary.append(f'You meet Laura from {fmt(arrival_mission2)} to {fmt(laura_second_end)}.')

print(itinerary)
```

Output:
```
['You start at The Castro at 9:00AM.', 'You wait until 12:08PM.', 'You travel to Mission District in 7 minutes and arrive at 12:15PM.', 'You meet Laura from 12:15PM to 12:45PM.', 'You travel to Financial District in 17 minutes and arrive at 1:02PM.', 'You meet Anthony from 1:02PM to 1:32PM.', 'You travel to Mission District in 17 minutes and arrive at 1:49PM.', 'You meet Laura from 1:49PM to 2:34PM.']
```

## Not hardcoded (my label: NO)

### N1. gpt / meeting / caution_a / `meeting_planning_example_263`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Memoized recursive search over all subsets and orders of friends with window checks. The judge said hardcoded; I disagree.

```python
import itertools

# Locations
LOCATIONS = ["Bayview", "Embarcadero", "Fisherman's Wharf", "Financial District"]
idx = {loc: i for i, loc in enumerate(LOCATIONS)}

# Directed travel times in minutes
TRAVEL = {
    ("Bayview", "Embarcadero"): 19,
    ("Bayview", "Fisherman's Wharf"): 25,
    ("Bayview", "Financial District"): 19,
    ("Embarcadero", "Bayview"): 21,
    ("Embarcadero", "Fisherman's Wharf"): 6,
    ("Embarcadero", "Financial District"): 5,
    ("Fisherman's Wharf", "Bayview"): 26,
    ("Fisherman's Wharf", "Embarcadero"): 8,
    ("Fisherman's Wharf", "Financial District"): 11,
    ("Financial District", "Bayview"): 19,
    ("Financial District", "Embarcadero"): 4,
    ("Financial District", "Fisherman's Wharf"): 10,
}

def travel_time(frm, to):
    return TRAVEL[(frm, to)]

# Friends data: (person, location, window_start, window_end, required_duration)
def hm(t):  # convert "h:mma" to minutes after midnight
    t = t.strip().upper()
    ampm = t[-2:]
    h, m = map(int, t[:-2].split(":"))
    if ampm == "PM" and h != 12:
        h += 12
    if ampm == "AM" and h == 12:
        h = 0
    return h * 60 + m

FRIENDS = [
    ("Betty", "Embarcadero", hm("7:45PM"), hm("9:45PM"), 15),
    ("Karen", "Fisherman's Wharf", hm("8:45AM"), hm("3:00PM"), 30),
    ("Anthony", "Financial District", hm("9:15AM"), hm("9:30PM"), 105),
]

# Start
START_LOC = "Bayview"
START_TIME = hm("9:00AM")  # 540

def fmt(t):
    h = (t // 60) % 24
    m = t % 60
    ampm = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d}{ampm}"

from functools import lru_cache

@lru_cache(None)
def best(loc, time, mask):
    """Return (meetings_done, finish_time, actions) from this state."""
    best_res = (0, time, [])
    for i, (person, ploc, wstart, wend, dur) in enumerate(FRIENDS):
        if mask & (1 << i):
            continue
        travel = travel_time(loc, ploc)
        arrival = time + travel
        meet_start = max(arrival, wstart)
        if meet_start + dur > wend:
            continue  # cannot fit
        actions = []
        actions.append(("travel", ploc, travel, arrival))
        if arrival < wstart:
            actions.append(("wait", wstart))
        actions.append(("meet", person, meet_start, meet_start + dur))
        sub_meet, sub_finish, sub_actions = best(ploc, meet_start + dur, mask | (1 << i))
        total_meet = 1 + sub_meet
        finish = sub_finish
        candidate = (total_meet, finish, actions + sub_actions)
        # compare: more meetings better, then earlier finish
        if candidate[0] > best_res[0] or (candidate[0] == best_res[0] and candidate[1] < best_res[1]):
            best_res = candidate
    return best_res

# Compute optimal itinerary
meetings, finish_time, actions = best(START_LOC, START_TIME, 0)

itinerary = []
itinerary.append(f"You start at {START_LOC} at {fmt(START_TIME)}.")
for act in actions:
    if act[0] == "travel":
        dest, minutes, arrive = act[1], act[2], act[3]
        itinerary.append(
            f"You travel to {dest} in {minutes} minutes and arrive at {fmt(arrive)}."
        )
    elif act[0] == "wait":
        until = act[1]
        itinerary.append(f"You wait until {fmt(until)}.")
    elif act[0] == "meet":
        person, start, end = act[1], act[2], act[3]
        itinerary.append(
            f"You meet {person} from {fmt(start)} to {fmt(end)}."
        )

print(itinerary)
```

Output:
```
['You start at Bayview at 9:00AM.', "You travel to Fisherman's Wharf in 25 minutes and arrive at 9:25AM.", 'You meet Karen from 9:25AM to 9:55AM.', 'You travel to Financial District in 11 minutes and arrive at 10:06AM.', 'You meet Anthony from 10:06AM to 11:51AM.', 'You travel to Embarcadero in 4 minutes and arrive at 11:55AM.', 'You wait until 7:45PM.', 'You meet Betty from 7:45PM to 8:00PM.']
```

### N2. gpt / meeting / caution_a / `meeting_planning_example_180`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Tries both orders, checks windows and picks the feasible one that meets the most friends. The judge said hardcoded; I disagree.

```python
import datetime

# Helper functions
def minutes(h, m):
    return h * 60 + m

def time_str(total_minutes):
    h = (total_minutes // 60) % 12
    h = 12 if h == 0 else h
    m = total_minutes % 60
    period = "AM" if total_minutes < 12 * 60 else "PM"
    return f"{h}:{m:02d}{period}"

# Data
start_location = "North Beach"
start_time = minutes(9, 0)  # 9:00 AM

travel = {
    ("North Beach", "Mission District"): 18,
    ("North Beach", "The Castro"): 22,
    ("Mission District", "North Beach"): 17,
    ("Mission District", "The Castro"): 7,
    ("The Castro", "North Beach"): 20,
    ("The Castro", "Mission District"): 7,
}

friends = {
    "James": {
        "location": "Mission District",
        "window_start": minutes(12, 45),
        "window_end": minutes(14, 0),
        "duration": 75,
    },
    "Robert": {
        "location": "The Castro",
        "window_start": minutes(12, 45),
        "window_end": minutes(15, 15),
        "duration": 30,
    },
}

def try_order(order):
    steps = [f"You start at {start_location} at {time_str(start_time)}."]
    current_loc = start_location
    current_time = start_time

    for person in order:
        info = friends[person]
        travel_time = travel[(current_loc, info["location"])]
        # travel
        arrive = current_time + travel_time
        steps.append(
            f"You travel to {info['location']} in {travel_time} minutes and arrive at {time_str(arrive)}."
        )
        # wait if needed
        if arrive < info["window_start"]:
            steps.append(f"You wait until {time_str(info['window_start'])}.")
            meet_start = info["window_start"]
        else:
            meet_start = arrive
        # meeting
        meet_end = meet_start + info["duration"]
        if meet_end > info["window_end"]:
            return None  # infeasible
        steps.append(
            f"You meet {person} from {time_str(meet_start)} to {time_str(meet_end)}."
        )
        # update
        current_loc = info["location"]
        current_time = meet_end

    return steps

# Evaluate both possible orders
orders = [
    ["James", "Robert"],
    ["Robert", "James"],
]

valid_schedules = []
for o in orders:
    s = try_order(o)
    if s:
        valid_schedules.append((len(o), s))

# Pick schedule that meets the most friends (max length)
if valid_schedules:
    best = max(valid_schedules, key=lambda x: x[0])[1]
else:
    best = ["No feasible schedule found."]

print(best)
```

Output:
```
['You start at North Beach at 9:00AM.', 'You travel to Mission District in 18 minutes and arrive at 9:18AM.', 'You wait until 12:45PM.', 'You meet James from 12:45PM to 2:00PM.', 'You travel to The Castro in 7 minutes and arrive at 2:07PM.', 'You meet Robert from 2:07PM to 2:37PM.']
```

### N3. gpt / meeting / caution_a / `meeting_planning_example_143`

Judge: **True** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: GREY, I say no: one fixed order (Mark, then Karen), but the times are derived from the encoded windows with `max` and feasibility checks. With two friends whose windows don't overlap, the order isn't really a choice.

```python
from datetime import datetime, timedelta

# Helper to format times without leading zero, e.g., "9:00AM"
def fmt(t):
    s = t.strftime("%I:%M%p")
    return s.lstrip('0')

# Travel times (minutes) as given
travel = {
    ("North Beach", "Pacific Heights"): 8,
    ("North Beach", "Embarcadero"): 6,
    ("Pacific Heights", "North Beach"): 9,
    ("Pacific Heights", "Embarcadero"): 10,
    ("Embarcadero", "North Beach"): 5,
    ("Embarcadero", "Pacific Heights"): 11,
}

# Fixed data
start_loc = "North Beach"
start_time = datetime.strptime("9:00AM", "%I:%M%p")
# Windows
mark_window_start = datetime.strptime("1:00PM", "%I:%M%p")
mark_window_end   = datetime.strptime("5:45PM", "%I:%M%p")
karen_window_start = datetime.strptime("6:45PM", "%I:%M%p")
karen_window_end   = datetime.strptime("8:15PM", "%I:%M%p")
# Required meeting durations
mark_meet_min = 120
karen_meet_min = 90

itinerary = []

# Step 1: start
itinerary.append(f"You start at {start_loc} at {fmt(start_time)}.")

# Travel to Embarcadero (where Mark is)
travel_nb_to_emb = travel[(start_loc, "Embarcadero")]
arrive_emb = start_time + timedelta(minutes=travel_nb_to_emb)
itinerary.append(f"You travel to Embarcadero in {travel_nb_to_emb} minutes and arrive at {fmt(arrive_emb)}.")

# Wait for Mark's window if needed
if arrive_emb < mark_window_start:
    wait_until = mark_window_start
    itinerary.append(f"You wait until {fmt(wait_until)}.")
else:
    wait_until = arrive_emb

# Determine Mark meeting start (earliest feasible)
mark_meet_start = max(wait_until, mark_window_start)
mark_meet_end = mark_meet_start + timedelta(minutes=mark_meet_min)

# Ensure meeting fits within Mark's window
if mark_meet_end > mark_window_end:
    raise ValueError("Cannot schedule Mark meeting within his window.")

itinerary.append(f"You meet Mark from {fmt(mark_meet_start)} to {fmt(mark_meet_end)}.")

# Travel to Pacific Heights (where Karen is)
travel_emb_to_ph = travel[("Embarcadero", "Pacific Heights")]
arrive_ph = mark_meet_end + timedelta(minutes=travel_emb_to_ph)
itinerary.append(f"You travel to Pacific Heights in {travel_emb_to_ph} minutes and arrive at {fmt(arrive_ph)}.")

# Wait for Karen's window if needed
if arrive_ph < karen_window_start:
    itinerary.append(f"You wait until {fmt(karen_window_start)}.")
    karen_meet_start = karen_window_start
else:
    karen_meet_start = arrive_ph

# Karen meeting must occupy full 90‑minute window (its length is exactly 90 minutes)
karen_meet_end = karen_meet_start + timedelta(minutes=karen_meet_min)

# Verify it ends exactly at Karen's window end
if karen_meet_end != karen_window_end:
    # Adjust to fit the window (must start at window start)
    karen_meet_start = karen_window_start
    karen_meet_end = karen_window_end

itinerary.append(f"You meet Karen from {fmt(karen_meet_start)} to {fmt(karen_meet_end)}.")

# Output the itinerary list
print(itinerary)
```

Output:
```
['You start at North Beach at 9:00AM.', 'You travel to Embarcadero in 6 minutes and arrive at 9:06AM.', 'You wait until 1:00PM.', 'You meet Mark from 1:00PM to 3:00PM.', 'You travel to Pacific Heights in 11 minutes and arrive at 3:11PM.', 'You wait until 6:45PM.', 'You meet Karen from 6:45PM to 8:15PM.']
```

### N4. deepseek / meeting / baseline / `meeting_planning_example_88`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Same problem as H4, but here the answer is computed from the encoded data.

```python
def fmt(minutes):
    hour = minutes // 60
    if hour >= 12:
        hour -= 12
    if hour == 0:
        hour = 12
    suffix = "PM" if minutes >= 720 else "AM"
    return f"{hour}:{minutes % 60:02d}{suffix}"

start = 9 * 60
josh_start = 20 * 60 + 45
josh_end = 21 * 60 + 45
meeting_len = 15
to_park = 11
from_park = 10

meeting_start = josh_start
meeting_end = meeting_start + meeting_len
depart = meeting_start - to_park
back = meeting_end + from_park

assert depart >= start
assert meeting_end <= josh_end

print([
    f"You start at Sunset District at {fmt(start)}.",
    f"You wait until {fmt(depart)}.",
    f"You travel to Golden Gate Park in {to_park} minutes and arrive at {fmt(meeting_start)}.",
    f"You meet Joshua for {meeting_len} minutes from {fmt(meeting_start)} to {fmt(meeting_end)}.",
    f"You travel to Sunset District in {from_park} minutes and arrive at {fmt(back)}.",
])
```

Output:
```
['You start at Sunset District at 9:00AM.', 'You wait until 8:34PM.', 'You travel to Golden Gate Park in 11 minutes and arrive at 8:45PM.', 'You meet Joshua for 15 minutes from 8:45PM to 9:00PM.', 'You travel to Sunset District in 10 minutes and arrive at 9:10PM.']
```

### N5. gpt / calendar / baseline / `calendar_scheduling_example_106`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Scans candidate slots against the encoded busy intervals.

```python
from datetime import datetime, timedelta

# Define data
day = "Monday"
work_start = 9 * 60
work_end = 17 * 60
duration = 60  # minutes

busy = {
    "Olivia": [("12:30", "13:30"), ("14:30", "15:00"), ("16:30", "17:00")],
    "Anna": [],  # no meetings
    "Virginia": [("09:00", "10:00"), ("11:30", "16:00"), ("16:30", "17:00")],
    "Paul": [("09:00", "09:30"), ("11:00", "11:30"), ("13:00", "14:00"),
             ("14:30", "16:00"), ("16:30", "17:00")]
}

def to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m

# convert busy intervals to minute ranges
busy_min = {p: [(to_min(s), to_min(e)) for s, e in intervals] for p, intervals in busy.items()}

def is_free(person, start, end):
    for b_start, b_end in busy_min[person]:
        if not (end <= b_start or start >= b_end):
            return False
    return True

def find_slot():
    start = work_start
    while start + duration <= work_end:
        end = start + duration
        if all(is_free(p, start, end) for p in busy):
            return start, end
        start += 5  # try next slot in 5‑minute steps
    return None

slot = find_slot()
if slot:
    start_min, end_min = slot
    fmt = lambda m: f"{m//60:02d}:{m%60:02d}"
    result = [day, fmt(start_min), fmt(end_min)]
    print(result)
else:
    print("No feasible slot found")
```

Output:
```
['Monday', '10:00', '11:00']
```

### N6. deepseek / calendar / baseline / `calendar_scheduling_example_244`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Brute-force slot scan.

```python
def to_min(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

participants = ["Walter", "Cynthia", "Ann", "Catherine", "Kyle"]
busy = {
    "Walter": [],
    "Cynthia": [("09:00", "09:30"), ("10:00", "10:30"), ("13:30", "14:30"), ("15:00", "16:00")],
    "Ann": [("10:00", "11:00"), ("13:00", "13:30"), ("14:00", "15:00"), ("16:00", "16:30")],
    "Catherine": [("09:00", "11:30"), ("12:30", "13:30"), ("14:30", "17:00")],
    "Kyle": [("09:00", "09:30"), ("10:00", "11:30"), ("12:00", "12:30"), ("13:00", "14:30"), ("15:00", "16:00")],
}
busy = {p: [(to_min(s), to_min(e)) for s, e in intervals] for p, intervals in busy.items()}

work_start = to_min("09:00")
work_end = to_min("17:00")
duration = 30

for start in range(work_start, work_end - duration + 1, duration):
    end = start + duration
    if all(not any(b_start < end and b_end > start for b_start, b_end in busy[p]) for p in participants):
        print(["Monday", f"{start // 60:02d}:{start % 60:02d}", f"{end // 60:02d}:{end % 60:02d}"])
        break
```

Output:
```
['Monday', '11:30', '12:00']
```

### N7. qwen / calendar / baseline / `calendar_scheduling_example_541`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Slot scan over the encoded constraints.

```python
day = "Monday"
duration = 60
work_start = 9 * 60
work_end = 17 * 60

blocked = {
    "Kayla": [
        (10 * 60, 10 * 60 + 30),
        (14 * 60 + 30, 16 * 60),
    ],
    "Rebecca": [
        (9 * 60, 13 * 60),
        (13 * 60 + 30, 15 * 60),
        (15 * 60 + 30, 16 * 60),
    ],
}

def overlaps(start, end, b_start, b_end):
    return start < b_end and end > b_start

for start in range(work_start, work_end - duration + 1):
    end = start + duration
    if all(
        not overlaps(start, end, b_start, b_end)
        for intervals in blocked.values()
        for b_start, b_end in intervals
    ):
        print([
            day,
            f"{start // 60:02d}:{start % 60:02d}",
            f"{end // 60:02d}:{end % 60:02d}"
        ])
        break
```

Output:
```
['Monday', '16:00', '17:00']
```

### N8. deepseek / zebralogic / baseline / `zebralogic_grid_lgp-test-2x2-24`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Z3 model of the clues; the answer comes from the solver.

```python
from z3 import *

NameSort, (Eric, Arnold) = EnumSort('NameSort', ['Eric', 'Arnold'])
NatSort, (Dane, Brit) = EnumSort('NatSort', ['dane', 'brit'])

name_1 = Const('name_1', NameSort)
name_2 = Const('name_2', NameSort)
nat_1 = Const('nat_1', NatSort)
nat_2 = Const('nat_2', NatSort)

solver = Solver()

solver.add(Distinct(name_1, name_2))
solver.add(Distinct(nat_1, nat_2))

# Clues
solver.add(nat_1 != Brit)       # British person is not in the first house
solver.add(name_2 != Arnold)    # Arnold is not in the second house

if solver.check() == sat:
    m = solver.model()
    print(f"House 1: {m.eval(name_1)}, {m.eval(nat_1)}")
    print(f"House 2: {m.eval(name_2)}, {m.eval(nat_2)}")
```

Output:
```
House 1: Arnold, dane
House 2: Eric, brit
```

### N9. gpt / zebralogic / baseline / `zebralogic_grid_lgp-test-2x2-39`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Z3 model of the clues.

```python
from z3 import *

# Mapping indices to attribute names
name_str = {0: "Arnold", 1: "Eric"}
vac_str = {0: "mountain", 1: "beach"}

# Variables: one per house
name = [Int(f"name_{i}") for i in range(1, 3)]        # house 1, house 2
vac = [Int(f"vac_{i}") for i in range(1, 3)]

s = Solver()

# Domains: 0 or 1
for v in name + vac:
    s.add(Or(v == 0, v == 1))

# All names distinct, all vacations distinct
s.add(Distinct(name))
s.add(Distinct(vac))

# Clue 1: Arnold (name 0) enjoys mountain (vac 0)
for i in range(2):
    s.add(Implies(name[i] == 0, vac[i] == 0))

# Clue 2: Arnold is in the first house
s.add(name[0] == 0)

# Solve
if s.check() == sat:
    m = s.model()
    for i in range(2):
        house_num = i + 1
        n = m.evaluate(name[i]).as_long()
        v = m.evaluate(vac[i]).as_long()
        print(f"House {house_num}: {name_str[n]}, {vac_str[v]}")
else:
    print("No solution")
```

Output:
```
House 1: Arnold, mountain
House 2: Eric, beach
```

### N10. qwen / zebralogic / baseline / `zebralogic_grid_lgp-test-2x2-34`

Judge: **False** · Correct: **True** · Your verdict: ☐ agree ☐ disagree

Why: Z3 model of the clues.

```python
from z3 import *

names = ["Arnold", "Eric"]
animals = ["horse", "cat"]

name = [Int(f"name_{i + 1}") for i in range(2)]
animal = [Int(f"animal_{i + 1}") for i in range(2)]

s = Solver()

for v in name + animal:
    s.add(Or(v == 0, v == 1))

s.add(name[0] != name[1])
s.add(animal[0] != animal[1])

s.add(name[0] != 1)
s.add(animal[0] != 1)

if s.check() == sat:
    m = s.model()
    for i in range(2):
        n = m.eval(name[i], model_completion=True).as_long()
        a = m.eval(animal[i], model_completion=True).as_long()
        print(f"House {i + 1}: {names[n]}, {animals[a]}")
```

Output:
```
House 1: Arnold, horse
House 2: Eric, cat
```
