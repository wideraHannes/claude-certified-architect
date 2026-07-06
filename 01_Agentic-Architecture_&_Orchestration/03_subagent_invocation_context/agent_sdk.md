# Agent SDK — intuition

> Build production AI agents with Claude Code as a library. Same tools, agent loop, and context management that power Claude Code — programmable.
> — [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)

## Client SDK vs. Agent SDK

**Client SDK** = direct API access; you implement the tool loop.
**Agent SDK** = Claude with built-in tool execution; the loop is already written.

```python
# Client SDK — you write the loop
response = client.messages.create(...)
while response.stop_reason == "tool_use":
    result = your_tool_executor(response.tool_use)
    response = client.messages.create(tool_result=result, **params)

# Agent SDK — Claude runs the loop
async for message in query(prompt="Fix the bug in auth.py"):
    print(message)
```

That is the whole shift. Everything else — built-in tools (`Read`/`Bash`/`Agent`/…), subagents via `AgentDefinition`, hooks, MCP, sessions — is just capability Claude Code already has, exposed as a library.

## Three primitives

- **`ClaudeAgentOptions`** — declarative spec: `system_prompt`, `model`, `allowed_tools`, `agents`, `permission_mode`, hooks, MCP.
- **`query(prompt, options)`** — async generator that runs the loop and streams messages (`SystemMessage` → `AssistantMessage` → `UserMessage` → terminal `ResultMessage.result`).
- **`AgentDefinition`** — one subagent slot in `options.agents`: `description` (routing hint), `prompt` (its system prompt), `tools` (its allow-list), optional `model`. Attribute streamed events via `AssistantMessage.parent_tool_use_id`.

## Structured output — the honest gap

The Client SDK has a clean typed-output pattern: expose a Pydantic `model_json_schema()` as a tool, force it with `tool_choice={"type":"tool","name":…}`, parse `tool_use.input`.

**Agent SDK has no equivalent** — no `output_schema`, no `response_format`, no forced `tool_choice` on `AgentDefinition`. A subagent's return value is the final text of its inner agent loop. Deliberate: the consumer is another Claude turn, not Python.

Workarounds, weakest → strongest:

1. **Prompt-only JSON** — fragile; one apologetic sentence breaks `json.loads`.
2. **In-process MCP tool as a typed sink** — register `record_findings(findings: list[Finding])`, tell the subagent its final action must call it, capture the structured `input` from the stream or a `PreToolUse` hook. Direct analog of Client-SDK forced `tool_choice`.
3. **Hook-based validate-and-retry** — `PostToolUse`/`Stop` hook validates against a Pydantic model, rejects with feedback on failure.

## Repo gotcha: auth & model IDs

Transport is a subprocess to the local `claude` CLI, so it uses **CLI auth** (Claude Code login or `ANTHROPIC_API_KEY`) — **not** this repo's Requesty router in `config.py`. Model IDs are the short aliases `"sonnet"` / `"opus"` / `"haiku"`; the Vertex form used elsewhere in this repo will not resolve.
