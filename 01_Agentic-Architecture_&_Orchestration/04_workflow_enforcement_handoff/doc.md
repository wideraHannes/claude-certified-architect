# Workflow Enforcement and Handoff

Condensed notes from [1.4 Workflow Enforcement and Handoff](https://claudecertificationguide.com/learn/1-agentic-architecture/1-4-workflow-enforcement-handoff).

## Core distinction

- **Prompt-based guidance** — instructions in the system prompt. Probabilistic (~90–95% compliance). Non-deterministic.
- **Programmatic enforcement** — code-level prerequisite gates. Deterministic (100%). Physically prevents wrong execution order.

## Exam decision rule

Use **programmatic enforcement** whenever a single failure would cause:

- financial loss (refunds, transfers, payments),
- security breach (identity verification, access control), or
- compliance violation (AML, regulatory).

Prompt-based guidance is only acceptable for low-stakes concerns (formatting, style, output ordering).

## Prerequisite gate mechanism

A prerequisite gate is a code check that blocks a tool until a precondition is met. The model *cannot* argue its way past a gate — the barrier lives in the tool handler, not in the prompt.

```
process_refund():
    if session.verified_customer_id is None:
        return "BLOCKED: call get_customer first"
    ...proceed...
```

The canonical "8% failure" example: a system prompt says *"Always verify identity before processing refunds"* and still fails 8% of the time in production. A prerequisite gate drops that to 0% — not by improving the prompt, but by making the illegal order impossible.

## Structured handoff protocol

Human agents **do not** have access to the model's conversation transcript. The handoff summary is their only source of context.

Five mandatory fields:

1. **customer_id** — so the human can pull the account.
2. **conversation_summary** — what the customer asked, what was attempted.
3. **root_cause** — the agent's diagnosis.
4. **refund_amount** — a specific number, or 0 if none applies.
5. **recommended_action** — the concrete next step for the human.

Missing fields force the human to restart the investigation from scratch.

## Multi-concern requests

Correct pattern: **decompose → investigate in parallel with shared context → synthesize a unified resolution**. Never handle a multi-concern request by picking only the first item or by opening separate conversations.

## Exam traps

- "Just improve the system prompt" — never sufficient for financial/compliance failures.
- "Add few-shot examples" — same. Probabilistic, not deterministic.
- "Add a routing classifier" — classifiers route between agents; they do not enforce workflow inside an agent.
- Handoff summaries with missing fields — a hard fail on the exam.

## Subagent lifecycle hooks (Agent SDK, referenced)

- **SubagentStart / SubagentStop** — hook points for logging, rate-limiting, schema-validating subagent input/output.
- **Subagent-scoped PreToolUse / PostToolUse** — per-subagent policy enforcement (e.g. billing subagent blocks refunds over threshold; tech-support subagent does not).
- **Stop-hook auto-conversion** — a `Stop` hook declared in a subagent's frontmatter runs at runtime as `SubagentStop`.

## Files in this section

- `prerequisite_gate.py` — Tasks 1–3: three tools (`get_customer`, `lookup_order`, `process_refund`) plus a session-level gate that blocks `process_refund` until verification has occurred, tested against a direct bypass prompt.
- `structured_handoff.py` — Tasks 4–5: a forced-tool-call handoff producing all five required fields, tested against a three-concern (return / billing dispute / account update) request.
