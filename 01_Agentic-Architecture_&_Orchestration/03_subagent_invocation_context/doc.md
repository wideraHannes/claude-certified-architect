# Subagent Invocation and Context Passing

Notes on [1.3](https://claudecertificationguide.com/learn/1-agentic-architecture/1-3-subagent-invocation-context). Uses `claude-agent-sdk` — see [`agent_sdk.md`](./agent_sdk.md) for SDK basics.

## Rules

0. **`"Agent"` in `allowed_tools`** (alias `"Task"`). Without it, no subagent spawns.
1. **Complete transfer.** Subagents inherit nothing. Inline every fact.
2. **Metadata separation.** Bundle each claim with `source_url`, `document_name`, `page_number`, `retrieved_by`. Pass verbatim — never summarize.
3. **Goal-oriented prompts.** Outcomes and criteria, not procedures.

## Findings shape

```json
{"findings":[{"claim":"…","source_url":"…","document_name":"…","page_number":0,"confidence":"…","retrieved_by":"…"}]}
```

Same schema in every prompt (coordinator + producers + synthesis).

## Parallel spawn detection

≥2 `Agent`/`Task` `ToolUseBlock`s in one `AssistantMessage` with `parent_tool_use_id is None` = parallel. 1-per-turn across turns = sequential regression.

## Exam traps

- Assuming subagents inherit context or peer output.
- Blaming synthesis for missing citations when coordinator stripped metadata.
- Sequential invocation of independent producers.
- Confusing `fork_session` (branch) with `resume` (continue).
- Forgetting `permission_mode="acceptEdits"` in headless scripts.

## Root cause

Unsourced claims from synthesis ⇒ fix coordinator's context-passing, not the synthesis prompt.
