"""
Overload vs scoped tool sets for 2.3.

Same three queries against:
  A) OVERLOAD  — 18 tools scraped from three roles into one agent.
  B) SCOPED    — 5 tools for the role the query actually belongs to.

We measure two things per run:
  - Did the model pick a tool relevant to the query?
  - Round-trip latency.

Reads out as an A/B table. Illustrates the 4–5-per-role rule from the guide.
"""

from __future__ import annotations

import time
from typing import Any

from config import client, settings

# ---------------------------------------------------------------------------
# Three role toolkits. Each tool is a stub — only name + description matter,
# since we never actually execute them; we just watch which one the model
# picks on the first turn.
# ---------------------------------------------------------------------------
WEB_SEARCH_TOOLS = [
    ("web_search",       "Search the public web for a query string."),
    ("web_fetch_url",    "Fetch the raw HTML of a specific URL."),
    ("news_search",      "Search recent news articles from indexed publishers."),
    ("wiki_lookup",      "Look up an encyclopedia summary of a named entity."),
    ("cached_web_search","Search results cached within the last 24h."),
]

DOC_ANALYSIS_TOOLS = [
    ("read_pdf",           "Read the text content of a local PDF path."),
    ("extract_metadata",   "Extract title, author, and creation date from a document."),
    ("summarize_document", "Produce a paragraph summary of a document."),
    ("find_citations",     "List citation strings inside a document."),
    ("ocr_scan",           "Run OCR on a scanned image or non-text PDF."),
    ("diff_documents",     "Show the textual diff between two documents."),
]

SYNTHESIS_TOOLS = [
    ("compose_report",     "Compose a multi-section report from findings."),
    ("cite_source",        "Attach a formatted citation to a claim."),
    ("verify_fact",        "SCOPED: verify a single-source factual claim."),
    ("outline_report",     "Produce a section outline from a topic and findings."),
    ("format_markdown",    "Render a structured report as Markdown."),
    ("word_count",         "Count words in a passage."),
    ("check_tone",         "Score a passage's tone (formal / neutral / casual)."),
]

ALL_TOOLS = WEB_SEARCH_TOOLS + DOC_ANALYSIS_TOOLS + SYNTHESIS_TOOLS
assert len(ALL_TOOLS) == 18, "overload set should be 18 tools"


def _to_schema(tools: list[tuple[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": desc,
            "input_schema": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }
        for name, desc in tools
    ]


# ---------------------------------------------------------------------------
# Cases. Each query names the role it should stay inside.
# ---------------------------------------------------------------------------
CASES = [
    {
        "role": "web_search",
        "query": "What was announced at the 2024 Anthropic developer conference?",
        "acceptable": {t[0] for t in WEB_SEARCH_TOOLS},
    },
    {
        "role": "doc_analysis",
        "query": "Extract the author and publication date from /docs/paper.pdf.",
        "acceptable": {t[0] for t in DOC_ANALYSIS_TOOLS},
    },
    {
        "role": "synthesis",
        "query": "Turn these three findings into a Markdown report with citations: ...",
        "acceptable": {t[0] for t in SYNTHESIS_TOOLS},
    },
]

ROLE_TOOLS = {
    "web_search":   WEB_SEARCH_TOOLS,
    "doc_analysis": DOC_ANALYSIS_TOOLS,
    "synthesis":    SYNTHESIS_TOOLS,
}


def call(tools: list[dict[str, Any]], query: str) -> tuple[str | None, float]:
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=settings.default_model,
        max_tokens=256,
        tools=tools,
        tool_choice={"type": "any"},  # force a tool pick so we can compare
        messages=[{"role": "user", "content": query}],
    )
    dt = time.perf_counter() - t0
    picks = [b.name for b in resp.content if b.type == "tool_use"]
    return (picks[0] if picks else None, dt)


def main() -> None:
    overload_schema = _to_schema(ALL_TOOLS)

    print(f"{'role':<13} {'overload pick':<22} {'ok?':<5} {'ms':<6}  "
          f"{'scoped pick':<22} {'ok?':<5} {'ms':<6}")
    print("-" * 92)
    for case in CASES:
        scoped_schema = _to_schema(ROLE_TOOLS[case["role"]])

        over_pick, over_ms = call(overload_schema, case["query"])
        scop_pick, scop_ms = call(scoped_schema, case["query"])

        over_ok = "✓" if over_pick in case["acceptable"] else "✗"
        scop_ok = "✓" if scop_pick in case["acceptable"] else "✗"

        print(
            f"{case['role']:<13} "
            f"{str(over_pick):<22} {over_ok:<5} {over_ms * 1000:<6.0f}  "
            f"{str(scop_pick):<22} {scop_ok:<5} {scop_ms * 1000:<6.0f}"
        )


if __name__ == "__main__":
    main()
