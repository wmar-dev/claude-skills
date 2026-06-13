#!/usr/bin/env python3
"""Summarize token/context usage from a Claude Code session transcript.

Usage: analyze_session.py [session_id]

With no argument, analyzes the most recently modified transcript for the
current working directory's project.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Standard rough estimate for English text/code; tool results don't carry
# real token counts, only character counts.
CHARS_PER_TOKEN = 4


def find_transcript(session_id=None):
    project_dir = Path.home() / ".claude" / "projects" / os.getcwd().replace("/", "-")
    if session_id:
        path = project_dir / f"{session_id}.jsonl"
        if not path.exists():
            sys.exit(f"No transcript found at {path}")
        return path

    candidates = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        sys.exit(f"No session transcripts found in {project_dir}")
    return candidates[0]


def analyze(path):
    out_sum = cc_sum = cr_sum = 0
    final_cc = final_cr = 0
    turns = 0
    tool_sizes = defaultdict(lambda: [0, 0])  # name -> [calls, chars]
    tool_calls = {}  # tool_use_id -> (name, input)
    file_reads = defaultdict(int)
    calls_list = []  # (name, chars, detail)
    model_usage = defaultdict(lambda: [0, 0])  # model -> [turns, output_tokens]
    cache_resets = []  # (turn_index, cc_tokens, prev_total_tokens, cause)
    prev_total = None
    prev_tool_names = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue

            content = msg.get("content")
            cur_tool_names = []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        cur_tool_names.append(block.get("name"))

            usage = msg.get("usage")
            if usage:
                turns += 1
                out_sum += usage.get("output_tokens", 0)
                cc = usage.get("cache_creation_input_tokens", 0)
                cr = usage.get("cache_read_input_tokens", 0)
                cc_sum += cc
                cr_sum += cr
                final_cc, final_cr = cc, cr

                model = msg.get("model")
                if model:
                    model_usage[model][0] += 1
                    model_usage[model][1] += usage.get("output_tokens", 0)

                total = cc + cr
                if prev_total is not None and prev_total > 2000 and cc > 1000 and cc > prev_total * 0.5:
                    cause = "ToolSearch" if "ToolSearch" in prev_tool_names else None
                    cache_resets.append((turns, cc, prev_total, cause))
                prev_total = total
                prev_tool_names = cur_tool_names

            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tool_calls[block.get("id")] = (block.get("name"), block.get("input") or {})
                elif block.get("type") == "tool_result":
                    name, inp = tool_calls.get(block.get("tool_use_id"), ("unknown", {}))
                    result_content = block.get("content")
                    if isinstance(result_content, list):
                        text = "".join(b.get("text", "") for b in result_content if isinstance(b, dict))
                    elif isinstance(result_content, str):
                        text = result_content
                    else:
                        text = ""
                    tool_sizes[name][0] += 1
                    tool_sizes[name][1] += len(text)
                    detail = (
                        inp.get("file_path")
                        or inp.get("command")
                        or inp.get("pattern")
                        or inp.get("url")
                        or inp.get("description")
                        or inp.get("prompt")
                        or ""
                    )
                    calls_list.append((name, len(text), str(detail)[:80]))
                    if name == "Read":
                        file_reads[inp.get("file_path", "?")] += 1

    return {
        "turns": turns,
        "out_sum": out_sum,
        "cc_sum": cc_sum,
        "cr_sum": cr_sum,
        "context_size": final_cr + final_cc,
        "tool_sizes": tool_sizes,
        "calls_list": calls_list,
        "file_reads": file_reads,
        "model_usage": model_usage,
        "cache_resets": cache_resets,
    }


def report(stats):
    print(f"Assistant turns: {stats['turns']}")
    print(f"Total output tokens: {stats['out_sum']:,}")
    print(f"Total cache-creation tokens (sum across turns): {stats['cc_sum']:,}")
    print(f"Total cache-read tokens (sum across turns): {stats['cr_sum']:,}")
    print(f"Context size at end of session: {stats['context_size']:,}")

    print("\nTool result sizes (approx tokens = chars / 4):")
    for name, (calls, chars) in sorted(stats["tool_sizes"].items(), key=lambda x: -x[1][1]):
        print(f"  {name:14s} {calls:3d} calls  ~{chars // CHARS_PER_TOKEN:>7,} tokens")

    print("\nTop 8 individual tool results by size:")
    for name, size, detail in sorted(stats["calls_list"], key=lambda x: -x[1])[:8]:
        print(f"  ~{size // CHARS_PER_TOKEN:>6,} tokens  {name:12s} {detail}")

    repeats = {fp: n for fp, n in stats["file_reads"].items() if n > 1}
    if repeats:
        print("\nFiles Read more than once:")
        for fp, n in sorted(repeats.items(), key=lambda x: -x[1]):
            print(f"  {n}x  {fp}")

    if stats["model_usage"]:
        print("\nOutput tokens by model:")
        for model, (n_turns, out_tok) in sorted(stats["model_usage"].items(), key=lambda x: -x[1][1]):
            print(f"  {model:24s} {n_turns:3d} turns  ~{out_tok:>7,} output tokens")

    resets = stats["cache_resets"]
    if resets:
        reset_tokens = sum(cc for _, cc, _, _ in resets)
        print(f"\nMid-session cache resets: {len(resets)} (re-cached ~{reset_tokens:,} tokens total)")
        for turn, cc, prev_total, cause in resets[:5]:
            cause_str = f" — follows a {cause} call (new tool schema changed the cached prefix)" if cause else ""
            print(f"  turn {turn:3d}: re-cached ~{cc:,} tokens (prior context was ~{prev_total:,}){cause_str}")


def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    path = find_transcript(session_id)
    print(f"Transcript: {path}\n")
    report(analyze(path))


if __name__ == "__main__":
    main()
