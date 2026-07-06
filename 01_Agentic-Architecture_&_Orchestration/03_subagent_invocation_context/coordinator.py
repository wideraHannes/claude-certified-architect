"""
Build Exercise — Subagent Invocation & Context Passing.

Implements the 6-step exercise from
https://claudecertificationguide.com/learn/1-agentic-architecture/1-3-subagent-invocation-context
on top of the current Claude Agent SDK.

Design:
  - Coordinator with Agent in allowed_tools (Step 1: without it, no delegation).
  - Two research subagents scoped by role (Step 2):
      web_search   — WebSearch / WebFetch only
      doc_analyst  — Read / Grep / Glob only, pointed at ./sources
  - One synthesis subagent that MUST cite every claim (Steps 3-5).
  - Coordinator system prompt orders parallel invocation of the two research
    agents in a single response (Step 6) and mandates that every finding is
    forwarded to the synthesis agent WITH metadata intact (Rule 2 / Step 4).
  - After the run, we grep the transcript for source_url / page_number tokens
    as a coarse attribution check (Step 5).
"""

from __future__ import annotations

import anyio
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
    query,
)


SOURCES_DIR = Path(__file__).parent / "sources"


FINDINGS_SCHEMA = """{
  "findings": [
    {
      "claim":         "<single factual statement>",
      "source_url":    "<URL, or empty string if a local file>",
      "document_name": "<filename or site title>",
      "page_number":   <integer, 0 if not applicable>,
      "confidence":    "<high|medium|low>",
      "retrieved_by":  "<agent name>"
    }
  ]
}"""


COORDINATOR_PROMPT = f"""You are the research coordinator in a multi-agent pipeline.

Your job is orchestration, not research. You never read files, search the web,
or write prose yourself. You delegate to three named subagents via the Agent tool:

  - web_search   — gathers web findings on the topic
  - doc_analyst  — extracts findings from local files under ./sources
  - synthesis    — produces the final cited report

RULES (do not violate):

1. Complete information transfer. Subagents inherit NOTHING from you or from
   each other. Every fact a subagent needs must be inlined in the Agent tool
   prompt you write for it.

2. Structured metadata separation. Every finding is a JSON object of the shape:
{FINDINGS_SCHEMA}
   When you forward findings to the synthesis agent, you MUST pass the full
   array verbatim. Do not summarize. Do not strip source_url, document_name,
   page_number, or retrieved_by.

3. Goal-oriented prompting. Tell each subagent what "done" looks like, not the
   procedural steps.

PROTOCOL:

Turn 1 — Emit TWO Agent tool calls in the SAME response (parallel spawn):
  a) web_search agent, prompted with the topic and the required JSON shape.
  b) doc_analyst agent, prompted with the topic, the absolute path
     {SOURCES_DIR}, and the required JSON shape.

Turn 2 — After both return, emit ONE Agent tool call to the synthesis agent.
  Its prompt must contain: the topic, and the CONCATENATED findings arrays from
  both research agents, with every metadata field intact.

Turn 3 — Reply with the synthesis agent's final report verbatim as your text
  answer. Do not add commentary.
"""


WEB_SEARCH_PROMPT = f"""You are a web-search specialist. You have WebSearch and
WebFetch and nothing else. You have no memory of past runs and no awareness of
sibling agents.

Return ONLY a JSON object matching this schema — no prose, no code fences:
{FINDINGS_SCHEMA}

Rules:
- Every claim must have a real source_url you actually fetched or searched.
- Set retrieved_by to "web_search".
- page_number is 0 for web pages.
- Aim for 3-6 findings covering the assigned topic broadly.
"""


DOC_ANALYST_PROMPT = f"""You are a document analyst. You have Read, Grep, and
Glob and nothing else. You have no memory of past runs and no awareness of
sibling agents.

The coordinator will give you an absolute directory path. Use Glob to list its
files, Read them, and extract factual claims. The files use a "Page N" heading
convention — treat each such block as a page and record its number.

Return ONLY a JSON object matching this schema — no prose, no code fences:
{FINDINGS_SCHEMA}

Rules:
- source_url is "" for local files.
- document_name is the file's basename.
- page_number is the integer from the "Page N" heading the claim came from.
- Set retrieved_by to "doc_analyst".
"""


