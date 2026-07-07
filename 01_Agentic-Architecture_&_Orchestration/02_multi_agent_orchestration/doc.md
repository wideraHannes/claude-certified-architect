# Multi-Agent Orchestration Patterns

Notes on [1.2](https://claudecertificationguide.com/learn/1-agentic-architecture/1-2-orchestration-patterns).

## Hub-and-spoke

Coordinator decomposes the task and delegates to specialized subagents. **All traffic through the hub** — subagents never talk to each other.

## Rules

- **Isolation** — subagents inherit no history or system prompt. Pass every needed fact in the prompt.
- **No shared memory** — each invocation is independent.

## Coordinator does

1. Invoke only the subagents needed.
2. Assign non-overlapping scopes.
3. Detect gaps in output, re-delegate with follow-up queries.

## Exam trap

Narrow decomposition. Splitting "renewable energy" into only solar + wind silently drops geothermal, tidal, biomass. Failures trace back to the split, not the subagent.
