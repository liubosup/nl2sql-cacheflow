from __future__ import annotations

from nl2sql_cacheflow.domain.models import CacheEntry, InferenceResult, QueryInput, WorkflowTrace
from nl2sql_cacheflow.domain.protocols import QueryNormalizer, SqlExecutor, CacheStore
from nl2sql_cacheflow.services.cache_router import CacheRouter
from nl2sql_cacheflow.services.reuse_validator import ReuseValidator
from nl2sql_cacheflow.services.unified_generation import UnifiedGenerationPath


class CacheFirstNl2SqlWorkflow:
    def __init__(
        self,
        query_normalizer: QueryNormalizer,
        cache_router: CacheRouter,
        reuse_validator: ReuseValidator,
        generation_path: UnifiedGenerationPath,
        sql_executor: SqlExecutor,
        cache_store: CacheStore,
    ) -> None:
        self._query_normalizer = query_normalizer
        self._cache_router = cache_router
        self._reuse_validator = reuse_validator
        self._generation_path = generation_path
        self._sql_executor = sql_executor
        self._cache_store = cache_store

    def run(self, request: QueryInput) -> InferenceResult:
        query = self._query_normalizer.normalize(request.question, request.schema_id)
        decision = self._cache_router.route(query)
        trace = WorkflowTrace(
            normalized_question=query.normalized_question,
            cache_similarity=decision.similarity,
            cache_selected_question=decision.top_entry.question if decision.top_entry else None,
        )

        selected_sql = None
        reused = False
        if not decision.should_fallback and decision.top_entry is not None:
            if self._reuse_validator.validate(query, decision.top_entry):
                selected_sql = decision.top_entry.sql
                reused = True
                trace.cache_reuse_allowed = True
                trace.selected_strategy = "cache_reuse"
            else:
                trace.warnings.append("cache_hit_rejected_by_safety_validator")

        if selected_sql is None:
            selected_sql, evidence, candidates = self._generation_path.run(query)
            trace.generation_evidence = evidence
            trace.generated_candidates = candidates
            trace.selected_strategy = "generate"

        execution_result = self._sql_executor.execute_and_validate(
            request.schema_id, selected_sql
        )

        if not reused and selected_sql is not None:
            self._cache_store.put(
                CacheEntry(
                    question=request.question,
                    normalized_question=query.normalized_question,
                    schema_id=request.schema_id,
                    sql=selected_sql,
                    slots=query.slots,
                    metadata={},
                )
            )

        return InferenceResult(
            sql=selected_sql,
            execution_result=execution_result,
            reused_from_cache=reused,
            trace=trace,
        )
