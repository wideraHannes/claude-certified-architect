# Chapter 2 — Tool Design & MCP Integration

Exam-prep quick reference. Source: [claudecertificationguide.com](https://claudecertificationguide.com/).

---

## 2.0 Two surfaces, don't mix them up

Chapter 2 straddles two Anthropic products that both use tools and both speak MCP. The exam will punish you for answering as if they were the same thing.

**Claude Code** — the coding assistant you *use* to build software.
- A CLI / IDE product. You are the user; the model helps you write code.
- MCP servers are configured via files on your machine: project-level `.mcp.json`, user-level `~/.claude.json`.
- All discovered tools are live at once — no per-server activation.
- The "team" in these scenarios is a team of developers extending their own dev environment.
- This is the surface for **§2.4 MCP Server Integration**.

**Claude Agent SDK** — the library you *use to build* agentic software.
- A Python/TS runtime you embed in your own app. The end user talks to the agent you built.
- Tools are defined in code (`@beta_tool`, `AgentDefinition(tools=[...])`), scoped per role, gated by hooks.
- MCP servers, if used, are wired through the SDK's own client APIs, not through `.mcp.json`.
- This is the surface for the design lessons in **§2.1–2.3** — tool schemas, structured errors, tool distribution and `tool_choice`.

**Rule of thumb.** If the scenario names a config file (`.mcp.json`, `~/.claude.json`) or "the dev team's Claude Code setup", it's Claude Code (§2.4). If it names `tool_choice`, an `AgentDefinition`, `isError` metadata, or "our agent app", it's SDK territory (§2.1–2.3). MCP the protocol is common to both; the *integration mechanism* is not.

---

## 2.1 Tool Schema Design (SDK)

See [`01_tool_schema_design/doc.md`](01_tool_schema_design/doc.md). Descriptions are the model's user manual; enforcement lives in code, not prose.

## 2.2 Structured Error Responses (SDK)

See [`02_structured_error_responses/doc.md`](02_structured_error_responses/doc.md). Every failure carries `errorCategory` + `isRetryable` + `description`. `isError=false, resultCount=0` is a valid empty result, not a failure.

## 2.3 Tool Distribution & Tool Choice (SDK)

See [`03_tool_distribution_choice/doc.md`](03_tool_distribution_choice/doc.md). 4–5 tools per role; constrained tools over generic ones; `tool_choice` modes matched to output requirements.

## 2.4 MCP Server Integration (Claude Code)

See [`04_mcp_server_integration/doc.md`](04_mcp_server_integration/doc.md). Project vs user config scoping, `${VAR}` expansion, community-vs-custom decision, description quality against the built-in-tool fallback.

---

## Cross-cutting themes

- **Description is a prompt (probabilistic); code is deterministic.** Same ladder as chapter 1.
- **Least privilege by construction.** Narrow tools, scoped allow-lists, validated inputs — not "the description says don't".
- **The surface dictates the mechanism.** Same MCP protocol, different wiring: `.mcp.json` in Claude Code, SDK client APIs in agent apps.
