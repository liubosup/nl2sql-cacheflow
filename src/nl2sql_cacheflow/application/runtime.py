from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import os

from nl2sql_cacheflow.application.workflow import CacheFirstNl2SqlWorkflow
from nl2sql_cacheflow.infra.cache_store import InMemoryCacheStore
from nl2sql_cacheflow.infra.generator import HeuristicSqlGenerator
from nl2sql_cacheflow.infra.legacy_adapters import LegacyLlmSqlGenerator, LegacySqlExecutor, LegacyWeComNotifier
from nl2sql_cacheflow.infra.normalizer import RuleBasedQueryNormalizer
from nl2sql_cacheflow.infra.retrieval import SchemaEvidenceRetriever
from nl2sql_cacheflow.infra.schema_catalog import LocalSchemaCatalog
from nl2sql_cacheflow.infra.sql_executor import GuardedSqlExecutor
from nl2sql_cacheflow.infra.stubs import HashEmbeddingBackend
from nl2sql_cacheflow.services.cache_router import CacheRouter
from nl2sql_cacheflow.services.prompt_builder import SqlPromptBuilder
from nl2sql_cacheflow.services.reuse_validator import ReuseValidator
from nl2sql_cacheflow.services.unified_generation import UnifiedGenerationPath


@dataclass(slots=True)
class RuntimeBundle:
    workflow: CacheFirstNl2SqlWorkflow
    schema_catalog: LocalSchemaCatalog
    notifier: LegacyWeComNotifier | None = None


def build_legacy_backed_runtime(
    root_dir: str | Path | None = None,
) -> CacheFirstNl2SqlWorkflow:
    return build_legacy_runtime_bundle(root_dir=root_dir).workflow


def build_legacy_runtime_bundle(
    root_dir: str | Path | None = None,
) -> RuntimeBundle:
    root = Path(root_dir) if root_dir is not None else _default_repo_root()
    packaged_root = root / "nl2sql-cacheflow" if (root / "nl2sql-cacheflow").exists() else root
    packaged_assets = packaged_root / "assets" / "legacy"
    external_schema_path = root / "Ai_nl2sql" / "app" / "data" / "schema_config.json"
    external_join_rules_path = root / "Ai_nl2sql" / "app" / "data" / "join_rules.json"
    schema_path = external_schema_path if external_schema_path.exists() else packaged_assets / "schema_config.json"
    join_rules_path = (
        external_join_rules_path if external_join_rules_path.exists() else packaged_assets / "join_rules.json"
    )

    schema_catalog = LocalSchemaCatalog.from_legacy_files(
        schema_path=schema_path,
        join_rules_path=join_rules_path,
        business_rules=[
            "Prefer schema-first SQL generation when cache reuse is not safe.",
            "Only generate executable SELECT statements.",
        ],
    )
    prompt_builder = SqlPromptBuilder()
    embedding = HashEmbeddingBackend()
    cache_store = InMemoryCacheStore(embedding_backend=embedding)
    use_real_llm = os.getenv("NL2SQL_REBUILD_USE_LEGACY_LLM", "0") == "1"
    use_real_db = os.getenv("NL2SQL_REBUILD_USE_LEGACY_DB", "0") == "1"
    use_real_wecom = os.getenv("NL2SQL_REBUILD_USE_LEGACY_WECOM", "0") == "1"
    legacy_env = os.getenv("NL2SQL_REBUILD_LEGACY_ENV", os.getenv("AI_NL2SQL_ENV", "local"))

    sql_generator = (
        LegacyLlmSqlGenerator(prompt_builder=prompt_builder, root_dir=root, env_name=legacy_env)
        if use_real_llm
        else HeuristicSqlGenerator(prompt_builder=prompt_builder)
    )
    sql_executor = (
        LegacySqlExecutor(root_dir=root, env_name=legacy_env)
        if use_real_db
        else GuardedSqlExecutor()
    )
    notifier = (
        LegacyWeComNotifier(root_dir=root, env_name=legacy_env)
        if use_real_wecom
        else None
    )

    return RuntimeBundle(
        workflow=CacheFirstNl2SqlWorkflow(
            query_normalizer=RuleBasedQueryNormalizer(),
            cache_router=CacheRouter(
                embedding_backend=embedding,
                cache_store=cache_store,
                top_k=5,
                similarity_threshold=0.77,
            ),
            reuse_validator=ReuseValidator(),
            generation_path=UnifiedGenerationPath(
                evidence_retriever=SchemaEvidenceRetriever(schema_catalog=schema_catalog),
                sql_generator=sql_generator,
                evidence_top_k=8,
            ),
            sql_executor=sql_executor,
            cache_store=cache_store,
        ),
        schema_catalog=schema_catalog,
        notifier=notifier,
    )


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
