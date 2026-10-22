# Local model on change requests: `qwen38:main`, 31 Aug - 1 Sep 2026

Model: Qwen3.8-27B, Q4_K_M, on an RTX 3090 Ti served by Ollama, driven by opencode 1.18.25 in an isolated cage (no outbound network, builds forbidden). Tasks were real change requests from a private codebase, given in plain language without file names, then compared with how the change had been made by a person. Those tasks and their reference patches are private and are **not** in this repository. The synthetic `t01`-`t06` tasks here follow the same classes but have not been run against this model.

Single runs. Settings changed during the evening and are marked per row:

| set | model window | output cap | reasoning | notes |
|---|---|---|---|---|
| A | 65 536 | 8 192 | default (maximum) | temperature 0.3 |
| B | 98 304 | 32 768 | low | |
| C | 98 304 (about 30k working) | 8 192 | low | tool output clipped to 150 lines / 6 KB |

| Class | Set | Time | Verdict | Notes |
|---|---|---|---|---|
| Text / number formatting | A | n/a | ✅ | |
| Layout: header row hides the first item | A | 6 min | ❌ | No edits; stopped at exactly 8 192 tokens of reasoning (`length`) |
| same, repeat | A | about 12 min | ❌ | Interrupted externally, no edits |
| same, repeat | C | 4 min | ❌ | Same stall, even with low reasoning |
| Permission filter leak | B | 6.5 min | ✅ | Same files as the reference; explained both halves of the cause |
| Legacy bookmark opens a blank page | C | 19 min | ❌ | Explained the role difference correctly, blamed a different culprit with confidence |
| Read-only view sends error emails | C | 10 min | ⚠️ | Right file; fixed 2 of 3 causes; keyed on role names rather than the server's check |
| Unstable ordering | direct Ollama, low reasoning | 3.75 min (225 s) | ✅ | One file, two lines, 11 turns |
| Money allocation + migration (checklist of 12) | opencode, 4-bit, 98k | 49 min | ⚠️ 10/12 | Broke the total when a payment was only partly allocated |
| same task, second attempt | pi, 3-bit, 196k | n/a | ⚠️ 10/12 | Left the total untouched: wrong in 2 of 4 scenarios |

A task on a feature with design freedom was prepared but not run.

## What held up
- Pinpoint fixes with an obvious address; correct explanations of the cause in its own words.
- Discipline: never touched the database schema when it should not, never added dependencies, no stray files.

## What did not
- Anything requiring a mental picture of the screen (zero edits, three times).
- Choosing between two plausible causes: picked the wrong one and sounded sure. Without a reference to compare against this looks like a finished answer.
- Completeness: stopped when two of three causes were fixed.

## Hardware note
After an aborted run, orphaned inference workers can keep holding GPU memory; the next run then fails with an allocation error that looks like a model fault. Compare `ollama ps` (empty) with `nvidia-smi` (memory still used), then stop the leftover worker processes; Ollama restarts them on demand.
