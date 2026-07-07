"""
Structured handoff protocol.

Human agents do NOT see the conversation transcript. The handoff summary is
their only context, so every field must be populated with real content — no
placeholders. Multi-concern requests must be decomposed so no item is
silently dropped.
"""

from pydantic import BaseModel, Field

from config import client, settings

SYSTEM = """You are a customer-support agent preparing a handoff to a human agent.
The human agent cannot see the conversation. Your summary is their only source
of context.

Rules:
- Decompose multi-concern requests into distinct items and address every one.
- Every field must contain real content — no placeholders, no "n/a", no empty text.
- refund_amount is a number; use 0 if no refund applies.
- recommended_action must be concrete enough for the human to act on immediately."""


class Handoff(BaseModel):
    customer_id: str = Field(min_length=1)
    conversation_summary: str = Field(
        min_length=60,
        description="What the customer asked and what the agent tried. Cover every concern.",
    )
    root_cause: str = Field(
        min_length=20, description="The agent's diagnosis of the underlying issue(s)."
    )
    refund_amount: float = Field(
        ge=0.0, description="Refund amount in USD. 0 if no refund applies."
    )
    recommended_action: str = Field(
        min_length=20,
        description="Concrete next step(s) for the human agent, one per concern.",
    )


HANDOFF_TOOL = {
    "name": "record_handoff",
    "description": "Record the structured handoff summary for the human agent.",
    "input_schema": Handoff.model_json_schema(),
}


def build_handoff(conversation: str) -> Handoff:
    response = client.messages.create(
        model=settings.default_model,
        max_tokens=2048,
        system=SYSTEM,
        tools=[HANDOFF_TOOL],
        tool_choice={"type": "tool", "name": "record_handoff"},
        messages=[{"role": "user", "content": conversation}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return Handoff.model_validate(tool_use.input)


REQUIRED_CONCERNS = {
    "return": ["return", "damaged", "o-77"],
    "billing": ["billing", "duplicate", "double", "$89"],
    "account": ["account", "email"],
}


def _verify_multi_concern(handoff: Handoff) -> None:
    haystack = (
        handoff.conversation_summary + " " + handoff.recommended_action
    ).lower()
    missing = [
        name
        for name, keywords in REQUIRED_CONCERNS.items()
        if not any(k in haystack for k in keywords)
    ]
    print("=" * 60)
    if missing:
        print(f"FAIL: handoff omits these concerns: {missing}")
    else:
        print(f"PASS: all three concerns represented: {list(REQUIRED_CONCERNS)}")
    print("=" * 60)


if __name__ == "__main__":
    # Task 5 — three distinct concerns in one request.
    conversation = (
        "Customer C-1001 (alice@example.com) writes with three issues:\n"
        "  1) Order O-77 (Widget, $49.99) arrived damaged — she wants to return it "
        "and be refunded the full $49.99.\n"
        "  2) She was double-charged on her last invoice — a billing dispute for $89.50.\n"
        "  3) Please update the account email to alice.new@example.com.\n\n"
        "Agent actions so far: looked up the customer and verified identity, "
        "confirmed order O-77 belongs to the account, acknowledged the duplicate "
        "charge appears in billing history, and noted the email change request."
    )
    handoff = build_handoff(conversation)
    print(handoff.model_dump_json(indent=2))
    _verify_multi_concern(handoff)
