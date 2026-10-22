#!/usr/bin/env python3
"""
Re-key chunking outputs whose judge responses were attached to the wrong examples.

The batch judge used to map Vertex AI batch outputs to examples by position, but
batch output order is not input order, so each example's chunk_analysis mostly
came from another example's trace. Judge chunks quote the trace, so each chunk is
re-assigned to the one trace (in the same file) that contains it verbatim:

  - Up to 5 probes of 150 characters (or the whole chunk if 40-150 characters)
    are searched across all traces of the file; a probe counts only if it occurs
    in exactly one trace. The chunk goes to the trace with the most probe hits.
  - A chunk with no unique probe hit inherits the trace of its matched
    neighbours within the same original chunk list, if they agree.
  - Chunks are ordered by their position in the trace, and token statistics are
    recomputed with enrich_chunks_with_tokens.

Status per example: "full" if its matched chunks cover >= 90% of the trace's
characters, "partial" if they cover less, "none" if no chunk matched (then
chunk_analysis is [] and token_statistics is null, so it can't be averaged in
by mistake).

Writes <condition>_chunking_rekeyed.json next to each input; never overwrites it.

Usage (needs tiktoken, e.g. /local-ssd/hz466/vllm-env/bin/python):
    python scripts/rekey_chunking.py output/*/*/*_chunking.json
"""

import bisect
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking.chunk_parser import enrich_chunks_with_tokens, has_solver_like_chunks

PROBE = 150
MIN_PROBE = 40
FULL_COVERAGE = 0.9
SEP = "\x00\x00\x00"


class TraceIndex:
    """All traces of one file joined into one string, for fast unique-substring lookup."""

    def __init__(self, traces: list[str]):
        self.starts = []
        parts, pos = [], 0
        for t in traces:
            self.starts.append(pos)
            parts.append(t)
            pos += len(t) + len(SEP)
        self.text = SEP.join(parts)

    def trace_of(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset) - 1

    def locate(self, probe: str):
        """(trace index, offset in trace) if probe occurs in exactly one trace, else None."""
        i = self.text.find(probe)
        if i < 0:
            return None
        t = self.trace_of(i)
        j = self.text.find(probe, i + 1)
        while j >= 0:
            if self.trace_of(j) != t:
                return None
            j = self.text.find(probe, j + 1)
        return t, i - self.starts[t]


def chunk_text(chunk: dict) -> tuple[str, str]:
    kind = next(k for k in chunk if k != "tokens")
    return kind, chunk[kind]


def match_chunk(index: TraceIndex, text: str):
    """(trace index, estimated start offset) for a chunk, or None."""
    if len(text) >= PROBE:
        n = min(5, len(text) // PROBE)
        offsets = [round(k * (len(text) - PROBE) / max(1, n - 1)) for k in range(n)]
        probes = [(o, text[o:o + PROBE]) for o in offsets]
    elif len(text) >= MIN_PROBE:
        probes = [(0, text)]
    else:
        return None
    votes = {}
    for o, p in probes:
        hit = index.locate(p)
        if hit:
            votes.setdefault(hit[0], []).append(max(0, hit[1] - o))
    if not votes:
        return None
    trace = max(votes, key=lambda t: len(votes[t]))
    starts = sorted(votes[trace])
    return trace, starts[len(starts) // 2]


def coverage(intervals: list[tuple[int, int]], length: int) -> float:
    covered, end = 0, 0
    for s, e in sorted(intervals):
        s, e = max(s, end), min(e, length)
        if e > s:
            covered += e - s
        end = max(end, e)
    return covered / length if length else 0.0


def rekey_file(path: Path) -> dict:
    data = json.load(open(path))
    examples = data["examples"]
    traces = [ex.get("reasoning_before_code") or "" for ex in examples]
    index = TraceIndex(traces)

    assigned = {i: [] for i in range(len(examples))}  # trace index -> [(start, kind, text)]
    n_chunks = n_matched = n_inferred = 0
    for ex in examples:
        chunks = [chunk_text(c) for c in ex.get("chunk_analysis", []) if c]
        hits = [match_chunk(index, text) for _, text in chunks]
        n_chunks += len(chunks)
        n_matched += sum(h is not None for h in hits)
        # unmatched chunks inherit their neighbours' trace when both sides agree
        for k, h in enumerate(hits):
            if h is not None:
                continue
            prev = next((hits[j] for j in range(k - 1, -1, -1) if hits[j] is not None), None)
            nxt = next((hits[j] for j in range(k + 1, len(hits)) if hits[j] is not None), None)
            sides = [s for s in (prev, nxt) if s is not None]
            if sides and all(s[0] == sides[0][0] for s in sides):
                hits[k] = (sides[0][0], (prev[1] + 1) if prev else max(0, nxt[1] - 1))
                n_inferred += 1
        for (kind, text), h in zip(chunks, hits):
            if h is not None:
                assigned[h[0]].append((h[1], kind, text))

    status = Counter()
    for i, ex in enumerate(examples):
        parts = sorted(assigned[i], key=lambda p: p[0])
        cov = coverage([(s, s + len(t)) for s, _, t in parts], len(traces[i]))
        if parts:
            chunks = [{kind: text} for _, kind, text in parts]
            enriched, stats = enrich_chunks_with_tokens(chunks)
            ex["chunk_analysis"], ex["token_statistics"] = enriched, stats
            ex["has_solver_like"] = has_solver_like_chunks(chunks)
            st = "full" if cov >= FULL_COVERAGE else "partial"
        else:
            ex["chunk_analysis"], ex["token_statistics"], ex["has_solver_like"] = [], None, False
            st = "none"
        ex.setdefault("judge_metadata", {})["rekey"] = {"status": st, "coverage": round(cov, 3), "chunks": len(parts)}
        status[st] += 1

    data["run_metadata"]["rekeyed_from"] = str(path)
    data["run_metadata"]["rekey_note"] = (
        "chunk_analysis re-assigned by verbatim matching of chunk text to traces "
        "(original batch outputs were mapped to examples by position)")
    if "summary" in data:
        data["summary"]["examples_with_solver_like"] = sum(ex["has_solver_like"] for ex in examples)
        data["summary"]["examples_sound_only"] = len(examples) - data["summary"]["examples_with_solver_like"]
    out = path.with_name(path.name.replace("_chunking.json", "_chunking_rekeyed.json"))
    json.dump(data, open(out, "w"), indent=2, ensure_ascii=False)
    return {"file": str(path), "chunks": n_chunks, "matched": n_matched, "inferred": n_inferred, **status}


if __name__ == "__main__":
    totals = Counter()
    for arg in sys.argv[1:]:
        r = rekey_file(Path(arg))
        totals.update({k: v for k, v in r.items() if k != "file"})
        print(f"{r['file']}: chunks {r['matched']}+{r['inferred']} inferred/{r['chunks']}, "
              f"full {r.get('full', 0)}, partial {r.get('partial', 0)}, none {r.get('none', 0)}")
    print(f"TOTAL: {dict(totals)}")
