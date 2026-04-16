from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nl2sql_cacheflow.domain.models import EvidenceBundle, NormalizedQuery, SqlCandidate
from nl2sql_cacheflow.domain.protocols import PromptBuilder


class HashEmbeddingBackend:
    """Deterministic lightweight embedding for local tests."""

    def embed(self, text: str) -> list[float]:
        buckets = [0.0] * 8
        for idx, ch in enumerate(text):
            buckets[idx % len(buckets)] += float(ord(ch))
        norm = max(sum(abs(x) for x in buckets), 1.0)
        return [x / norm for x in buckets]


@dataclass
class StaticEvidenceRetriever:
    schema_summary: str = "schema evidence"
    join_hints: list[str] = field(default_factory=list)
    business_hints: list[str] = field(default_factory=list)
    cache_examples: list[str] = field(default_factory=list)

    def retrieve(self, query: NormalizedQuery, k: int) -> EvidenceBundle:
        return EvidenceBundle(
            schema_summary=self.schema_summary,
            join_hints=self.join_hints[:k],
            business_hints=self.business_hints[:k],
            cache_examples=self.cache_examples[:k],
        )


@dataclass
class RecordingSqlGenerator:
    sql_to_return: str
    prompt_builder: PromptBuilder | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def generate(self, query: NormalizedQuery, evidence: EvidenceBundle) -> list[SqlCandidate]:
        prompt = self.prompt_builder.build(query, evidence) if self.prompt_builder else None
        self.calls.append(
            {
                "normalized_question": query.normalized_question,
                "evidence": {
                    "schema_summary": evidence.schema_summary,
                    "join_hints": list(evidence.join_hints),
                    "business_hints": list(evidence.business_hints),
                    "cache_examples": list(evidence.cache_examples),
                },
                "prompt": prompt.prompt if prompt else "",
                "main_table": prompt.main_table if prompt else None,
            }
        )
        return [SqlCandidate(sql=self.sql_to_return, source="stub-generator", score=1.0)]


@dataclass
class RecordingSqlExecutor:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def execute_and_validate(self, schema_id: str, sql: str) -> dict[str, Any]:
        result = {"schema_id": schema_id, "sql": sql, "valid": sql is not None}
        self.calls.append(result)
        return result


class AlwaysEquivalentJudge:
    def is_equivalent(self, query: NormalizedQuery, candidate: Any) -> bool:
        return True
