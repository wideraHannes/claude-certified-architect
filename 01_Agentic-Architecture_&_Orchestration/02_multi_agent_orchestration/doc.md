# Multi-Agent Orchestration Patterns

Condensed notes from [1.2 Orchestration Patterns](https://claudecertificationguide.com/learn/1-agentic-architecture/1-2-orchestration-patterns).

## Hub-and-Spoke (Core Pattern)

A **coordinator** agent sits at the center, receives the initial task, decomposes it, and delegates to specialized **subagents** (e.g. web search, document analysis).

**Golden rule:** all communication flows through the coordinator. Subagents never talk to each other directly. This gives observability, consistent error handling, and controlled information flow.

## Key Principles

- **Isolation** — Subagents do NOT inherit the coordinator's conversation history or system prompt. Every piece of context a subagent needs must be explicitly passed in its prompt.
- **No shared memory** — Each subagent invocation is independent. A second call has no knowledge of the first.

## Coordinator Responsibilities

1. **Dynamic selection** — invoke only the subagents actually needed, not the full pipeline every time.
2. **Scope partitioning** — assign distinct, non-overlapping subtopics to avoid duplicate work.
3. **Iterative refinement** — evaluate subagent output, detect gaps, and re-delegate with targeted follow-up queries.
4. **Centralized routing** — keep all traffic through the hub.

## Exam Pitfall: Narrow Decomposition

If a coordinator splits "renewable energy" into only *solar* and *wind*, it silently misses geothermal, tidal, biomass, fusion. The failure is in the **coordinator's decomposition**, not the subagents. Always trace failures back to how the task was split up front.
