# Agent SDK Hooks

Notes on [1.5](https://claudecertificationguide.com/learn/1-agentic-architecture/1-5-agent-sdk-hooks). SDK ref: [hooks](https://code.claude.com/docs/en/agent-sdk/hooks).

## Prompt vs. hook

- **Prompt** — ~95%, probabilistic.
- **Hook** — 100%, deterministic callback at a lifecycle point. Model can't argue past it.

Same rule as [[1.4 workflow enforcement]]: money/security/compliance ⇒ hook.

## Two hooks

- **PreToolUse** — before the tool runs. Block, modify input, or auto-approve. Policy enforcement lives here (refund > $500, AML gate).
- **PostToolUse** — after tool returns, before model sees result. Rewrite output. Use for **data normalization** (timestamp formats, unit conversions).

Trap: policy in PostToolUse — the action already ran.

## Callback shape

```python
async def my_hook(input_data, tool_use_id, context):
    return {"hookSpecificOutput": {
        "hookEventName": input_data["hook_event_name"],
        "permissionDecision": "deny",  # allow | ask | defer
        "permissionDecisionReason": "...",
    }}
```

Modify input (Pre): `updatedInput` + `permissionDecision: "allow"`. Modify output (Post): `updatedToolOutput`.

## Matchers

- Only `[A-Za-z0-9_\- ,|]` → exact string; `|` = alternatives.
- Any other char → unanchored regex.
- Empty/`"*"` → matches everything.
- **Filter by tool name only.** Filter arguments inside the callback.
- MCP tools: `mcp__{server}__{tool}`.

## Precedence

All matching hooks run in parallel, non-deterministic order. Precedence: **deny > defer > ask > allow**. Write each to stand alone.

## Python gotchas

- `SessionStart`/`SessionEnd` — TypeScript only. In Python use `.claude/settings.json` shell hooks with `setting_sources=["project"]`.
- Async side-effect hooks: `{"async_": True, "asyncTimeout": 30000}`. Fire-and-forget only.

## Exam traps

- "PostToolUse to block the refund" — too late; use PreToolUse.
- "Stronger prompt" — probabilistic, insufficient for financial/compliance.
- Matchers filtering by argument — they don't.
- `updatedInput` without `permissionDecision: "allow"` — silently dropped.
