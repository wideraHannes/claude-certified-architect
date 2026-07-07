# Agent SDK Hooks

Condensed notes from [1.5 Agent SDK Hooks](https://claudecertificationguide.com/learn/1-agentic-architecture/1-5-agent-sdk-hooks).
SDK reference: [Intercept and control agent behavior with hooks](https://code.claude.com/docs/en/agent-sdk/hooks).

## Core distinction

- **Prompt-based guidance** — probabilistic (~95%). Fine for style, formatting, ordering.
- **Hooks** — deterministic (100%). Callback code the SDK runs at fixed lifecycle points. The model cannot argue its way past a hook.

Same decision rule as [[1.4 workflow enforcement]]: if a single failure means money loss, security breach, or compliance violation → use a hook, not a prompt.

## The two hooks that carry the exam

- **PreToolUse** — fires *before* a tool executes. Can block, modify input, or auto-approve.
  - Use it for policy enforcement: refund > $500, transfer before AML, discount > 20%.
  - Trap: putting a policy check in PostToolUse instead — the action already happened.
- **PostToolUse** — fires *after* a tool returns, before the model sees the result. Can rewrite the output.
  - Use it for **data normalization**: one tool returns Unix timestamps, another ISO 8601, another a human-readable date; normalize them all before the model reinterprets each format from scratch on every turn.

## Callback contract (Python SDK)

```python
async def my_hook(input_data, tool_use_id, context):
    # input_data has: hook_event_name, tool_name, tool_input, session_id, cwd, ...
    # PreToolUse decision:
    return {
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "permissionDecision": "deny",  # or "allow" | "ask" | "defer"
            "permissionDecisionReason": "why the model should stop retrying",
        }
    }
    # PostToolUse rewrite:
    return {
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "updatedToolOutput": normalized_text,
        }
    }
    # No-op:
    return {}
```

Registration:

```python
ClaudeAgentOptions(
    hooks={
        "PreToolUse":  [HookMatcher(matcher="mcp__billing__process_refund", hooks=[refund_gate])],
        "PostToolUse": [HookMatcher(matcher="mcp__billing__.*",             hooks=[normalize])],
    },
)
```

## Matcher rules that bite

- Only letters/digits/`_`/`-`/space/`,`/`|` → **exact string**, `|` separates alternatives (`"Write|Edit"`).
- Any other character → **unanchored regex** (`"^mcp__"` matches every MCP tool).
- Empty / omitted / `"*"` → matches everything.
- **Matchers filter by tool name only**, never by arguments. Filter by `tool_input.file_path` (or `.amount`) *inside* the callback.
- MCP tool names are `mcp__{server}__{tool}`.

## Multiple hooks + precedence

All matching hooks run in parallel, in non-deterministic order. Precedence: **deny > defer > ask > allow**. Write each hook to stand alone — never assume another hook ran first.

## Modifying input vs. output

- Modify a tool's *input* (PreToolUse): put `updatedInput` inside `hookSpecificOutput` **and** set `permissionDecision: "allow"` (or `"ask"`). Return a new dict — do not mutate `tool_input`.
- Modify a tool's *output* (PostToolUse): set `updatedToolOutput` inside `hookSpecificOutput`. Works for any tool in both SDKs; the older `updatedMCPToolOutput` is deprecated.

## Async / side-effect hooks

For logging or webhooks that must not block the model: return `{"async_": True, "asyncTimeout": 30000}` (note the trailing underscore in Python — `async` is reserved). Fire-and-forget only: async hooks cannot block, modify, or inject context.

## Python-specific gotchas

- `SessionStart` / `SessionEnd` are **not** available as SDK callback hooks in Python — TypeScript only. In Python register them as shell-command hooks in `.claude/settings.json` and load with `setting_sources=["project"]`, or use the first `receive_response()` message as your init trigger.
- `structuredContent` from a tool handler is TypeScript-only; the Python `@tool` decorator forwards only `content` and `is_error`.
- `agent_id` / `agent_type` are on `PreToolUse`, `PostToolUse`, `PostToolUseFailure` only.

## Exam traps

- "Use PostToolUse to block the refund" — wrong, the refund already ran. **PreToolUse**.
- "Just add a stronger system-prompt rule" — probabilistic, not deterministic; never sufficient for financial or compliance.
- "Add a routing classifier" — classifiers route between agents, they don't enforce workflow inside one.
- Assuming matchers filter by argument (file path, amount) — they don't; filter inside the callback.
- Forgetting `permissionDecision: "allow"` alongside `updatedInput` — the modified input is silently dropped.

## Files in this section

- `hooks_exercise.py` — minimal walkthrough on built-in tools (no MCP yet). Three callbacks, one per pattern:
  1. `block_env_writes` — PreToolUse on `Write`, `permissionDecision="deny"` when the path ends in `.env`.
  2. `defang_rm_rf` — PreToolUse on `Bash`, `updatedInput` swaps `rm -rf ...` for a harmless `echo`. Requires `permissionDecision="allow"` alongside.
  3. `annotate_bash_output` — PostToolUse on `Bash`, `updatedToolOutput` appends a compliance banner before the model reads the result.

  Registration is the "table of contents" — read `options.hooks` top-down to see event → matcher → callback.
