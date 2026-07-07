# Chapter 1 — Agentic Architecture & Orchestration

Exam-prep quick reference. Source: [claudecertificationguide.com](https://claudecertificationguide.com/).

Central theme: **prompts are probabilistic; code (loops, hooks, gates, schemas) is deterministic.** Whenever failure means money, security, or compliance, escalate from prompt guidance to a code-enforced mechanism.

---

## 1.0 What are we even looking at? — Messages API vs Claude Agent SDK

Two Anthropic surfaces show up in this chapter. They solve different problems and the exam expects you to pick the right one.

**Messages API (`anthropic.Anthropic().messages.create`)**
- The raw HTTP endpoint. One request = one model turn. You send `messages` + `tools`, you get back `content` blocks (`text`, `tool_use`) plus a `stop_reason`.
- **You own the loop.** If `stop_reason == "tool_use"`, *you* execute the tools, append `tool_result` blocks, and call the API again. Nothing is remembered server-side; state lives entirely in the `messages` list you resend each turn.
- You own tool dispatch, `tool_use_id` pairing, parallel fan-out, retries, and `is_error` handling.
- **Ergonomic layer on top**: `client.beta.messages.tool_runner(...).until_done()` with `@beta_tool` functions — same API, just wraps the while-loop. This is what §1.1 Ring 5 shows.
- Use when you want maximum control, custom transport, custom orchestration, or the loop *is* the exercise (§1.1, §1.2, §1.4 in this repo).

**Claude Agent SDK (`claude-agent-sdk` Python package)**
- A higher-level agent runtime. Under the hood it **shells out to the local `claude` CLI as its transport** and inherits the CLI's auth (Claude Code login or `ANTHROPIC_API_KEY`) — it does *not* hit the Messages API directly from your Python process.
- Gives you: named `AgentDefinition`s with scoped tool allow-lists, the `Agent`/`Task` delegation tool, **hooks** (`PreToolUse`/`PostToolUse`), `permission_mode`, `fork_session` / `--resume`, and streaming `AssistantMessage` events with `parent_tool_use_id` attribution.
- The loop, tool dispatch, and subagent orchestration are handled for you. What you configure is **policy**: which agents exist, what tools they can touch, what hooks fire, and how sessions are persisted.
- Use when the exercise is *about* subagents, hooks, or session state (§1.3, §1.5, §1.7).

**Why this repo mixes both**
`config.py` wires the Messages-API client through a Requesty EU router with Vertex-hosted model IDs (`vertex/claude-sonnet-4-6@europe-west1`). Sections whose subject is the Agent SDK itself bypass `config.py` — the SDK uses the CLI's transport and short model aliases (`"sonnet"`, `"opus"`, `"haiku"`). Same underlying model family, different control surface.

**Mental model**
| Concern | Messages API | Agent SDK |
|---|---|---|
| Who runs the loop | you | the SDK |
| Where state lives | your `messages` list | SDK session (resumable) |
| Subagent delegation | you build it (hub-and-spoke) | built-in via `Agent` tool |
| Deterministic gates | you code them into tools | code them into tools **or** hooks |
| Model IDs (this repo) | Vertex form via Requesty | short aliases via CLI |
| Auth | `ANTHROPIC_API_KEY` (or router key) | CLI login / `ANTHROPIC_API_KEY` |

Rule of thumb: **Messages API = mechanism, Agent SDK = policy.** The chapter's core patterns (hub-and-spoke, structured hand-offs, prerequisite gates, attention dilution) apply on either surface — you'll see the same lessons implemented twice.

---

## 1.1 Agentic Loops

**Golden rules**
- Loop shape: `while stop_reason == "tool_use": run tools → append results → resample`. Terminate on `end_turn`.
- Preserve turn pairing: append the full assistant `content` (all `tool_use` blocks) then a user message with the matching `tool_result` blocks. Never drop or reorder.
- Bind results by `tool_use_id`, not tool name.
- Handle **every** `tool_use` block in a turn — Claude parallelizes; return all results in one follow-up user message.
- On tool failure, return the message with `is_error: true` — do not raise. This lets Claude retry with corrected input.
- Loop is stateful only through `messages`; the SDK remembers nothing for you.
- Cap iterations/tokens defensively.

**Pitfalls**
- Missing assistant turn before the tool_result user turn → API 400.
- Returning only *some* results when the model emitted several tool_use blocks.
- Treating `stop_reason == "tool_use"` as an error rather than the normal continue signal.

**Target abstraction**
`client.beta.messages.tool_runner(...).until_done()` with `@beta_tool` functions replaces the hand-rolled loop, parallel fan-out, and `is_error` conversion. Rings 1–4 are scaffolding; Ring 5 is production shape.

---

## 1.2 Multi-Agent Orchestration

**Golden rules**
- **Hub-and-spoke**: one coordinator decomposes, dispatches, aggregates. Subagents never talk peer-to-peer.
- Subagents are **stateless** — no inherited history, no shared prompt, no memory of siblings.
- Coordinator: (1) decompose broadly, (2) dispatch only what's needed, (3) assign non-overlapping scopes, (4) detect gaps, (5) re-delegate with targeted follow-ups. Cap iterations.
- Enforce decomposition **breadth** via schema constraints (e.g. `min_length=5` on subtopic lists).
- Specialize spokes by role (search, analysis, synthesis) with their own system prompts.
- Coordinator itself does no research — only orchestrates.

**Pitfalls**
- Narrow decomposition (the flagship exam trap): splitting "renewable energy" into solar + wind silently drops geothermal, tidal, biomass, fusion.
- Assuming a subagent remembers prior turns or knows about siblings.
- Peer-to-peer subagent calls bypassing the hub.
- Skipping the review/re-dispatch loop.

**Structured-output pattern**
Define a Pydantic `BaseModel`, expose via `model_json_schema()` as a tool, force with `tool_choice={"type":"tool","name":...}`, parse `tool_use.input` back through the model. Preferred over prose parsing at every hop.

---

## 1.3 Subagent Invocation & Context (Agent SDK)

**Golden rules**
- `"Agent"` (alias `"Task"`) must appear in `allowed_tools` — without it, delegation silently fails.
- Every subagent invocation is a **clean-room turn**: only its `AgentDefinition.prompt` + the exact string the coordinator inlines. If it isn't in that string, it does not exist for the child.
- Each subagent gets a scoped `tools` allow-list — least-privilege per role.
- Pass findings as a strict JSON schema (`claim + source_url + document_name + page_number + confidence + retrieved_by`); forward verbatim, never summarize.
- Coordinator prompt is **goal-oriented** (define done + output shape), not a procedural checklist.
- Spawn independent producers in **parallel** — multiple Agent ToolUseBlocks in one AssistantMessage. Sequential fan-out of independent work is a regression.
- Synthesis agent should have **no tools** — forces citation discipline upstream.
- Headless: set `permission_mode="acceptEdits"`.
- Distinguish `fork_session` (branch from checkpoint) from `resume` (continue same session).
- Attribute streamed events via `AssistantMessage.parent_tool_use_id`.

**Pitfalls**
- Assuming subagents see parent context or each other's output.
- Stripping metadata before synthesis then blaming synthesis for missing citations.
- Sequential dispatch of independent work.
- Confusing `fork_session` with `resume`.

---

## 1.4 Workflow Enforcement & Handoff

**Golden rules**
- Enforce preconditions **inside the tool handler**, not in the system prompt — the model literally cannot argue past a return-early check.
- Track prerequisite state (`session.verified_customer_id`) server-side, never in the model's context.
- Gate must also block the **mismatched-identity** case, not just "none".
- Handoffs to humans require 5 populated fields: `customer_id`, `conversation_summary`, `root_cause`, `refund_amount` (0 if none, numeric), `recommended_action`. Humans do **not** see the transcript.
- Force structured output via Pydantic-as-tool + `tool_choice`. Use `min_length`, `ge=0` to reject placeholders ("n/a").
- Multi-concern requests: decompose → investigate in parallel with shared context → synthesize one resolution.
- Verify determinism by direct-calling the tool function in tests.

**Pitfalls / exam traps**
- "Improve the prompt / add few-shot" as the fix for a financial or compliance failure.
- "Add a routing classifier" — routes between agents; does not enforce a workflow within one.
- Handoff object missing a field, or containing placeholder text.
- Gating only on `verified == None`, forgetting identity mismatch.

**Prerequisite-gate pattern**
Early-return in the tool: `process_refund` returns `"BLOCKED: call get_customer first"` if `session.verified_customer_id` is unset or mismatched. Model self-corrects on receiving the block. Turns a ~8% prompt-guidance failure rate into 0%.

---

## 1.5 Agent SDK Hooks

**Golden rules**
- Hooks are 100% deterministic — use whenever money, security, or compliance is on the line.
- Policy/enforcement → **PreToolUse**. Data shaping → **PostToolUse**.
- Matchers filter by **tool name only** — inspect arguments in the callback.
- Matcher syntax: alnum/`_`/`-`/`,`/`|`/space = exact + alternatives; anything else = unanchored regex; empty or `"*"` = all. MCP tools: `mcp__{server}__{tool}`.
- Multiple matching hooks run in **parallel, non-deterministic order**. Precedence: **deny > defer > ask > allow**. Write each hook standalone.
- To modify input in Pre: return `updatedInput` **and** `permissionDecision: "allow"` (else silently dropped).
- To modify output in Post: return `updatedToolOutput`.
- Fire-and-forget: `{"async_": True, "asyncTimeout": 30000}`.

**Lifecycle**
- `PreToolUse` — before tool runs; allow/ask/defer/deny or rewrite input.
- `PostToolUse` — after tool returns, before model sees result; can rewrite output.
- `SessionStart` / `SessionEnd` — TS only; Python emulates via `.claude/settings.json` shell hooks + `setting_sources=["project"]`.

**Callback contract**
`async def hook(input_data, tool_use_id, context)` returning `{"hookSpecificOutput": {...}}` or `{}`. Registered via `ClaudeAgentOptions.hooks` → `HookMatcher`.

**Pitfalls**
- Using PostToolUse to block — action already ran.
- Substituting "a stronger prompt" for a hook on financial/compliance paths.
- Expecting matchers to filter by tool argument.
- Returning `updatedInput` without `permissionDecision: "allow"`.
- Assuming hook order is stable.

---

## 1.6 Task Decomposition

**Golden rules**
- **Fixed pipeline** (steps known upfront: code review, extraction, compliance) vs **dynamic decomposition** (plan emerges: exploration, audits, debugging).
- Choose by **shape**, not size. Structured → pipeline. Open-ended → dynamic.
- **Attention dilution is structural**: more items per context ⇒ less attention per item. Symptoms: deep on the first few, shallow on the rest, inconsistent judgment.
- Fix dilution with **per-item local passes + one cross-item integration pass** (e.g. 14 files → 14 focused calls + 1 integration call).
- Dynamic decomposition when the plan itself is part of the work.

**Pitfalls**
- Reaching for a stronger model, larger context, or "better" prompt to fix a structural attention problem.
- Forcing a fixed pipeline onto open-ended work.
- Batching items with no integration pass — misses cross-cutting concerns.

**Decompose vs not**
Decompose: many similar items (dilution risk); open-ended plan; steps benefit from isolated context. Don't: small cohesive task, single-shot narrow scope, splitting would sever needed context.

---

## 1.7 Session State & Resumption

**Golden rules**
- Three options: `--resume <session>`, `fork_session`, or fresh-start + summary injection.
- `--resume` restores full history **and cached tool results**. Only safe if files are unchanged since session end.
- `fork_session` branches from a shared baseline for comparing divergent strategies — not for continuation, and it inherits parent cache.
- After any file edits: fresh session seeded with a curated summary of the delta.
- Cached tool results are **first-class state** — they outlive the files they described and silently poison reasoning.
- Persist findings as structured docs during the original session so summaries are cheap later.

**Pitfalls**
- Resuming after edits, then trusting fix suggestions that reference old code.
- Believing "please re-read the file" cleans stale tool results — it doesn't; the stale entries still bias tangential reasoning.
- Using `fork_session` to escape stale context — the fork inherits it.
- Conflating `fork_session` with `--resume`.
- Full re-exploration for a 3-file delta.

**Resume vs fork (one-liner)**
`--resume` linearly continues one session with cached history intact; `fork_session` creates a sibling branch off a shared baseline for parallel alternative strategies. Neither escapes stale context from out-of-band edits.

---

## Cross-cutting themes

- **Determinism escalation ladder**: prompt → structured output (tool_choice) → code gate → hook. Match the rung to the failure cost.
- **Context is not shared unless you pass it.** True for subagents, true across sessions, true across turns after edits.
- **Cached state can rot silently.** Tool results, verified-identity fields, session history.
- **Parallelize independent work; serialize dependencies.** Applies to tool_use blocks in one turn and to Agent invocations from the coordinator.
- **Schema-first hand-offs** (Pydantic-as-tool + `tool_choice`) recur across 1.2, 1.3, 1.4.
