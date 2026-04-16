from __future__ import annotations

from nl2sql_cacheflow.domain.models import EvidenceBundle, NormalizedQuery, SqlCandidate
from nl2sql_cacheflow.domain.protocols import EvidenceRetriever, SqlGenerator


class UnifiedGenerationPath:
    def __init__(
        self,
        evidence_retriever: EvidenceRetriever,
        sql_generator: SqlGenerator,
        evidence_top_k: int,
    ) -> None:
        self._evidence_retriever = evidence_retriever
        self._sql_generator = sql_generator
        self._evidence_top_k = evidence_top_k

    def collect_evidence(self, query: NormalizedQuery) -> EvidenceBundle:
        evidence = self._evidence_retriever.retrieve(query, self._evidence_top_k)
        return evidence

    def generate_candidates(
        self, query: NormalizedQuery, evidence: EvidenceBundle
    ) -> list[SqlCandidate]:
        return self._sql_generator.generate(query, evidence)

    def run(self, query: NormalizedQuery) -> tuple[str | None, EvidenceBundle, list[SqlCandidate]]:
        evidence = self.collect_evidence(query)
        candidates = self.generate_candidates(query, evidence)
        if not candidates:
            return None, evidence, []
        return candidates[0].sql, evidence, candidates
