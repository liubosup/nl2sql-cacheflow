from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from nl2sql_cacheflow.domain.models import CacheEntry
from nl2sql_cacheflow.domain.protocols import EmbeddingBackend
from nl2sql_cacheflow.services.cache_router import cosine_similarity


class InMemoryCacheStore:
    def __init__(self, embedding_backend: EmbeddingBackend | None = None) -> None:
        self._entries: dict[str, list[CacheEntry]] = defaultdict(list)
        self._embedding_backend = embedding_backend

    def retrieve_top_k(
        self, schema_id: str, embedding: Sequence[float], k: int
    ) -> list[CacheEntry]:
        entries = self._entries.get(schema_id, [])
        ranked = sorted(
            entries,
            key=lambda entry: cosine_similarity(
                embedding, entry.metadata.get("embedding", [])
            ),
            reverse=True,
        )
        return ranked[:k]

    def put(self, entry: CacheEntry) -> None:
        if self._embedding_backend is not None and "embedding" not in entry.metadata:
            entry.metadata["embedding"] = self._embedding_backend.embed(
                entry.normalized_question
            )
        self._entries[entry.schema_id].insert(0, entry)

    def all_for_schema(self, schema_id: str) -> list[CacheEntry]:
        return list(self._entries.get(schema_id, []))
