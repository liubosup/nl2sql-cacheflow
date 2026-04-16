from __future__ import annotations

from nl2sql_cacheflow.domain.models import EvidenceBundle, NormalizedQuery
from nl2sql_cacheflow.domain.protocols import SchemaCatalog


class SchemaEvidenceRetriever:
    def __init__(self, schema_catalog: SchemaCatalog) -> None:
        self._schema_catalog = schema_catalog

    def retrieve(self, query: NormalizedQuery, k: int) -> EvidenceBundle:
        return self._schema_catalog.build_evidence(query, k)
