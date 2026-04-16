from __future__ import annotations

import re

from nl2sql_cacheflow.domain.models import NormalizedQuery, SemanticSlots


class RuleBasedQueryNormalizer:
    """Minimal deterministic normalizer for the MVP.

    The goal here is not full NL understanding. It provides a stable canonical
    representation and a small slot extraction layer so the cache-first workflow
    can be developed and tested end-to-end.
    """

    _STOPWORDS = {
        "the",
        "a",
        "an",
        "please",
        "show",
        "list",
        "me",
        "all",
        "give",
        "find",
        "what",
        "is",
        "are",
    }

    def normalize(self, question: str, schema_id: str) -> NormalizedQuery:
        normalized = self._normalize_text(question)
        slots = self._extract_slots(normalized)
        candidate_tables = self._extract_candidate_tables(normalized)
        return NormalizedQuery(
            raw_question=question,
            normalized_question=normalized,
            schema_id=schema_id,
            slots=slots,
            candidate_tables=candidate_tables,
        )

    def _normalize_text(self, text: str) -> str:
        lowered = text.strip().lower()
        lowered = re.sub(r"[^a-z0-9_\s]", " ", lowered)
        tokens = [tok for tok in lowered.split() if tok and tok not in self._STOPWORDS]
        return " ".join(tokens)

    def _extract_slots(self, normalized: str) -> SemanticSlots:
        tokens = normalized.split()
        metrics = [tok for tok in tokens if tok in {"count", "sum", "avg", "average", "max", "min", "total"}]
        ordering = [tok for tok in tokens if tok in {"highest", "lowest", "top", "bottom", "ascending", "descending"}]
        grouping = [tok for tok in tokens if tok in {"by", "per"}]
        time_constraints = [
            tok
            for tok in tokens
            if tok in {"today", "yesterday", "monthly", "yearly", "weekly", "daily", "last", "recent"}
            or re.fullmatch(r"\d{4}", tok)
        ]
        filters = {}
        entities = []
        for idx, tok in enumerate(tokens[:-1]):
            if tok in {"for", "in", "of"}:
                entities.append(tokens[idx + 1])
            if tok == "where" and idx + 1 < len(tokens) - 1:
                filters[tokens[idx + 1]] = tokens[idx + 2] if idx + 2 < len(tokens) else True
            if tok == "between" and idx + 2 < len(tokens):
                filters["between"] = f"{tokens[idx + 1]}:{tokens[idx + 2]}"
        return SemanticSlots(
            entities=entities,
            metrics=metrics,
            filters=filters,
            time_constraints=time_constraints,
            ordering=ordering,
            grouping=grouping,
        )

    def _extract_candidate_tables(self, normalized: str) -> list[str]:
        tokens = normalized.split()
        return [tok for tok in tokens if tok.endswith("s")]
