#!/usr/bin/env python3
"""
Chunking pipeline runner for a local open-weight judge (vLLM).

Same judge prompt and request format as the Gemini judge (one user message =
judge prompt + "\\n\\n" + reasoning segment), but runs offline on one GPU and
writes {condition}_chunking_{tag}.json next to the Gemini {condition}_chunking.json.

The run is resumable: every finished segment is appended to a JSONL cache, so
restarting the command skips work that is already done.

Usage (one free GPU, vllm-env; set CUDA_VISIBLE_DEVICES):
    python src/run_chunking_local.py --tag gemma
    python src/run_chunking_local.py --tag gemma --inputs output/qwen/calendar/baseline_execution.json
"""

import argparse
import glob
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from general.io_utils import get_timestamp, make_path_relative
from chunking.chunk_parser import parse_and_stitch_segments
from chunking.reasoning_splitter import split_reasoning_by_tokens

REPO_ROOT = Path(__file__).parent.parent


def extract_json_object(response: str) -> str:
    """
    Keep the first complete JSON object. Open models often wrap it in a code
    fence, and Gemma sometimes repeats the whole object after finishing it.
    """
    start = response.find("{")
    if start < 0:
        return response
    try:
        _, end = json.JSONDecoder().raw_decode(response, start)
        return response[start:end]
    except json.JSONDecodeError:
        return response[start:response.rfind("}") + 1]


def loop_start(text: str, window: int = 300):
    """Position where the response starts repeating a 300-char passage it already wrote, else None."""
    for i in range(0, len(text) - window, 50):
        if text.find(text[i:i + window]) < i:
            return i
    return None


def needs_retry(row: dict) -> bool:
    """A segment is retried in smaller pieces if it looped, truncated or did not parse."""
    if row["finish_reason"] == "length" or loop_start(extract_json_object(row["response"])) is not None:
        return True
    try:
        parse_and_stitch_segments([extract_json_object(row["response"])])
    except ValueError:
        return True
    return False


def build_requests(input_paths: list, segment_tokens: int) -> tuple:
    """Split every example's pre-code reasoning into judge segments."""
    requests, examples = [], {}
    for path in input_paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for example in data["examples"]:
            key = f"{make_path_relative(str(path))}::{example['example_id']}"
            text = example.get("reasoning_before_code") or ""
            segments = split_reasoning_by_tokens(text, segment_tokens) if text.strip() else []
            examples[key] = {"path": str(path), "example": example, "num_segments": len(segments)}
            for i, segment in enumerate(segments):
                requests.append({"id": f"{key}::{i}", "text": segment})
    return requests, examples


def load_cache(cache_path: Path) -> dict:
    done = {}
    if cache_path.exists():
        with cache_path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    done[row["id"]] = row
    return done


def load_llm(args):
    from vllm import LLM
    return LLM(
        model=args.model,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_num_seqs=args.max_num_seqs,
        quantization=args.quantization,
        kv_cache_dtype=args.kv_cache_dtype,
        enable_prefix_caching=True,
    )


def run_judge(llm, requests: list, cache_path: Path, args) -> None:
    """Judge all pending segments in length-sorted waves, appending results to the cache."""
    from vllm import SamplingParams

    judge_prompt = (REPO_ROOT / args.judge_prompt).read_text(encoding="utf-8")
    tokenizer = llm.get_tokenizer()

    # Longest first, so the slowest requests do not form the tail of the run
    pending = sorted(requests, key=lambda r: len(r["text"]), reverse=True)
    total, start = len(pending), time.time()
    generated = 0

    for wave_start in range(0, total, args.wave_size):
        wave = pending[wave_start:wave_start + args.wave_size]
        messages = [[{"role": "user", "content": f"{judge_prompt}\n\n{r['text']}"}] for r in wave]
        params = []
        for m in messages:
            prompt_len = len(tokenizer.apply_chat_template(m, tokenize=True, add_generation_prompt=True))
            params.append(SamplingParams(temperature=0.0, max_tokens=max(1, args.max_model_len - prompt_len)))

        outputs = llm.chat(messages, params, use_tqdm=False)
        with cache_path.open("a", encoding="utf-8") as f:
            for request, output in zip(wave, outputs):
                completion = output.outputs[0]
                generated += len(completion.token_ids)
                f.write(json.dumps({
                    "id": request["id"],
                    "response": completion.text,
                    "finish_reason": completion.finish_reason,
                    "output_tokens": len(completion.token_ids),
                    "prompt_tokens": len(output.prompt_token_ids),
                }) + "\n")

        done = wave_start + len(wave)
        elapsed = time.time() - start
        print(f"[{get_timestamp()}] {done}/{total} segments, {generated:,} output tokens, "
              f"{generated / elapsed:,.0f} tok/s, {elapsed / 3600:.2f} h elapsed", flush=True)


def resolve_segment(segment_id: str, done: dict):
    """
    Response for one segment. If it was retried in pieces, the pieces' chunk
    lists are merged into one response; pieces that still fail are dropped.
    """
    row = done.get(segment_id)
    if row is None or f"{segment_id}::r0" not in done:
        return row
    chunks, j = [], 0
    while f"{segment_id}::r{j}" in done:
        piece = done[f"{segment_id}::r{j}"]
        if not needs_retry(piece):
            chunks += json.loads(extract_json_object(piece["response"]))["chunk_analysis"]
        j += 1
    if not chunks:  # every piece failed: leave the segment unjudged rather than empty
        return {"response": "", "finish_reason": "stop"}
    return {"response": json.dumps({"chunk_analysis": chunks}), "finish_reason": "stop"}


