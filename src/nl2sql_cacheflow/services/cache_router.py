from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from nl2sql_cacheflow.domain.models import CacheEntry, NormalizedQuery
from nl2sql_cacheflow.domain.protocols import CacheStore, EmbeddingBackend


@dataclass(slots=True)
class CacheDecision:
    candidates: list[CacheEntry]
    top_entry: CacheEntry | None
    similarity: float | None
    should_fallback: bool


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class CacheRouter:
    def __init__(
        self,
        embedding_backend: EmbeddingBackend,
        cache_store: CacheStore,
        top_k: int,
        similarity_threshold: float,
    ) -> None:
        self._embedding_backend = embedding_backend
        self._cache_store = cache_store
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    def route(self, query: NormalizedQuery) -> CacheDecision:
        embedding = self._embedding_backend.embed(query.normalized_question)
        candidates = self._cache_store.retrieve_top_k(
            schema_id=query.schema_id,
            embedding=embedding,
            k=self._top_k,
        )
        if not candidates:
            return CacheDecision([], None, None, True)

        scored = []
        for entry in candidates:
            entry_embedding = entry.metadata.get("embedding")
            sim = cosine_similarity(embedding, entry_embedding) if entry_embedding else 0.0
            scored.append((sim, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        top_similarity, top_entry = scored[0]
        return CacheDecision(
            candidates=[entry for _, entry in scored],
            top_entry=top_entry,
            similarity=top_similarity,
            should_fallback=top_similarity < self._similarity_threshold,
        )
