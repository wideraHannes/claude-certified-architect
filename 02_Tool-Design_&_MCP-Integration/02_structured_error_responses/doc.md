# Structured Error Responses

Notes on [2.2](https://claudecertificationguide.com/learn/2-tool-design-mcp/2-2-structured-error-responses).

## Golden rule

Every failure carries `errorCategory`, `isRetryable`, and `description`. Without them the agent can't tell "retry" from "give up".

## The four categories

| Category     | Retry?               |
|--------------|----------------------|
| `transient`  | Yes — same input.    |
| `validation` | Yes — fix input.     |
| `business`   | No — escalate.       |
| `permission` | No — escalate.       |

## The trap

`isError=false, resultCount=0` is a **valid empty result**, not a failure. Retrying it is the classic 2.2 mistake.

| Wire shape                        | Meaning         | Retry? |
|-----------------------------------|-----------------|--------|
| `isError=false, resultCount=0`    | No such row     | No     |
| `isError=true,  transient`        | Query never ran | Yes    |

## Multi-agent propagation

Subagents recover locally where they can; only unresolvable errors bubble up, with partial results attached.

## Implementation — `error_recovery_loop.py`

- `ToolError` / `ToolResult` — the required metadata shape.
- `TRANSIENT`, `VALIDATION`, `BUSINESS`, `PERMISSION`, `EMPTY`, `SUCCESS` — one canonical outcome each, reused in the scripts.
- `decide()` — the recovery table in code.
- `run_agent()` — hand-rolled loop so the recovery branch is visible; feeds results back as JSON with `is_error` set.
- `main()` — scripts one scenario per branch.
