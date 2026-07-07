# Task Decomposition Strategies

Notes on [1.6](https://claudecertificationguide.com/learn/1-agentic-architecture/1-6-task-decomposition).

## Two patterns

- **Fixed pipeline** — steps known upfront. Predictable, debuggable. Code review, extraction, compliance.
- **Dynamic decomposition** — plan emerges from investigation. Legacy exploration, audits, debugging unknown systems.

Pick by shape, not size. Open-ended ⇒ dynamic. Structured ⇒ pipeline.

## Attention dilution

More items in one context ⇒ less attention per item. Symptom: deep on the first few, shallow on the rest, same pattern judged inconsistently across items.

**Not fixed by** bigger model, bigger context, or better prompt. It's structural.

**Fix:** per-item local passes + one cross-item integration pass. 14 files → 14 focused calls + 1 integration call.

## Exam traps

- "Use a stronger model / larger context / better prompt" for dilution — wrong.
- Fixed pipeline on open-ended work — wrong.
- Batching without a cross-batch integration pass — misses cross-cutting issues.
