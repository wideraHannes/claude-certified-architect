# Session State and Resumption

Notes on [1.7](https://claudecertificationguide.com/learn/1-agentic-architecture/1-7-session-state-resumption).

## Three approaches

- **`--resume <session>`** — restores full history + cached tool results. Only safe when files haven't changed.
- **`fork_session`** — branches from a shared baseline. For comparing alternatives, not for continuation.
- **Fresh start + summary injection** — new session with a curated summary of prior findings. Avoids stale tool results.

## Stale context

Resuming after file edits leaves outdated tool results in history. Agent may recommend fixes already applied or reference removed code. Asking it to "re-read the file" doesn't help — the stale results still influence tangential reasoning.

## Rules

- Resume only if files are unchanged.
- Fork only for divergent strategies.
- After edits: fresh start + summary of what changed, not full re-exploration.

## Exam traps

- Suggesting `--resume` after file edits.
- Recommending full re-exploration when only a few files changed.
- Confusing `fork_session` (branch) with `--resume` (continue).
- Using `fork_session` to escape stale context — the fork inherits it.

## Hands-on (skipped)

Six-step build to skip: (1) named session analyzing a 10-file codebase, (2) record findings as structured docs, (3) edit 3 files, (4) `--resume` and observe contradictory advice from stale context, (5) fresh session with an injected summary focused on the 3 changed files, (6) compare output quality of resume vs. fresh-start.
