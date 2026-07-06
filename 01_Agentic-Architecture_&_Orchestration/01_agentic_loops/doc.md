# Agentic Loops — Rings

Progressively adding capability to a tool-using agent.

- **Ring 1 — Single tool, single turn.** One tool, one round-trip: send request → get `tool_use` → run tool → send `tool_result` → get final text. No loop.
- **Ring 2 — Agentic loop.** Same as Ring 1, but wrapped in `while stop_reason == "tool_use"` so the model can call tools repeatedly until done.
- **Ring 3 — Multiple tools.** Register several tools and handle *all* `tool_use` blocks in one assistant turn (parallel tool use), batching results back in a single user message.
- **Ring 4 — Error handling.** Wrap tool execution in `try/except`. On failure, return the error string with `is_error: true` so the model can retry, correct input, or clarify.
- **Ring 5 — Tool Runner SDK.** Replace the hand-rolled loop with `client.beta.messages.tool_runner(...).until_done()`. Tools become `@beta_tool`-decorated Python functions; schemas come from type hints and docstrings.
