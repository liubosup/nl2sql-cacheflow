import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nl2sql_cacheflow.application.query_service import QueryApplicationService
from nl2sql_cacheflow.application.workflow import CacheFirstNl2SqlWorkflow
from nl2sql_cacheflow.application.runtime import build_legacy_backed_runtime, build_legacy_runtime_bundle
from nl2sql_cacheflow.domain.models import CacheEntry, QueryInput
from nl2sql_cacheflow.infra.cache_store import InMemoryCacheStore
from nl2sql_cacheflow.infra.log_store import JsonlQueryLogStore
from nl2sql_cacheflow.infra.normalizer import RuleBasedQueryNormalizer
from nl2sql_cacheflow.infra.retrieval import SchemaEvidenceRetriever
from nl2sql_cacheflow.infra.schema_catalog import LocalSchemaCatalog
from nl2sql_cacheflow.infra.sql_executor import GuardedSqlExecutor
from nl2sql_cacheflow.infra.stubs import (
    AlwaysEquivalentJudge,
    HashEmbeddingBackend,
    RecordingSqlGenerator,
)
from nl2sql_cacheflow.services.prompt_builder import SqlPromptBuilder
from nl2sql_cacheflow.services.cache_router import CacheRouter
from nl2sql_cacheflow.services.reuse_validator import ReuseValidator
from nl2sql_cacheflow.services.unified_generation import UnifiedGenerationPath


def build_workflow(sql_to_return: str = "SELECT 1"):
    normalizer = RuleBasedQueryNormalizer()
    embedding = HashEmbeddingBackend()
    cache_store = InMemoryCacheStore(embedding_backend=embedding)
    cache_router = CacheRouter(
        embedding_backend=embedding,
        cache_store=cache_store,
        top_k=5,
        similarity_threshold=0.77,
    )
    reuse_validator = ReuseValidator(equivalence_judge=AlwaysEquivalentJudge())
    schema_catalog = LocalSchemaCatalog(
        tables={
            "students": {
                "name": "students",
                "fields": {"id": "int", "name": "text", "year": "int"},
            },
            "teachers": {
                "name": "teachers",
                "fields": {"id": "int", "name": "text", "subject": "text"},
            },
        }
    )
    evidence_retriever = SchemaEvidenceRetriever(schema_catalog=schema_catalog)
    prompt_builder = SqlPromptBuilder()
    generator = RecordingSqlGenerator(sql_to_return=sql_to_return, prompt_builder=prompt_builder)
    generation_path = UnifiedGenerationPath(
        evidence_retriever=evidence_retriever,
        sql_generator=generator,
        evidence_top_k=3,
    )
    executor = GuardedSqlExecutor(rows_by_sql={sql_to_return: [{"ok": True}]})
    workflow = CacheFirstNl2SqlWorkflow(
        query_normalizer=normalizer,
        cache_router=cache_router,
        reuse_validator=reuse_validator,
        generation_path=generation_path,
        sql_executor=executor,
        cache_store=cache_store,
    )
    return workflow, cache_store, generator, executor, embedding, normalizer


