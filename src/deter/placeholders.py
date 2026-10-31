"""Replace the concrete values of a Calendar or Meeting Planning problem with placeholders.

The model sees only the placeholder text. The program gets the values at run time: the executor
defines a dict VALUES (placeholder name -> value) before the program's own code
(values_preamble). Placeholder kinds:
  Calendar: Person<i> (participant), Day<i> (weekday), T<i> (clock time, "H:MM" 24-hour),
            D1 (meeting duration, minutes)
  Meeting:  Person<i> (friend), L<i> (location), T<i> (clock time, "H:MMAM"/"H:MMPM"),
            D<i> (minimum meeting length, minutes), TRAVEL[a][b] (minutes from L<a> to L<b>)
Each distinct value gets one placeholder. T and D numbers are shuffled (seeded by the problem id),
so their order says nothing about the values; Person, Day and L are numbered by first appearance.

Every conversion records, for each placeholder, the surface string it replaced, so that
restore() gives back the original text exactly (checked by scripts/build_placeholders.py).
"""

import random
import re

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CAL_DURATIONS = {"half an hour": 30, "one hour": 60}

CAL_TASK = re.compile(r"schedule a meeting for (.+?) for (half an hour|one hour) between")
CAL_TIME = re.compile(r"\b\d{1,2}:\d{2}\b")
MEET_TIME = re.compile(r"\b\d{1,2}:\d{2}(?:AM|PM)\b")
MEET_FRIEND = re.compile(r"(?:^|\. )([A-Z][a-z]+) will be at ")
MEET_MIN = re.compile(r"for a minimum of (\d+) minutes")
TRAVEL_LINE = re.compile(r"^(.+?) to (.+?): (\d+)\.$")


def _word(s: str) -> re.Pattern:
    return re.compile(r"(?<![\w'])" + re.escape(s) + r"(?!\w)")


def _sub_all(text: str, mapping: dict) -> str:
    """Replace each key of mapping (surface -> placeholder) as a whole word, longest first."""
    for surface in sorted(mapping, key=len, reverse=True):
        text = _word(surface).sub(mapping[surface], text)
    return text


def _shuffled_names(prefix: str, surfaces: list, rng: random.Random) -> dict:
    nums = list(range(1, len(surfaces) + 1))
    rng.shuffle(nums)
    return {s: f"{prefix}{n}" for s, n in zip(surfaces, nums)}


def _ordered_names(prefix: str, surfaces: list) -> dict:
    return {s: f"{prefix}{i}" for i, s in enumerate(surfaces, 1)}


def _unique(seq):
    return list(dict.fromkeys(seq))


def convert_calendar(problem: str, seed: str) -> dict:
    rng = random.Random(seed)
    head, sep, task = problem.rpartition("TASK:")
    m = CAL_TASK.search(task)
    people = re.split(r", | and ", m.group(1))
    days = [d for d in WEEKDAYS if _word(d).search(task)]
    times = _unique(CAL_TIME.findall(task))

    people_map = _ordered_names("Person", people)
    day_map = _ordered_names("Day", days)
    time_map = _shuffled_names("T", times, rng)
    dur_map = {m.group(2): "D1"}

    # Times and the duration first (their surfaces contain no names), then names and days
    out = CAL_TIME.sub(lambda t: time_map[t.group(0)], task)
    out = out.replace(f" for {m.group(2)} between", " for D1 between", 1)
    out = _sub_all(out, {**people_map, **day_map})

    surfaces = {v: k for k, v in {**people_map, **day_map, **time_map, **dur_map}.items()}
    values = {**{v: k for k, v in {**people_map, **day_map, **time_map}.items()},
              "D1": CAL_DURATIONS[m.group(2)]}
    return {"problem": head + sep + out, "values": values, "surfaces": surfaces}


def convert_meeting(problem: str, seed: str) -> dict:
    rng = random.Random(seed)
    head, rest = problem.split("Travel distances (in minutes):")
    travel_block, cons = rest.split("CONSTRAINTS:")
    travel = [TRAVEL_LINE.match(line.strip()).groups() for line in travel_block.strip().splitlines()]
    locations = _unique([a for a, _, _ in travel] + [b for _, b, _ in travel])
    friends = _unique(MEET_FRIEND.findall(cons))
    times = _unique(MEET_TIME.findall(cons))
    minimums = _unique(MEET_MIN.findall(cons))

    loc_map = _ordered_names("L", locations)
    friend_map = _ordered_names("Person", friends)
    time_map = _shuffled_names("T", times, rng)
    dur_map = _shuffled_names("D", minimums, rng)

    out = MEET_TIME.sub(lambda t: time_map[t.group(0)], cons)
    out = MEET_MIN.sub(lambda d: f"for a minimum of {dur_map[d.group(1)]} minutes", out)
    out = _sub_all(out, {**loc_map, **friend_map})

    loc_list = ", ".join(loc_map.values())
    travel_text = (f" TRAVEL[a][b] is the travel time from location a to location b, for every "
                   f"ordered pair of distinct locations among {loc_list}.\n\n")
    text = head + "Travel distances (in minutes):" + travel_text + "CONSTRAINTS:" + out

    values = {v: k for k, v in {**loc_map, **friend_map, **time_map}.items()}
    values.update({ph: int(s) for s, ph in dur_map.items()})
    values["TRAVEL"] = {}
    for a, b, minutes in travel:
        values["TRAVEL"].setdefault(loc_map[a], {})[loc_map[b]] = int(minutes)

    surfaces = {v: k for k, v in {**loc_map, **friend_map, **time_map, **dur_map}.items()}
    surfaces["__travel_text__"] = travel_text
    surfaces["__travel_block__"] = travel_block
    return {"problem": text, "values": values, "surfaces": surfaces}


CONVERTERS = {"calendar": convert_calendar, "meeting": convert_meeting}


def convert(task: str, problem: str, seed: str) -> dict:
    """Return {"problem": placeholder text, "values": VALUES dict, "surfaces": for restore()}."""
    return CONVERTERS[task](problem, seed)


def restore(task: str, converted: dict) -> str:
    """Undo convert(): put each placeholder's original surface string back."""
    surfaces = dict(converted["surfaces"])
    text = converted["problem"]
    if task == "meeting":
        text = text.replace(surfaces.pop("__travel_text__"), surfaces.pop("__travel_block__"), 1)
    if task == "calendar":
        text = text.replace(" for D1 between", f" for {surfaces.pop('D1')} between", 1)
    return re.sub(r"\b(?:Person|Day|T|L|D)\d+\b", lambda m: surfaces.get(m.group(0), m.group(0)), text)


def leaked_values(task: str, converted: dict) -> list:
    """Concrete values still visible in the placeholder text (should be none)."""
    text = converted["problem"].rpartition("TASK:")[2] if task == "calendar" else \
        converted["problem"].split("Travel distances (in minutes):")[1]
    leaks = []
    for name, value in converted["values"].items():
        if name != "TRAVEL" and re.search(r"\b" + re.escape(str(value)) + r"\b", text):
            leaks.append(f"{name}={value}")
    leaks += [d for d in WEEKDAYS if _word(d).search(text)]
    leaks += re.findall(r"(?<![A-Za-z\d])\d+(?![\d])", re.sub(r"\b(?:Person|Day|T|L|D)\d+\b", "", text))
    return leaks


def values_preamble(values: dict) -> str:
    """Python source that defines VALUES, prepended to the program before it runs."""
    return f"VALUES = {values!r}\n\n"
