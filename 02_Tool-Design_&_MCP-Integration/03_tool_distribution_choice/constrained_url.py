"""
Generic vs constrained tool for 2.3.

Two tools with the same *capability* (fetch a URL and return text), different
*constraints*:

  fetch_url(url)      — accepts anything; a footgun for subagents.
  load_document(url)  — validates that the URL points at a document host and
                        has a document MIME extension. Rejects anything else
                        with a structured error (2.2 shape).

Same subagent, same three prompts. The constrained tool refuses two of them
in code — no prompt engineering required. The description of a tool is a
suggestion; the code is the enforcement.
"""

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel

from config import client, settings


# ---------------------------------------------------------------------------
# Structured error shape reused from 2.2.
# ---------------------------------------------------------------------------
class ToolError(BaseModel):
    errorCategory: Literal["transient", "validation", "business", "permission"]
    isRetryable: bool
    description: str


class ToolResult(BaseModel):
    isError: bool
    data: dict[str, Any] | None = None
    error: ToolError | None = None


ALLOWED_HOSTS = {"arxiv.org", "docs.python.org", "example.com"}
DOCUMENT_EXTS = (".pdf", ".md", ".txt", ".html", ".htm")


def load_document(url: str) -> ToolResult:
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return ToolResult(
            isError=True,
            error=ToolError(
                errorCategory="permission",
                isRetryable=False,
                description=(
                    f"Host {parsed.hostname!r} is not in the document allow-list "
                    f"{sorted(ALLOWED_HOSTS)}. This tool loads documents only."
                ),
            ),
        )
    if not parsed.path.lower().endswith(DOCUMENT_EXTS):
        return ToolResult(
            isError=True,
            error=ToolError(
                errorCategory="validation",
                isRetryable=False,
                description=(
                    f"Path {parsed.path!r} does not end with a document extension "
                    f"({', '.join(DOCUMENT_EXTS)})."
                ),
            ),
        )
    return ToolResult(isError=False, data={"url": url, "text": "<document body>"})


def fetch_url(url: str) -> ToolResult:
    # No validation — will "succeed" for anything.
    return ToolResult(isError=False, data={"url": url, "text": "<raw body>"})


# ---------------------------------------------------------------------------
# Tool schemas. Descriptions are deliberately similar; the difference lives
# in the validators above.
# ---------------------------------------------------------------------------
FETCH_URL_SCHEMA = {
    "name": "fetch_url",
    "description": "Fetch the raw body at a URL and return it as text.",
    "input_schema": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
}

LOAD_DOCUMENT_SCHEMA = {
    "name": "load_document",
    "description": (
        "Load a document from an allow-listed host. Accepts PDF, Markdown, "
        "plain text, and HTML paths only. Returns a structured error for any "
        "URL that is not a document."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
}


# ---------------------------------------------------------------------------
# Driver. Runs one turn with `tool_choice="any"` so we always see the pick.
# Then executes the picked tool and prints the outcome.
# ---------------------------------------------------------------------------
IMPLEMENTATIONS = {"fetch_url": fetch_url, "load_document": load_document}


def run(label: str, schema: dict[str, Any], query: str) -> None:
    resp = client.messages.create(
        model=settings.default_model,
        max_tokens=256,
        tools=[schema],
        tool_choice={"type": "tool", "name": schema["name"]},
        messages=[{"role": "user", "content": query}],
    )
    tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
    if not tool_use:
        print(f"  {label:<15} : model did not call the tool")
        return
    result = IMPLEMENTATIONS[tool_use.name](**tool_use.input)
    verdict = "OK" if not result.isError else f"BLOCKED ({result.error.errorCategory})"  # type: ignore[union-attr]
    print(f"  {label:<15} : {tool_use.input.get('url'):<45} → {verdict}")
    if result.isError:
        print(f"    reason      : {result.error.description}")  # type: ignore[union-attr]


CASES = [
    ("arxiv PDF (a real document)",
     "Load the paper at https://arxiv.org/paper/2401.12345.pdf"),
    ("random API endpoint",
     "Fetch https://api.malicious.example/admin/keys"),
    ("HTML doc on allow-listed host",
     "Load https://docs.python.org/3/tutorial/index.html"),
]


def main() -> None:
    for label, query in CASES:
        print(f"\n─── {label} ───")
        run("fetch_url",     FETCH_URL_SCHEMA,     query)
        run("load_document", LOAD_DOCUMENT_SCHEMA, query)


if __name__ == "__main__":
    main()