SYNTHESIS_PROMPT = """You are a synthesis writer. You have NO research tools —
only what the coordinator inlines in your prompt.

You will receive a topic and a JSON array of findings, each with a claim plus
metadata (source_url, document_name, page_number, retrieved_by).

Produce a markdown report with these rules:
- Every factual sentence ends with an inline citation in the form
  [source_url] for web findings, or [document_name p.N] for document findings.
- Never invent a citation. If a claim has no metadata, drop the claim.
- Group by theme, not by source.
- Close with a "## Sources" section listing each unique source once.
"""


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=COORDINATOR_PROMPT,
        model="sonnet",
        # Step 1: Agent MUST be in allowed_tools or no subagent can be spawned.
        # The coordinator itself gets nothing else — it cannot do research.
        allowed_tools=["Agent"],
        agents={
            "web_search": AgentDefinition(
                description=(
                    "Use this agent to gather web-sourced findings on a topic. "
                    "Returns a JSON findings array with source_url per claim."
                ),
                prompt=WEB_SEARCH_PROMPT,
                tools=["WebSearch", "WebFetch"],
                model="sonnet",
            ),
            "doc_analyst": AgentDefinition(
                description=(
                    "Use this agent to extract findings from local files under "
                    "a directory the coordinator names. Returns a JSON findings "
                    "array with document_name and page_number per claim."
                ),
                prompt=DOC_ANALYST_PROMPT,
                tools=["Read", "Grep", "Glob"],
                model="sonnet",
            ),
            "synthesis": AgentDefinition(
                description=(
                    "Use this agent LAST to turn the concatenated findings "
                    "array into a cited markdown report. It has no tools; "
                    "the coordinator must inline every finding in its prompt."
                ),
                prompt=SYNTHESIS_PROMPT,
                tools=[],
                model="sonnet",
            ),
        },
        permission_mode="acceptEdits",
    )


async def run(topic: str) -> str:
    options = _build_options()

    parallel_spawn_seen = False
    subagent_calls: list[str] = []
    final_text = ""

    async for msg in query(prompt=topic, options=options):
        if isinstance(msg, SystemMessage):
            continue

        if isinstance(msg, AssistantMessage):
            tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]
            agent_calls_in_turn = [
                b for b in tool_uses if b.name in ("Agent", "Task")
            ]
            if len(agent_calls_in_turn) >= 2 and msg.parent_tool_use_id is None:
                parallel_spawn_seen = True
            for b in agent_calls_in_turn:
                sub = b.input.get("subagent_type") or b.input.get("agent") or "?"
                origin = "coordinator" if msg.parent_tool_use_id is None else "subagent"
                subagent_calls.append(f"{origin} -> {sub}")
                print(f"[{origin}] spawn {sub}")

        if isinstance(msg, UserMessage):
            # tool_result blocks show up here; we don't dump them (too noisy).
            continue

        if isinstance(msg, ResultMessage):
            final_text = msg.result or ""

    print("\n--- orchestration trace ---")
    for c in subagent_calls:
        print(f"  {c}")
    print(
        f"parallel spawn in a single turn: {'YES' if parallel_spawn_seen else 'NO'}"
    )
    return final_text


def _verify_attribution(report: str) -> None:
    print("\n" + "=" * 60)
    checks = {
        "web citation present":  "http" in report,
        "page citation present": "p." in report.lower(),
        "sources section":       "## Sources" in report or "## sources" in report.lower(),
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print("=" * 60)


if __name__ == "__main__":
    report = anyio.run(
        run,
        "The state of renewable energy technologies in 2024 — solar, wind, "
        "geothermal, tidal, biomass, and fusion.",
    )
    print("\n" + report)
    _verify_attribution(report)
