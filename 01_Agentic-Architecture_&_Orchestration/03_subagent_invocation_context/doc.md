# Subagent Invocation and Context Passing

Notes for [1.3 Subagent Invocation and Context](https://claudecertificationguide.com/learn/1-agentic-architecture/1-3-subagent-invocation-context).

Uses `claude-agent-sdk`. For the SDK mental model (message stream, structured-output gap, sessions, auth), see [`agent_sdk.md`](./agent_sdk.md) — this doc assumes that intuition.

## Rule zero + the three context-passing rules

0. **`"Agent"` in `allowed_tools`** (alias `"Task"`). Without it, no subagent can be spawned. Ever.
1. **Complete transfer.** Subagents inherit *nothing* — not coordinator history, not sibling output. Inline every fact in the Agent tool prompt.
2. **Metadata separation.** Bundle each claim with `source_url`, `document_name`, `page_number`, `retrieved_by`. Pass the array **verbatim** downstream — never summarize.
3. **Goal-oriented prompts.** Specify outcomes and quality criteria, not procedures. Lets subagents adapt when the plan meets reality.

## Findings shape

```json
{"findings":[{"claim":"…","source_url":"…","document_name":"…","page_number":0,"confidence":"…","retrieved_by":"…"}]}
```

Embed this schema string in *every* prompt (coordinator + producers + synthesis) so shapes agree.

## Build exercise — the 6 steps (implemented in `coordinator.py`)

1. Coordinator with `allowed_tools=["Agent"]` **and nothing else** — physically cannot research, only delegate.
2. Two producers: `web_search` (WebSearch/WebFetch), `doc_analyst` (Read/Grep/Glob). Least-privilege by role.
3. Metadata schema shared across all agents.
4. Coordinator forwards the concatenated findings array **verbatim** to the synthesis subagent.
5. Every claim in the final report carries a citation. Failure ⇒ debug coordinator context-passing, not the synthesis prompt.
6. Emit both producer Agent tool calls in the **same assistant response**. Sequential turns = latency regression.

## Parallel spawn — how to detect it

Count `ToolUseBlock`s named `"Agent"`/`"Task"` inside a single `AssistantMessage` whose `parent_tool_use_id is None` (coordinator's own turn). ≥2 = parallel. 1-per-turn across turns = sequential regression.

## Exam pitfalls

1. Assuming subagents inherit context or peer output.
2. Blaming the synthesis agent for missing citations when the coordinator stripped metadata upstream.
3. Sequential invocation of independent producers.
4. Confusing `fork_session` (branch) with `resume` (continue).
5. Forgetting `permission_mode="acceptEdits"` in headless scripts — the run hangs on approval prompts.

## Root-cause rule

Unsourced claims from synthesis ⇒ fix the **coordinator's context-passing**, not the synthesis prompt. A subagent cannot cite a source it never received.
