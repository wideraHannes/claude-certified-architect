# Workflow Enforcement and Handoff

Notes on [1.4](https://claudecertificationguide.com/learn/1-agentic-architecture/1-4-workflow-enforcement-handoff).

## Prompt vs. code

- **Prompt** — probabilistic (~90–95%). Fine for style/formatting.
- **Programmatic gate** — deterministic (100%). Use whenever failure means money loss, security breach, or compliance violation.

## Prerequisite gate

Code in the tool handler that blocks execution until a precondition is met. The model cannot argue past it.

```
process_refund():
    if session.verified_customer_id is None:
        return "BLOCKED: call get_customer first"
```

Canonical example: "always verify identity" prompt fails 8% in production; gate drops it to 0%.

## Handoff — 5 mandatory fields

Human agents don't see the transcript. Missing any field forces them to restart.

1. `customer_id`
2. `conversation_summary`
3. `root_cause`
4. `refund_amount` (0 if none)
5. `recommended_action`

## Multi-concern requests

Decompose → investigate in parallel with shared context → synthesize one resolution. Never pick only the first item or open separate conversations.

## Exam traps

- "Improve the prompt" / "add few-shot" — probabilistic, never sufficient for financial/compliance.
- "Add a routing classifier" — routes between agents; doesn't enforce workflow inside one.
- Handoff missing fields — hard fail.
