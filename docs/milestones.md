# Milestones

## Milestone 1: Canonical Inputs

- Define `QueryInput`, `NormalizedQuery`, and `SemanticSlots`.
- Define the minimal schema context object.
- Add deterministic test fixtures.

## Milestone 2: Cache-First Routing

- Implement top-k cache retrieval.
- Implement similarity threshold gate.
- Implement slot consistency validation.
- Add a clear reuse-or-fallback decision result.

## Milestone 3: Unified Generation Path

- Retrieve schema/domain evidence.
- Build prompt context.
- Generate SQL.
- Validate executability.

## Milestone 4: Write-Back and Observability

- Write successful results into cache.
- Track latency, reuse rate, and fallback rate.
- Track invalid SQL and false reuse cases.

## Milestone 5: M4-Style Enhancement

- Multi-candidate generation.
- Candidate filtering.
- Ranking and selection.
- Compare against the M3-style baseline.
