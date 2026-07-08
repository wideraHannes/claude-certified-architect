# MCP Server Integration

Notes on [2.4](https://claudecertificationguide.com/learn/2-tool-design-mcp/2-4-mcp-server-integration).

## Scoping — where the config lives

| File                | Scope         | Version-controlled? | Use for                                                       |
|---------------------|---------------|---------------------|---------------------------------------------------------------|
| `.mcp.json`         | Project       | Yes — commit it     | Servers the whole team needs (Jira, GitHub, internal APIs).   |
| `~/.claude.json`    | User          | No — personal       | Experimental servers, personal integrations, pre-team testing.|

Both scopes are loaded at connection time and **every tool from every configured server is available simultaneously**. There is no per-server activation step.

## `.mcp.json` shape

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    },
    "jira": {
      "command": "npx",
      "args": ["-y", "@community/mcp-server-jira"],
      "env": {
        "JIRA_URL":   "${JIRA_URL}",
        "JIRA_TOKEN": "${JIRA_TOKEN}"
      }
    }
  }
}
```

`${VAR}` expansion is the whole point: the config is safe to commit, each dev supplies their own creds, and rotating a token needs zero config churn.

## Resources — the catalog channel

MCP **resources** expose a data catalog to the agent so it doesn't burn tool calls discovering the landscape. Typical resources:

- **Issue summaries** — current tickets with title + status.
- **Documentation TOCs** — hierarchical docs index.
- **DB schemas** — tables, columns, relations.

Rule of thumb: if the agent's first N tool calls are always "list what's here", that's a resource, not a tool.

## Build vs. use

| Situation                                                              | Move                                 |
|------------------------------------------------------------------------|--------------------------------------|
| Standard SaaS (Jira, GitHub, Slack, Linear, Notion)                    | Use the community server.            |
| Team-specific workflow a community server can't express                | Build custom.                        |
| Proprietary internal system with no community server                   | Build custom.                        |
| "We want more control"                                                 | Not a reason — use community.        |

Exam heuristic: **"Evaluate community servers first"** is the safe answer unless the scenario explicitly names a team-specific requirement.

## Description quality — the built-in-tool trap

If an MCP tool's description is sparse, the agent will silently prefer a built-in tool with a richer description. The MCP tool is present but never called.

Poor:

```
search_codebase: "Searches code"
```

Enhanced (3–5 sentences, capabilities + when to prefer over built-ins):

```
search_codebase: "Performs semantic code search across the entire
repository using AST-aware indexing. Returns matching functions,
classes, and methods with full context including file path, line
numbers, and surrounding code. More accurate than text-based grep
for finding code by intent rather than exact string match. Use this
instead of Grep when searching for code by what it does rather than
what it contains."
```

Same principle as [[2.1 tool schema design]]: the description is the model's user manual.

## Exam traps

- Building a custom server for a standard integration that has a community server.
- Putting team-wide config in `~/.claude.json` — it's personal and won't ship to teammates.
- Committing raw credentials in `.mcp.json` instead of `${ENV_VAR}`.
- Sparse MCP tool descriptions → agent falls back to built-in tools and the MCP server looks broken.
- Assuming servers need manual activation. They don't — all discovered tools are live at once.

## Files in this section

- _(to be added — planned: a `.mcp.json` with env-var expansion, a minimal custom MCP server for a case a community server can't cover, and a before/after tool-description A/B showing the built-in-tool fallback._
