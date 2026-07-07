# Tool Distribution & Tool Choice

Notes on [2.3](https://claudecertificationguide.com/learn/2-tool-design-mcp/2-3-tool-distribution-choice).

## Golden numbers

- **4–5 tools per agent role.** Error rate climbs sharply past that.
- **18-tool agents are a red flag** — the exam's canonical "too many" case.
- **Coordinator round-trip ≈ +40% latency.** If 85% of a subagent's calls are simple, give it a **scoped cross-role tool** instead of routing through the coordinator.

## `tool_choice` modes

| Mode                                | Behavior                                                 | Use when                                    |
|-------------------------------------|----------------------------------------------------------|---------------------------------------------|
| `{"type": "auto"}`                  | Model may answer conversationally OR call a tool.        | Chat / open-ended.                          |
| `{"type": "any"}`                   | Model MUST call one of the tools, but picks which.       | Structured output is mandatory.             |
| `{"type": "tool", "name": "X"}`     | Model MUST call tool `X` specifically.                   | Enforcing a workflow step (e.g. first turn).|
| `{"type": "none"}`                  | Model cannot call tools.                                 | Force a prose answer.                       |

Trap: `"auto"` when the app needs structured output — the model may reply in prose and downstream JSON parsing breaks.

## Generic vs constrained

Prefer the **narrowest tool that does the job**. `fetch_url(url)` is a footgun: subagents will use it for anything. `load_document(url)` with an allow-list of document hosts / MIME types is the same capability under least privilege.

The rule is **enforcement in code, not description**. A description saying "only use for PDFs" is a prompt (probabilistic). A URL validator that returns `isError=true` for non-PDFs is a hook-level guarantee (deterministic). See [[1.5 agent sdk hooks]] for the same distinction.

## Scoped cross-role tools

Default: role separation is strict — a synthesis agent has NO web search. Exception: if 85%+ of the operations are trivial single-source lookups, adding a **scoped** `verify_fact(claim, source_url)` to synthesis is cheaper than a coordinator round-trip. The description must include the escalation pathway: "for complex verifications requiring cross-referencing multiple sources, escalate to the coordinator."

## Fixing an overloaded agent — priority order

| Fix                                                 | Verdict                                       |
|-----------------------------------------------------|-----------------------------------------------|
| Split the agent by role, cap each at 4–5 tools      | ✓ first move                                  |
| Replace generic tools with constrained variants     | ✓ same priority                               |
| Add scoped cross-role tools where routing is hot    | ✓ after measuring the routing cost            |
| Swap `"auto"` → `"any"` where output is structured  | ✓ zero-cost win                               |
| Force the first tool with `{"type":"tool","name":…}`| ✓ for workflow-critical first steps           |
| Few-shot examples in the system prompt              | ✗ symptom, not root cause                     |
| A routing classifier layer                          | ✗ over-engineered                             |

## Exam traps

- Giving one agent 18 tools "for flexibility". Cap at 4–5.
- `tool_choice: "auto"` when structured output is required.
- Handing subagents a generic `fetch_url` / `run_shell` / `query_db`.
- Adding a cross-role tool without an escalation clause in the description.
- Assuming a well-written description enforces least privilege — it doesn't. Enforce in code.

## Files in this section

- `tool_choice_ab.py` — three runs on the same prompt, one per `tool_choice` mode (`auto`, `any`, `{"type":"tool","name":…}`). Shows which mode returns prose vs a forced call.
- `overload_vs_scoped.py` — same query against an 18-tool "kitchen sink" agent and a 5-tool scoped agent; logs which tool got picked and whether the pick was correct.
- `constrained_url.py` — `fetch_url` (generic) vs `load_document` (validated). Same subagent, same prompts; the constrained tool rejects non-document URLs with a structured error following [[2.2 structured error responses]].