class WorkflowTests(unittest.TestCase):
    def test_fallback_generation_writes_successful_sql_to_cache(self) -> None:
        workflow, cache_store, generator, executor, _, _ = build_workflow(
            sql_to_return="SELECT name FROM students"
        )

        result = workflow.run(QueryInput(question="Show all students", schema_id="school"))

        self.assertEqual(result.sql, "SELECT name FROM students")
        self.assertFalse(result.reused_from_cache)
        self.assertEqual(len(generator.calls), 1)
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(result.trace.selected_strategy, "generate")
        self.assertIn("main table: students", result.trace.generation_evidence.schema_summary)
        self.assertEqual(generator.calls[0]["main_table"], "students")
        self.assertIn("Return one executable SELECT statement only.", generator.calls[0]["prompt"])
        cached = cache_store.all_for_schema("school")
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0].sql, "SELECT name FROM students")
        self.assertIn("embedding", cached[0].metadata)

    def test_cache_hit_reuses_sql_and_skips_generation(self) -> None:
        workflow, cache_store, generator, executor, embedding, normalizer = build_workflow(
            sql_to_return="SELECT should_not_be_used"
        )
        normalized = normalizer.normalize("Show all students", "school")
        cache_store.put(
            CacheEntry(
                question="Show all students",
                normalized_question=normalized.normalized_question,
                schema_id="school",
                sql="SELECT name FROM students",
                slots=normalized.slots,
                metadata={"embedding": embedding.embed(normalized.normalized_question)},
            )
        )

        result = workflow.run(QueryInput(question="Show all students", schema_id="school"))

        self.assertEqual(result.sql, "SELECT name FROM students")
        self.assertTrue(result.reused_from_cache)
        self.assertEqual(len(generator.calls), 0)
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(result.trace.selected_strategy, "cache_reuse")
        self.assertTrue(result.trace.cache_reuse_allowed)

    def test_slot_mismatch_forces_fallback_even_when_cache_exists(self) -> None:
        workflow, cache_store, generator, executor, embedding, normalizer = build_workflow(
            sql_to_return="SELECT count(*) FROM students WHERE year = 2024"
        )
        cached_query = normalizer.normalize("count students for 2023", "school")
        incoming_query = normalizer.normalize("count students for 2024", "school")
        self.assertNotEqual(cached_query.slots, incoming_query.slots)

        cache_store.put(
            CacheEntry(
                question="count students for 2023",
                normalized_question=cached_query.normalized_question,
                schema_id="school",
                sql="SELECT count(*) FROM students WHERE year = 2023",
                slots=cached_query.slots,
                metadata={"embedding": embedding.embed(cached_query.normalized_question)},
            )
        )

        result = workflow.run(QueryInput(question="count students for 2024", schema_id="school"))

        self.assertFalse(result.reused_from_cache)
        self.assertEqual(result.sql, "SELECT count(*) FROM students WHERE year = 2024")
        self.assertEqual(len(generator.calls), 1)
        self.assertEqual(len(executor.calls), 1)
        self.assertIn("cache_hit_rejected_by_safety_validator", result.trace.warnings)

    def test_cache_store_returns_best_similarity_first(self) -> None:
        workflow, cache_store, _, _, embedding, normalizer = build_workflow()
        near = normalizer.normalize("show all students", "school")
        far = normalizer.normalize("list teachers in 2020", "school")

        cache_store.put(
            CacheEntry(
                question="list teachers in 2020",
                normalized_question=far.normalized_question,
                schema_id="school",
                sql="SELECT name FROM teachers",
                slots=far.slots,
                metadata={"embedding": embedding.embed(far.normalized_question)},
            )
        )
        cache_store.put(
            CacheEntry(
                question="show all students",
                normalized_question=near.normalized_question,
                schema_id="school",
                sql="SELECT name FROM students",
                slots=near.slots,
                metadata={"embedding": embedding.embed(near.normalized_question)},
            )
        )

        result = workflow.run(QueryInput(question="show all students", schema_id="school"))
        self.assertEqual(result.sql, "SELECT name FROM students")
        self.assertTrue(result.reused_from_cache)

    def test_guarded_executor_rejects_non_select_sql(self) -> None:
        executor = GuardedSqlExecutor()
        result = executor.execute_and_validate("school", "DELETE FROM students")
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "only_select_allowed")

    def test_legacy_schema_catalog_exposes_join_hints(self) -> None:
        runtime = build_legacy_backed_runtime(
            root_dir="/Users/liubo/Dev/codex-todo/nl2sql"
        )
        result = runtime.run(
            QueryInput(question="统计 2024 年华东区域 GMV", schema_id="legacy")
        )
        self.assertIsNotNone(result.trace.generation_evidence)
        self.assertTrue(result.trace.generation_evidence.join_hints)

    def test_legacy_runtime_can_generate_select_sql(self) -> None:
        runtime = build_legacy_backed_runtime(
            root_dir="/Users/liubo/Dev/codex-todo/nl2sql"
        )
        result = runtime.run(
            QueryInput(question="2024年订单数量是多少", schema_id="legacy")
        )
        self.assertTrue(result.sql.lower().startswith("select"))
        self.assertTrue(result.execution_result.valid)

    def test_query_service_writes_and_reads_history(self) -> None:
        workflow, _, _, _, _, _ = build_workflow(sql_to_return="SELECT count(*) AS value FROM students")
        with TemporaryDirectory() as tmpdir:
            log_store = JsonlQueryLogStore(Path(tmpdir) / "query_logs.jsonl")
            service = QueryApplicationService(
                workflow=workflow,
                log_store=log_store,
                schema_id="school",
                csv_export_path=Path(tmpdir) / "last_detail.csv",
            )
            response = service.ask("Show all students")
            self.assertTrue(response.sql.startswith("SELECT"))
            history = service.history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].question, "Show all students")
            self.assertTrue(service.csv_export_path.exists())

    def test_legacy_runtime_bundle_supports_classification(self) -> None:
        bundle = build_legacy_runtime_bundle(
            root_dir="/Users/liubo/Dev/codex-todo/nl2sql"
        )
        with TemporaryDirectory() as tmpdir:
            service = QueryApplicationService(
                workflow=bundle.workflow,
                log_store=JsonlQueryLogStore(Path(tmpdir) / "query_logs.jsonl"),
                schema_catalog=bundle.schema_catalog,
                schema_id="legacy",
            )
            result = service.classify_domain("统计 2024 年华东区域 GMV")
            self.assertIn("table", result)
            self.assertNotEqual(result["table"], "unknown")

    def test_wecom_query_without_notifier_reports_not_configured(self) -> None:
        workflow, _, _, _, _, _ = build_workflow(sql_to_return="SELECT 1")
        with TemporaryDirectory() as tmpdir:
            service = QueryApplicationService(
                workflow=workflow,
                log_store=JsonlQueryLogStore(Path(tmpdir) / "query_logs.jsonl"),
                schema_id="school",
            )
            result = service.ask_wecom("Show all students")
            self.assertIn("push_result", result)
            self.assertFalse(result["push_result"]["ok"])


if __name__ == "__main__":
    unittest.main()
