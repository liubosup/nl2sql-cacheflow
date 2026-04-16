from __future__ import annotations

from nl2sql_cacheflow.domain.models import CacheEntry, NormalizedQuery
from nl2sql_cacheflow.domain.protocols import EquivalenceJudge


class ReuseValidator:
    """Safety-aware reuse validator for cache hits.

    This MVP version only performs deterministic slot-level checks.
    Later versions can add an optional LLM equivalence check.
    """

    def __init__(self, equivalence_judge: EquivalenceJudge | None = None) -> None:
        self._equivalence_judge = equivalence_judge

    def validate(self, query: NormalizedQuery, candidate: CacheEntry) -> bool:
        if query.schema_id != candidate.schema_id:
            return False

        q_slots = query.slots
        c_slots = candidate.slots
        slots_match = (
            q_slots.entities == c_slots.entities
            and q_slots.metrics == c_slots.metrics
            and q_slots.filters == c_slots.filters
            and q_slots.time_constraints == c_slots.time_constraints
            and q_slots.ordering == c_slots.ordering
            and q_slots.grouping == c_slots.grouping
        )
        if not slots_match:
            return False

        if self._equivalence_judge is None:
            return True
        return self._equivalence_judge.is_equivalent(query, candidate)
