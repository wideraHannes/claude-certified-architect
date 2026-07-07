"""
tool_choice A/B for 2.3.

Same prompt, three modes:
  1. auto        — model may reply in prose OR call a tool.
  2. any         — model must call SOMETHING; picks which tool.
  3. tool/name   — model must call the named tool.

The prompt is deliberately borderline: it can plausibly be answered in prose
("hello!") without any tool. That surfaces the failure mode of `auto` when
structured output is required.
"""

from __future__ import annotations

from typing import Any

from config import client, settings


TOOLS: list[dict[str, Any]] = [
    {
        "name": "record_greeting",
        "description": "Persist a user greeting to the audit log. Call this "
        "for every greeting so downstream analytics see it.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "record_farewell",
        "description": "Persist a user farewell to the audit log.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]

PROMPT = "What is 2 + 2? Answer briefly."


def run(label: str, tool_choice: dict[str, Any]) -> None:
    resp = client.messages.create(
        model=settings.default_model,
        max_tokens=256,
        tools=TOOLS,
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": PROMPT}],
    )
    picks = [b.name for b in resp.content if b.type == "tool_use"]
    prose = "".join(b.text for b in resp.content if b.type == "text").strip()
    print(f"─── {label} (tool_choice={tool_choice}) ───")
    print(f"  stop_reason : {resp.stop_reason}")
    print(f"  tool picks  : {picks or '<none>'}")
    print(f"  prose       : {prose[:80]!r}\n")


def main() -> None:
    run("auto", {"type": "auto"})
    run("any", {"type": "any"})
    run("forced record_greeting", {"type": "tool", "name": "record_greeting"})


if __name__ == "__main__":
    main()
