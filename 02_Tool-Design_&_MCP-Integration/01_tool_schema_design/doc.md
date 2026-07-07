# Tool Schema Design

Notes on [2.1](https://claudecertificationguide.com/learn/2-tool-design-mcp/2-1-tool-schema-design).

## Golden rule

The **description is the routing signal**. Claude picks a tool from `name + description + input_schema` — nothing else. Vague or overlapping descriptions cause **misrouting**, and no amount of prompting fixes a schema-level ambiguity cheaply.

## Five elements of a production-grade description

1. **Primary purpose** — one unambiguous sentence: what does this tool do.
2. **Input expectations** — accepted formats, types, required vs optional, constraints.
3. **Concrete use cases** — 1–3 example queries that anchor selection.
4. **Limitations / edge cases** — what it does NOT handle.
5. **Explicit boundaries** — differentiate from sibling tools: *"Do NOT use for X — use `other_tool` instead."*

Minimal (misroutes):

> `get_customer`: "Retrieves customer information"
> `lookup_order`: "Retrieves order details"

Production-grade (routes reliably): expands each with the five elements, including cross-references like *"Do NOT use for order-specific queries — use `lookup_order` for those."*

## Fixing misrouting — priority order

When production logs show the wrong tool getting picked, the exam expects the cheapest root-cause fix first:

| Fix | Verdict |
|---|---|
| Expand descriptions with the 5 elements | **✓ first move** — addresses the root cause |
| Split a generic tool into purpose-specific ones | ✓ when responsibilities genuinely overlap |
| Rename confusingly similar tools | ✓ zero-cost clarity win |
| Few-shot examples in the system prompt | ✗ treats symptom, adds tokens |
| Routing classifier layer | ✗ over-engineered |
| Consolidate tools | ✗ high effort, defer |

## Splitting a generic tool

Broad responsibility → ambiguity. Break it up:

- Before: `analyze_document`
- After: `extract_data_points`, `summarize_content`, `verify_claim_against_source`

## System-prompt interactions

Keyword-heavy instructions in the system prompt can create unintended tool associations that **override well-written descriptions**. After tightening a description, re-audit the system prompt for stray keywords ("order", "customer", "analyze") that yank routing back the wrong way.

## Exam traps

- Picking few-shot / classifier / consolidation over description expansion on the first misrouting incident.
- Ignoring the system prompt after fixing schemas.
- Assuming `name` alone disambiguates — the model reads `description` primarily.
- Writing descriptions that state **what** without stating **when not to use it**.
