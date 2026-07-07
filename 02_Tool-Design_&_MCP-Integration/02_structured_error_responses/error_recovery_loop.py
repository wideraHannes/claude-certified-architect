"""
Practical for 2.2 — Structured Error Responses.

A flaky order-lookup tool returns each error category (plus valid-empty).
The agent reads the metadata and picks a recovery.
"""

from __future__ import annotations

import json
import random
from typing import Any, Literal

from pydantic import BaseModel

from config import client, settings


class ToolError(BaseModel):
    errorCategory: Literal["transient", "validation", "business", "permission"]
    isRetryable: bool
    description: str


class ToolResult(BaseModel):
    isError: bool
    resultCount: int = 0
    data: list[dict[str, Any]] = []
    error: ToolError | None = None


TRANSIENT = ToolResult(
    isError=True,
    error=ToolError(
        errorCategory="transient",
        isRetryable=True,
        description="Upstream order-service timed out.",
    ),
)
VALIDATION = ToolResult(
    isError=True,
    error=ToolError(
        errorCategory="validation",
        isRetryable=True,
        description="`order_id` must match /^A-\\d{4}$/.",
    ),
)
BUSINESS = ToolResult(
    isError=True,
    error=ToolError(
        errorCategory="business",
        isRetryable=False,
        description="Refund exceeds self-serve policy limit.",
    ),
)
PERMISSION = ToolResult(
    isError=True,
    error=ToolError(
        errorCategory="permission",
        isRetryable=False,
        description="Caller lacks scope `orders:read:pii`.",
    ),
)
EMPTY = ToolResult(isError=False, resultCount=0)
SUCCESS = ToolResult(
    isError=False,
    resultCount=1,
    data=[{"order_id": "A-8891", "status": "shipped"}],
)

OUTCOMES = [TRANSIENT, VALIDATION, BUSINESS, PERMISSION, EMPTY, SUCCESS]


def lookup_order(order_id: str, forced: ToolResult | None = None) -> ToolResult:
    return forced if forced is not None else random.choice(OUTCOMES)


TOOL_SCHEMA = {
    "name": "lookup_order",
    "description": (
        "Fetch a single order by id.\n"
        "Success: {isError: false, resultCount, data}. "
        "resultCount=0 means no such order — do NOT retry.\n"
        "Failure: {isError: true, error: {errorCategory, isRetryable, description}}."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
}


def decide(result: ToolResult) -> str:
    if not result.isError:
        return "empty" if result.resultCount == 0 else "accept"
    assert result.error
    match result.error.errorCategory:
        case "transient":
            return "retry same"
        case "validation":
            return "retry fixed"
        case _:
            return "escalate"


SYSTEM_PROMPT = (
    "You look up orders. Call `lookup_order`, then read the result.\n"
    "  transient  → retry with the same input.\n"
    "  validation → retry with corrected input.\n"
    "  business or permission → do not retry, explain and stop.\n"
    "  resultCount=0 → the order doesn't exist, stop."
)


def run_agent(query: str, script: list[ToolResult]) -> None:
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    step = 0
    for _ in range(6):
        resp = client.messages.create(
            model=settings.default_model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            tools=[TOOL_SCHEMA],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            text = "".join(b.text for b in resp.content if b.type == "text")
            print(f"  final → {text.strip()}\n")
            return

        results = []
        for tu in tool_uses:
            forced = script[step] if step < len(script) else None
            result = lookup_order(**tu.input, forced=forced)
            cat = result.error.errorCategory if result.error else "ok"
            print(f"  step {step}: {cat:<10} → {decide(result)}")
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result.model_dump()),
                "is_error": result.isError,
            })
            step += 1
        messages.append({"role": "user", "content": results})


def main() -> None:
    scenarios = [
        ("transient then success", [TRANSIENT, SUCCESS]),
        ("validation then success", [VALIDATION, SUCCESS]),
        ("business (no retry)", [BUSINESS]),
        ("permission (escalate)", [PERMISSION]),
        ("valid empty (do not retry)", [EMPTY]),
    ]
    for label, script in scenarios:
        print(f"\n─── {label} ───")
        run_agent("What's the status of order A-8891?", script)


if __name__ == "__main__":
    main()
