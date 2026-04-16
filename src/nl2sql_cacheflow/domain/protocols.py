from __future__ import annotations

from typing import Protocol, Sequence, Any

from .models import (
    CacheEntry,
    EvidenceBundle,
    NormalizedQuery,
    PromptContext,
    SqlCandidate,
    TableSchema,
)


class QueryNormalizer(Protocol):
    def normalize(self, question: str, schema_id: str) -> NormalizedQuery: ...


class EmbeddingBackend(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...


class CacheStore(Protocol):
    def retrieve_top_k(
        self, schema_id: str, embedding: Sequence[float], k: int
    ) -> list[CacheEntry]: ...

    def put(self, entry: CacheEntry) -> None: ...


class EvidenceRetriever(Protocol):
    def retrieve(self, query: NormalizedQuery, k: int) -> EvidenceBundle: ...


class SqlGenerator(Protocol):
    def generate(self, query: NormalizedQuery, evidence: EvidenceBundle) -> list[SqlCandidate]: ...


class SqlExecutor(Protocol):
    def execute_and_validate(self, schema_id: str, sql: str) -> Any: ...


class EquivalenceJudge(Protocol):
    def is_equivalent(self, query: NormalizedQuery, candidate: CacheEntry) -> bool: ...


class SchemaCatalog(Protocol):
    def match_main_table(self, query: NormalizedQuery) -> TableSchema | None: ...

    def build_evidence(self, query: NormalizedQuery, k: int) -> EvidenceBundle: ...


class PromptBuilder(Protocol):
    def build(self, query: NormalizedQuery, evidence: EvidenceBundle) -> PromptContext: ...
