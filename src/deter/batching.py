"""Several problems of one task in a single prompt, one program per problem.

Groups: the selected problem ids are shuffled with a fixed seed and cut into groups of K, so a
group is the same for every model and FL. The model answers with K code blocks headed
`# Problem i`; split_programs() finds the block for each position.
"""

import random
import re

from execution.code_extractor import extract_all_code_blocks, find_answer_start

GROUP_SEED = 20261031

# Trailing answer cues that address a single problem; they are dropped inside a batch
PROBLEM_CUES = [
    re.compile(r"\s*Your response should start with 'SOLUTION:'\.\s*$"),
    re.compile(r"\s*SOLUTION:\s*$"),
]
FORMAT_CUE = re.compile(r"\s*SOLUTION CODE:\s*$")


def make_groups(example_ids: list, k: int, seed: int = GROUP_SEED) -> list:
    ids = list(example_ids)
    random.Random(seed).shuffle(ids)
    return [ids[i:i + k] for i in range(0, len(ids), k)]


def strip_cue(text: str, cues: list) -> str:
    for cue in cues:
        text = cue.sub("", text)
    return text.rstrip()


def build_batch_prompt(prefix: str, problem_texts: list, output_format: str, suffix: str) -> str:
    k = len(problem_texts)
    problems = "\n\n".join(f"### Problem {i}\n\n{strip_cue(t.strip(), PROBLEM_CUES)}"
                           for i, t in enumerate(problem_texts, 1))
    prompt = prefix.replace("{K}", str(k)).replace("{PROBLEM}", problems)
    fmt = strip_cue(output_format, [FORMAT_CUE])
    return f"{prompt}\n\n{fmt}\n\n{suffix.replace('{K}', str(k)).strip()}"


HEADER = re.compile(r"^\s*#\s*Problem\s+(\d+)\b", re.I)


def _header_number(code: str):
    for line in code.splitlines()[:3]:
        m = HEADER.match(line)
        if m:
            return int(m.group(1))
    return None


def split_programs(trace: str, k: int) -> dict:
    """
    Return {"reasoning": text before the first program, "programs": {position: code or None},
    "unlabelled_blocks": count}. Blocks are taken from the final answer when the trace has an
    end-of-thinking marker, else from the whole trace (later blocks win). A block without a
    `# Problem i` header is used only when the answer has exactly k blocks, by its order.
    """
    answer_start = find_answer_start(trace)
    scope_start = answer_start if answer_start >= 0 else 0
    blocks = extract_all_code_blocks(trace[scope_start:])
    blocks = [b for b in blocks if b.get("pattern") != "single_line"]
    programs = {i: None for i in range(1, k + 1)}
    unlabelled = 0
    for b in blocks:
        n = _header_number(b["code"])
        if n in programs:
            programs[n] = b["code"]
        else:
            unlabelled += 1
    if answer_start >= 0 and unlabelled == len(blocks) == k:
        programs = {i: b["code"] for i, b in enumerate(blocks, 1)}
    # The reasoning ends where the answer's first program starts, as for a single program
    first = min((b["start"] for b in blocks), default=len(trace) - scope_start)
    reasoning = trace[:scope_start + first]
    return {"reasoning": reasoning.strip(), "programs": programs, "unlabelled_blocks": unlabelled}
