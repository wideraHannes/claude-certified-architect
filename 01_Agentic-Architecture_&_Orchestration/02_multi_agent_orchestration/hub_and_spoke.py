"""
Hub-and-spoke multi-agent orchestration.

Coordinator (hub) decomposes a topic, dispatches each subtopic to stateless
subagents (spokes), then aggregates their outputs into a report. Subagents
share no memory — the coordinator explicitly passes all context.
"""

from pydantic import BaseModel, Field

from config import client, settings

MAX_ITERATIONS = 3


COORDINATOR_SYSTEM = """You are the coordinator in a hub-and-spoke research system.
You decompose the topic, dispatch subagents with explicit context, and aggregate their results.
You never do the research yourself."""

WEB_SEARCH_SYSTEM = """You are a web-search specialist subagent.
You gather sourced findings on the ONE subtopic the coordinator assigns you.
You have no memory of previous invocations and no awareness of other subagents."""

DOCUMENT_ANALYSIS_SYSTEM = """You are a document-analysis specialist subagent.
You extract themes and key claims from source material the coordinator provides.
You have no memory of previous invocations. You only work with material given in this prompt."""


class Subtopic(BaseModel):
    name: str
    rationale: str


class Decomposition(BaseModel):
    subtopics: list[Subtopic] = Field(min_length=5)


class Finding(BaseModel):
    subtopic_name: str
    key_points: list[str] = Field(min_length=3)
    source_urls: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class Analysis(BaseModel):
    subtopic_name: str
    themes: list[str] = Field(min_length=2)
    key_claims: list[str] = Field(min_length=2)
    confidence: float = Field(ge=0.0, le=1.0)


class Gap(BaseModel):
    subtopic_name: str
    note: str = Field(description="What specifically needs another pass")


class Review(BaseModel):
    gaps: list[Gap] = Field(
        default_factory=list,
        description="Empty when coverage is sufficient; otherwise one entry per subtopic needing rework.",
    )


def _forced_tool_call(system: str, prompt: str, schema_model: type[BaseModel], tool_name: str):
    tool = {
        "name": tool_name,
        "description": f"Record structured output for {tool_name}.",
        "input_schema": schema_model.model_json_schema(),
    }
    response = client.messages.create(
        model=settings.default_model,
        max_tokens=2048,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return schema_model.model_validate(tool_use.input)


def decompose(topic: str) -> Decomposition:
    prompt = (
        f"Decompose this research topic into at least 5 subtopics covering the "
        f"full breadth (do not focus on one dimension): {topic}"
    )
    return _forced_tool_call(COORDINATOR_SYSTEM, prompt, Decomposition, "record_decomposition")


def _gap_line(note: str | None) -> str:
    if not note:
        return ""
    return f"\nTARGETED FOLLOW-UP — previous pass was inadequate: {note}\n"


def web_search_subagent(
    subtopic: Subtopic, research_goal: str, gap: str | None = None
) -> Finding:
    prompt = (
        f"Assigned subtopic: {subtopic.name}\n"
        f"Why it matters: {subtopic.rationale}\n"
        f"Broader research goal (context only): {research_goal}\n"
        f"{_gap_line(gap)}\n"
        f"Return >=3 key points, source URLs, and a confidence 0..1."
    )
    return _forced_tool_call(WEB_SEARCH_SYSTEM, prompt, Finding, "record_findings")


def document_analysis_subagent(
    subtopic: Subtopic,
    research_goal: str,
    prior_findings: Finding,
    gap: str | None = None,
) -> Analysis:
    points = "\n".join(f"- {p}" for p in prior_findings.key_points)
    prompt = (
        f"Assigned subtopic: {subtopic.name}\n"
        f"Broader research goal (context only): {research_goal}\n\n"
        f"Source material (from web_search subagent — the ONLY material available to you):\n"
        f"{points}\n"
        f"Sources: {prior_findings.source_urls}\n"
        f"{_gap_line(gap)}\n"
        f"Return >=2 themes, >=2 key claims, and a confidence 0..1."
    )
    return _forced_tool_call(DOCUMENT_ANALYSIS_SYSTEM, prompt, Analysis, "record_analysis")


def _run_spoke(sub: Subtopic, topic: str, gap: str | None = None) -> Analysis:
    findings = web_search_subagent(sub, topic, gap=gap)
    return document_analysis_subagent(sub, topic, findings, gap=gap)


def review_report(topic: str, report: str, subtopic_names: list[str]) -> Review:
    prompt = (
        f"Original topic: {topic}\n"
        f"Subtopics under review: {subtopic_names}\n\n"
        f"Current report:\n{report}\n\n"
        f"Read the report and identify subtopics whose coverage is not good enough. "
        f"For each, give a specific note on what to improve. "
        f"Return an empty gaps list if the report is sufficient."
    )
    return _forced_tool_call(COORDINATOR_SYSTEM, prompt, Review, "record_review")


def coordinator(topic: str) -> str:
    decomposition = decompose(topic)
    by_name = {s.name: s for s in decomposition.subtopics}
    print(
        f"[coordinator] decomposed into {len(by_name)} subtopics: {list(by_name)}"
    )

    # Initial pass: dispatch every spoke and accumulate results.
    results: dict[str, Analysis] = {}
    for sub in decomposition.subtopics:
        results[sub.name] = _run_spoke(sub, topic)
    report = _format_report(topic, decomposition, results)

    # Iterative refinement: coordinator reads the report, flags weak subtopics,
    # re-dispatches those spokes with feedback, and re-accumulates.
    for i in range(1, MAX_ITERATIONS + 1):
        gaps = [
            g for g in review_report(topic, report, list(by_name)).gaps
            if g.subtopic_name in by_name
        ]
        print(f"[coordinator] iter {i}: {len(gaps)} gap(s) {[g.subtopic_name for g in gaps]}")
        if not gaps:
            break
        for g in gaps:
            results[g.subtopic_name] = _run_spoke(by_name[g.subtopic_name], topic, gap=g.note)
        report = _format_report(topic, decomposition, results)

    return report


def _format_report(
    topic: str, decomposition: Decomposition, results: dict[str, Analysis]
) -> str:
    lines = [f"# Research report: {topic}", ""]
    for sub in decomposition.subtopics:
        a = results[sub.name]
        lines.append(f"## {sub.name}")
        lines.append("Themes: " + "; ".join(a.themes))
        lines.append("Key claims:")
        lines.extend(f"  - {c}" for c in a.key_claims)
        lines.append(f"Confidence: {a.confidence:.2f}\n")
    return "\n".join(lines)


REQUIRED_CATEGORIES = {"solar", "wind", "geothermal", "tidal", "biomass", "fusion"}


def _verify_required_categories(report: str) -> None:
    lower = report.lower()
    missing = {c for c in REQUIRED_CATEGORIES if c not in lower}
    print("\n" + "=" * 60)
    if missing:
        print(f"FAIL: missing exam-required categories: {sorted(missing)}")
    else:
        print(f"PASS: all six required categories covered: {sorted(REQUIRED_CATEGORIES)}")
    print("=" * 60)


if __name__ == "__main__":
    report = coordinator("renewable energy technologies")
    print("\n" + report)
    _verify_required_categories(report)
