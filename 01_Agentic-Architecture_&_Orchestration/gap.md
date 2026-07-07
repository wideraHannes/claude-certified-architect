# Domain 1 — Gap List

Items present in `ccaf_exam_guide.pdf` (Domain 1, Task Statements 1.1–1.7) that are missing or under-emphasized in `overview.md`. Follow-ups for later study.

Source: exam guide pp. 5–9.

---

## 1.1 Agentic Loops — explicit anti-pattern list

Exam guide lists three named anti-patterns that our overview doesn't call out by name:

1. **Parsing natural-language signals** from assistant text to decide when to terminate.
2. **Setting arbitrary iteration caps as the *primary* stopping mechanism** (caps are a defensive backstop, not the termination condition).
3. **Checking for assistant text content as a completion indicator** (use `stop_reason == "end_turn"`, not "did it produce prose").

Our overview says "cap iterations/tokens defensively" but doesn't warn that treating the cap as the primary stop is itself the anti-pattern. Worth a dedicated bullet.

---

## 1.2 Multi-Agent — observability as motivation for hub-and-spoke

Exam guide frames "route all subagent communication through the coordinator" as being about **observability, consistent error handling, and controlled information flow** — not just "no peer-to-peer." Overview treats it as a topology rule; the *why* (single choke point for logging/error policy) is missing.

Also: **"dynamically select which subagents to invoke rather than always routing through the full pipeline"** — coordinator should skip spokes it doesn't need, not fan out unconditionally. Overview implies this ("dispatch only what's needed") but could be sharper.

---

## 1.5 Hooks — PostToolUse data-normalization use case

Overview mentions "Data shaping → PostToolUse" abstractly. Exam guide is concrete: **normalize heterogeneous MCP tool outputs** — Unix timestamps → ISO 8601, numeric status codes → labels — *before the model sees them*. This is the canonical PostToolUse scenario for MCP-heavy stacks and deserves a worked example.

Also concrete on the PreToolUse side: **blocking refunds above a threshold (e.g. $500) and redirecting to an alternative workflow (human escalation)** — not just "deny." The redirect-to-alternative pattern isn't in the overview.

---

## 1.6 Task Decomposition — dynamic-plan procedure

Exam guide gives a concrete recipe for dynamic decomposition of open-ended tasks ("add comprehensive tests to a legacy codebase"):

1. Map structure.
2. Identify high-impact areas.
3. Build a prioritized plan that **adapts as dependencies are discovered**.

Overview says "the plan itself is part of the work" but doesn't walk through this map → prioritize → adapt sequence. Add a short worked pattern.

---

## 1.7 Session State — targeted re-analysis on resume

Exam guide skill: **"Informing a resumed session about specific file changes for targeted re-analysis rather than requiring full re-exploration."** Overview covers the fresh-start-plus-summary path but under-treats the middle ground: resume + explicit delta note ("files X, Y changed since checkpoint — re-read before answering"). Worth calling out as a distinct third option alongside `--resume` blind and full fresh start.

---

## Cross-cutting — retryable vs non-retryable (bleeds in from Domain 2)

Not strictly Domain 1, but Task Statement 2.2 (`isError` + `errorCategory` + `isRetryable`) is what makes the loop's `is_error: true` handling in §1.1 actually useful. Overview's loop section says "return `is_error: true` so Claude can retry" — but doesn't mention that structured error metadata is what lets Claude decide *whether* to retry vs escalate. Worth a forward-reference from §1.1 to Domain 2's error taxonomy.