def assemble_outputs(examples: dict, done: dict, args) -> None:
    """Write one {condition}_chunking_{tag}.json per execution file."""
    by_path = {}
    for key, info in examples.items():
        by_path.setdefault(info["path"], []).append((key, info))

    for path, items in sorted(by_path.items()):
        execution = json.loads(Path(path).read_text(encoding="utf-8"))
        meta = execution["run_metadata"]
        out_examples, failures = [], 0

        for key, info in items:
            example = info["example"]
            rows = [resolve_segment(f"{key}::{i}", done) for i in range(info["num_segments"])]
            base = {"example_id": example["example_id"],
                    "reasoning_before_code": example.get("reasoning_before_code", "")}
            if info["num_segments"] == 0:
                out_examples.append({**base, "chunk_analysis": [], "token_statistics": {},
                                     "has_solver_like": False, "judge_metadata": {"skipped": "empty reasoning"}})
                continue
            if any(r is None for r in rows):
                failures += 1
                out_examples.append({**base, "error": "segments not judged yet"})
                continue
            try:
                chunks, stats, has_solver_like = parse_and_stitch_segments(
                    [extract_json_object(r["response"]) for r in rows])
            except ValueError as e:
                failures += 1
                out_examples.append({**base, "error": str(e),
                                     "judge_metadata": {"num_segments": len(rows)}})
                continue
            text = example.get("reasoning_before_code", "")
            judged_chars = sum(len(v) for c in chunks for k, v in c.items() if k != "tokens")
            out_examples.append({
                **base,
                "chunk_analysis": chunks,
                "token_statistics": stats,
                "has_solver_like": has_solver_like,
                "judge_metadata": {
                    "num_segments": len(rows),
                    "was_split": len(rows) > 1,
                    "retried_segments": sum(f"{key}::{i}::r0" in done for i in range(info["num_segments"])),
                    "coverage": judged_chars / len(text) if text else None,
                },
            })

        output = {
            "run_metadata": {
                "task": meta["task"], "model": meta["model"], "condition": meta.get("condition", "baseline"),
                "execution_json": make_path_relative(path),
                "judge_model": args.model,
                "judge_prompt": args.judge_prompt,
                "judge_settings": {"quantization": args.quantization, "kv_cache_dtype": args.kv_cache_dtype,
                                   "segment_tokens": args.segment_tokens, "max_model_len": args.max_model_len,
                                   "temperature": 0.0},
                "timestamp": get_timestamp(),
                "num_examples": len(out_examples),
            },
            "summary": {"failed_examples": failures},
            "examples": out_examples,
        }
        condition = meta.get("condition", "baseline")
        out_path = Path(path).parent / f"{condition}_chunking_{args.tag}.json"
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {make_path_relative(str(out_path))} ({failures} failed examples)")


def main():
    parser = argparse.ArgumentParser(description="Run the chunking judge with a local vLLM model")
    parser.add_argument("--inputs", nargs="*", default=None,
                        help="Execution JSONs (default: output/*/*/*_execution.json)")
    parser.add_argument("--tag", required=True, help="Output suffix, e.g. 'gemma' -> *_chunking_gemma.json")
    parser.add_argument("--model", default="google/gemma-4-31B-it")
    parser.add_argument("--judge-prompt", default="prompts/judge/llm_as_judge_for_chunking.txt")
    parser.add_argument("--segment-tokens", type=int, default=2000,
                        help="Max cl100k tokens per judged segment (longer segments make Gemma loop)")
    parser.add_argument("--retry-tokens", type=int, default=700,
                        help="Segments that loop, truncate or fail to parse are re-judged in pieces this size")
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.92)
    parser.add_argument("--max-num-seqs", type=int, default=128)
    parser.add_argument("--quantization", default="fp8", help="Weight quantization ('none' for bf16)")
    parser.add_argument("--kv-cache-dtype", default="fp8")
    parser.add_argument("--wave-size", type=int, default=512, help="Requests per vLLM call between cache flushes")
    parser.add_argument("--limit", type=int, default=None, help="Judge at most this many pending segments")
    parser.add_argument("--assemble-only", action="store_true", help="Only write outputs from the cache")
    args = parser.parse_args()
    if args.quantization == "none":
        args.quantization = None

    inputs = args.inputs or sorted(glob.glob(str(REPO_ROOT / "output" / "*" / "*" / "*_execution.json")))
    requests, examples = build_requests(inputs, args.segment_tokens)
    cache_path = REPO_ROOT / "output" / f"judge_cache_{args.tag}.jsonl"
    done = load_cache(cache_path)
    pending = [r for r in requests if r["id"] not in done]
    if args.limit is not None:
        pending = pending[:args.limit]
    print(f"{len(examples)} examples, {len(requests)} segments, {len(done)} cached, {len(pending)} to judge")

    if not args.assemble_only:
        llm = None
        if pending:
            llm = load_llm(args)
            run_judge(llm, pending, cache_path, args)
            done = load_cache(cache_path)
        if args.limit is None:
            # Retry pass: re-judge failed segments in smaller pieces (once)
            text = {r["id"]: r["text"] for r in requests}
            retries = []
            for seg_id, row in done.items():
                if seg_id in text and f"{seg_id}::r0" not in done and needs_retry(row):
                    for j, piece in enumerate(split_reasoning_by_tokens(text[seg_id], args.retry_tokens)):
                        retries.append({"id": f"{seg_id}::r{j}", "text": piece})
            print(f"Retrying {len({r['id'].rsplit('::', 1)[0] for r in retries})} failed segments "
                  f"as {len(retries)} pieces")
            if retries:
                llm = llm or load_llm(args)
                run_judge(llm, retries, cache_path, args)
                done = load_cache(cache_path)
    if args.limit is None or args.assemble_only:
        assemble_outputs(examples, done, args)


if __name__ == "__main__":
    main()
