"""
Tool-schema A/B: MINIMAL vs PRODUCTION-GRADE descriptions.

Runs the same ambiguous customer/order queries through two tool sets
that differ ONLY in their `description` fields, captures which tool
Claude picks, and prints a side-by-side visualization so the routing
failures of the minimal schema — and the fix — are obvious at a glance.
"""

from pydantic import BaseModel, Field

from config import client, settings

# ---- Schemas -----------------------------------------------------------------


class ToolInput(BaseModel):
    """Shared input schema for both tools — isolates description as the only variable."""

    query: str = Field(description="Natural-language user request.")


class ToolSpec(BaseModel):
    name: str
    description: str

    def to_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": ToolInput.model_json_schema(),
        }


class Case(BaseModel):
    query: str
    expected: str
    why: str


class RunRow(BaseModel):
    case: Case
    minimal_pick: str | None
    prod_pick: str | None


# ---- Tool sets ---------------------------------------------------------------
# Same names, same input_schema. Only `description` changes.

MINIMAL_TOOLS: list[ToolSpec] = [
    ToolSpec(name="get_customer", description="Retrieves customer information."),
    ToolSpec(name="lookup_order", description="Retrieves order details."),
]

PROD_TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="get_customer",
        description=(
            "Primary purpose: fetch a CUSTOMER RECORD (identity, contact info, "
            "billing address, loyalty tier, account status).\n"
            "Input: a customer identifier — customer_id (int), email, or account "
            "phone number. Not an order id.\n"
            "Use for: 'what is the email on file for customer 4421', "
            "'show loyalty tier for jane@acme.com', 'billing address for user 9910'.\n"
            "Does NOT return: order history, shipment status, refunds, line items.\n"
            "Do NOT use for order-specific queries — use `lookup_order` for those, "
            "even when a customer is mentioned in the query."
        ),
    ),
    ToolSpec(
        name="lookup_order",
        description=(
            "Primary purpose: fetch a single ORDER (line items, shipment status, "
            "refund/return status, totals, timestamps).\n"
            "Input: an order identifier — order_id (e.g. 'A-8891', numeric) OR a "
            "(customer_id, relative-time) pair like 'customer 4421, yesterday'.\n"
            "Use for: 'shipping status of order A-8891', 'refund status of order "
            "77123', 'what items were in the order placed yesterday by customer X'.\n"
            "Does NOT return: customer profile fields (email, address, loyalty tier) "
            "unless they are attached to the specific order.\n"
            "Do NOT use for customer-profile lookups — use `get_customer` for those."
        ),
    ),
]

SYSTEM_PROMPT = (
    "You are a customer-service backend router. For each user request, pick "
    "exactly one tool and call it. Do not ask clarifying questions."
)

# ---- Test set ----------------------------------------------------------------

CASES: list[Case] = [
    Case(
        query="What's the shipping status of order #A-8891 for customer 4421?",
        expected="lookup_order",
        why="Order-scoped question; customer id is just context.",
    ),
    Case(
        query="Get the loyalty tier for customer 4421.",
        expected="get_customer",
        why="Pure profile field.",
    ),
    Case(
        query="Which items were in the order that customer 4421 placed yesterday?",
        expected="lookup_order",
        why="Line items live on the order, not the customer record.",
    ),
    Case(
        query="Show the billing address on file for user 9910.",
        expected="get_customer",
        why="Billing address is a profile field.",
    ),
    Case(
        query="Find the refund status of order 77123.",
        expected="lookup_order",
        why="Refund status is per-order.",
    ),
    Case(
        query="What email do we have on file for the customer who placed order A-8891?",
        expected="get_customer",
        why="Trap: mentions an order id, but the answer is a profile field.",
    ),
]


# ---- Runner ------------------------------------------------------------------


def _pick_tool(tools: list[ToolSpec], query: str) -> str | None:
    """Return the tool name Claude picks for `query`, or None if it emitted text."""
    resp = client.messages.create(
        model=settings.default_model,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        tools=[t.to_anthropic() for t in tools],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": query}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.name
    return None


# ---- Visualization -----------------------------------------------------------

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _mark(picked: str | None, expected: str) -> str:
    if picked == expected:
        return f"{GREEN}✓ {picked}{RESET}"
    return f"{RED}✗ {picked or '(text)'}{RESET}"


def _bar(hits: int, total: int, width: int = 24) -> str:
    filled = round(width * hits / total) if total else 0
    color = GREEN if hits == total else (YELLOW if hits >= total * 0.6 else RED)
    return f"{color}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def visualize(rows: list[RunRow]) -> None:
    q_w = min(max(len(r.case.query) for r in rows), 68)

    print()
    print(f"{BOLD}Tool-schema A/B — MINIMAL vs PRODUCTION-GRADE{RESET}")
    print(f"{DIM}Same names, same input_schema. Only `description` differs.{RESET}\n")

    header = (
        f"{BOLD}{'Query':<{q_w}}  {'Expected':<14}  "
        f"{'MINIMAL':<22}  {'PROD-GRADE':<22}{RESET}"
    )
    print(header)
    print(DIM + "─" * (q_w + 14 + 22 + 22 + 6) + RESET)

    min_hits = prod_hits = 0
    for row in rows:
        c = row.case
        min_hits += row.minimal_pick == c.expected
        prod_hits += row.prod_pick == c.expected
        q = c.query if len(c.query) <= q_w else c.query[: q_w - 1] + "…"
        print(
            f"{q:<{q_w}}  {CYAN}{c.expected:<14}{RESET}  "
            f"{_mark(row.minimal_pick, c.expected):<31}  "
            f"{_mark(row.prod_pick, c.expected):<31}"
        )
        print(f"{DIM}{'':<{q_w}}  why: {c.why}{RESET}")

    total = len(rows)
    print()
    print(f"{BOLD}Accuracy{RESET}")
    print(f"  MINIMAL     {_bar(min_hits, total)}  {min_hits}/{total}")
    print(f"  PROD-GRADE  {_bar(prod_hits, total)}  {prod_hits}/{total}")

    print()
    print(f"{BOLD}Why the production schema wins — 5 elements{RESET}")
    for i, line in enumerate(
        [
            "Primary purpose      — one unambiguous sentence.",
            "Input expectations   — accepted identifier types.",
            "Concrete use cases   — 1–3 example queries anchor selection.",
            "Limitations          — what the tool does NOT return.",
            "Explicit boundaries  — 'Do NOT use for X — use `other_tool`'.",
        ],
        start=1,
    ):
        print(f"  {CYAN}{i}.{RESET} {line}")

    print()
    print(f"{BOLD}Diff — `lookup_order.description`{RESET}")
    print(f"  {RED}MINIMAL:{RESET}    \"Retrieves order details.\"")
    print(
        f"  {GREEN}PROD-GRADE:{RESET} {len(PROD_TOOLS[1].description)} chars — "
        f"purpose + inputs + examples + limits + boundary vs `get_customer`."
    )


def main() -> None:
    print(
        f"{DIM}Querying model={settings.default_model} — 2 runs × "
        f"{len(CASES)} cases = {2 * len(CASES)} calls{RESET}"
    )
    rows: list[RunRow] = []
    for case in CASES:
        rows.append(
            RunRow(
                case=case,
                minimal_pick=_pick_tool(MINIMAL_TOOLS, case.query),
                prod_pick=_pick_tool(PROD_TOOLS, case.query),
            )
        )
        print(f"{DIM}  · {case.query[:60]}…{RESET}")
    visualize(rows)


if __name__ == "__main__":
    main()
