---
name: token-audit
description: Analyze a Claude Code session transcript to see what drove token/context usage and suggest concrete changes to reduce it next time (fewer redundant reads, narrower tool calls, more subagent delegation). Use when the user asks to reduce token usage, audit context consumption, or wants tips for more efficient sessions.
argument-hint: "[session_id]"
user-invocable: true
---

# Token Audit

Reflect on a Claude Code session transcript (default: the current session) to find what consumed the most tokens/context, then propose concrete, specific changes for future sessions.

## Usage

```
/token-audit [session_id]
```

If no `session_id` is given, audit the **current session's** transcript (the most recently modified one for this project).

## Step 1: Run the analysis script

The script `analyze_session.py` lives in the `scripts/` directory alongside this SKILL.md — use its absolute path:

```bash
python3 <skill-dir>/scripts/analyze_session.py [session_id]
```

With no argument, it picks the most recently modified transcript under `~/.claude/projects/<this-project>/` — i.e. the current session. Pass a `session_id` to audit a different one.

It prints: token totals (output, cache-creation, cache-read, end-of-session context size), a per-tool breakdown of result sizes, the top 8 largest individual tool results, and any files `Read` more than once.

## Step 2: Reflect and report

Using the numbers from Step 1, write a short report with two sections:

### Usage summary

State the totals plainly (turns, output tokens, cache-creation tokens, cache-read tokens, final context size), and name the top 2-3 tools/files by token contribution.

### Recommendations

For each significant contributor, give a **specific, actionable** suggestion grounded in what actually happened in this transcript — not generic advice. Patterns to look for:

- **Repeated `Read` of the same file** → name the file and how many times; suggest relying on edit results / conversation memory instead of re-reading (the harness already tells Claude not to re-read a file just edited).
- **Large `Read` calls on big files** → suggest using `offset`/`limit` to read only the relevant section next time.
- **Large `Bash` tool results** (full `git diff`, verbose build/test/log output, unfiltered `ls`/`find`) → suggest piping through `grep`/`head`, using `--quiet`/`-q` flags, or more targeted commands.
- **Broad exploration done inline** (many `Read`/`Grep`/`Glob` calls in the main thread) → suggest delegating to the `Explore` or `general-purpose` subagent next time, since their results return as a digested summary instead of raw file contents.
- **High cache-creation relative to context size** → context is being rebuilt rather than reused (e.g. long gaps causing cache expiry, or large CLAUDE.md/memory content reloaded); suggest trimming what's loaded into context up front.
- **Large `WebFetch`/`WebSearch` results** → suggest narrower queries or fetching specific sections/pages.

Only include recommendations for patterns that actually show up with meaningful weight — don't pad with boilerplate advice that didn't apply to this session.

End with a one-line takeaway: the single highest-leverage change for *this* session.

## Notes

- This skill only reads the local transcript file — it makes no API calls and changes nothing.
- "Tokens" for tool results are estimated as `chars / 4`; treat as approximate.
- A large or growing `cache-read` total is the main lever for "token usage" in long sessions — it reflects the cost of re-processing the accumulated context on every turn, so the biggest win is usually keeping context lean (smaller tool results, less redundant exploration) rather than any single call.
