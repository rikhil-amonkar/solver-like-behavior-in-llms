"""
Meeting planning constraint evaluation (Python task).

Simulates the itinerary output format against meeting planning constraints:
['You start at Richmond District at 9:00AM.',
 'You travel to Financial District in 22 minutes and arrive at 9:22AM.',
 'You wait until 5:15PM.',
 'You meet Betty for 60 minutes from 5:15PM to 6:15PM.']

A plan is valid if every step parses and is consistent with the start
location/time, the travel-time table, and each friend's location, availability
window and minimum meeting duration. Because the task asks to meet as many
friends as possible, a valid plan is only correct if it meets at least as many
friends as the golden solution.
"""

import re
from typing import Optional, Tuple

TIME = r"(\d{1,2}:\d{2}\s*[AaPp][Mm])"
START_RE = re.compile(rf"^You start at (.+?) at {TIME}\.?$")
TRAVEL_RE = re.compile(rf"^You travel (?:from (.+?) )?to (.+?) in (\d+) minutes? and arrive at {TIME}\.?$")
WAIT_RE = re.compile(rf"^You wait until {TIME}\.?$")
MEET_RE = re.compile(rf"^You meet (.+?)(?: for (\d+) minutes?)? from {TIME} to {TIME}\.?$")


def evaluate_meeting_solution(
    constraints: dict,
    solution: list,
    golden_solution: Optional[list] = None,
) -> Tuple[bool, dict]:
    """
    Validate meeting planning solution against constraints.

    Args:
        constraints: Constraints from task JSON (travel_distances, start, people_to_meet)
        solution: List of itinerary steps
        golden_solution: Golden itinerary (list of steps), used for the optimality check

    Returns:
        (is_valid, error_detail)
    """
    if not isinstance(solution, list):
        return False, {"error": "solution must be a list", "got": type(solution).__name__}

    if len(solution) == 0:
        return False, {"error": "solution cannot be empty"}

    is_valid, detail = validate_itinerary(constraints, solution)
    if not is_valid:
        return False, detail

    num_met = detail["num_met"]
    if golden_solution:
        golden_valid, golden_detail = validate_itinerary(constraints, golden_solution)
        golden_num_met = golden_detail["num_met"] if golden_valid else count_meetings(golden_solution)
        if num_met < golden_num_met:
            return False, {
                "error": "valid itinerary but meets fewer friends than the golden solution",
                "error_type": "suboptimal",
                "num_met": num_met,
                "golden_num_met": golden_num_met,
            }

    return True, {"num_met": num_met}


def validate_itinerary(constraints: dict, steps: list) -> Tuple[bool, dict]:
    """
    Simulate an itinerary step by step and check it against the constraints.

    Returns:
        (is_valid, detail) where detail holds "num_met" on success or "error"/"step" on failure
    """
    travel = {
        (norm(d["place"]["from"]), norm(d["place"]["to"])): int(d["walking_time"])
        for d in constraints.get("travel_distances", [])
    }
    people = {norm(p["name"]): p for p in constraints.get("people_to_meet", [])}
    start = constraints.get("start", {})

    location = None
    current = None
    met = set()

    for idx, step in enumerate(steps):
        if not isinstance(step, str):
            return False, {"error": "step is not a string", "step": idx}
        text = " ".join(step.strip().split())

        def fail(error, **extra):
            return False, {"error": error, "step": idx, "text": text, **extra}

        if idx == 0:
            m = START_RE.match(text)
            if not m:
                return fail("first step must be 'You start at [place] at [time].'")
            if norm(m.group(1)) != norm(start.get("location", "")):
                return fail("wrong start location", expected=start.get("location"))
            if parse_time(m.group(2)) != parse_time(start.get("time_of_day", "")):
                return fail("wrong start time", expected=start.get("time_of_day"))
            location, current = norm(m.group(1)), parse_time(m.group(2))
            continue

        m = TRAVEL_RE.match(text)
        if m:
            origin, dest = m.group(1), norm(m.group(2))
            minutes, arrive = int(m.group(3)), parse_time(m.group(4))
            if origin is not None and norm(origin) != location:
                return fail("travels from a place other than the current location", current=location)
            if (location, dest) not in travel:
                return fail("no travel time between these locations", origin=location, destination=dest)
            if minutes != travel[(location, dest)]:
                return fail("wrong travel time", expected=travel[(location, dest)], got=minutes)
            if arrive != current + minutes:
                return fail("wrong arrival time", expected=format_time(current + minutes))
            location, current = dest, arrive
            continue

        m = WAIT_RE.match(text)
        if m:
            until = parse_time(m.group(1))
            if until < current:
                return fail("waits until a time that has already passed", current=format_time(current))
            current = until
            continue

        m = MEET_RE.match(text)
        if m:
            name = norm(m.group(1))
            stated = int(m.group(2)) if m.group(2) else None
            begin, end = parse_time(m.group(3)), parse_time(m.group(4))
            person = people.get(name)
            if person is None:
                return fail("unknown person", person=m.group(1))
            if name in met:
                return fail("person met more than once", person=person["name"])
            if norm(person["location"]) != location:
                return fail("not at the person's location", expected=person["location"], current=location)
            if begin < current:
                return fail("meeting starts before arrival", current=format_time(current))
            if begin < parse_time(person["time_of_day"]["from"]) or end > parse_time(person["time_of_day"]["to"]):
                return fail("meeting outside availability window", window=person["time_of_day"])
            if end - begin < int(person["min_meeting_duration"]):
                return fail("meeting shorter than minimum duration",
                            required=person["min_meeting_duration"], got=end - begin)
            if stated is not None and stated != end - begin:
                return fail("stated duration does not match meeting times", stated=stated, actual=end - begin)
            met.add(name)
            current = end
            continue

        return fail("unparseable step")

    return True, {"num_met": len(met)}


def count_meetings(steps: list) -> int:
    """Count meeting steps in an itinerary without validating it."""
    return sum(1 for s in steps if isinstance(s, str) and MEET_RE.match(" ".join(s.strip().split())))


def norm(name: str) -> str:
    """Normalize a place or person name for comparison."""
    return " ".join(str(name).replace("’", "'").split()).lower()


def parse_time(time_str: str) -> Optional[int]:
    """Parse a 12-hour time like '9:00AM' or '9:00 AM' to minutes since midnight."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([AaPp][Mm])", str(time_str).strip())
    if not m:
        return None
    hour, minute, suffix = int(m.group(1)) % 12, int(m.group(2)), m.group(3).upper()
    return (hour + (12 if suffix == "PM" else 0)) * 60 + minute


def format_time(minutes: int) -> str:
    """Format minutes since midnight as a 12-hour time like '9:00AM'."""
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour % 24 < 12 else "PM"
    return f"{(hour % 12) or 12}:{minute:02d}{suffix}"
