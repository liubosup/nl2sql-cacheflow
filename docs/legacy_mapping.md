# Legacy Mapping

This table explains how the old project maps into the rebuilt package.

| Legacy area | Problem | Rebuild destination |
| --- | --- | --- |
| `app/services/query_pipeline.py` | orchestration mixed with prompting, execution, cache, logging | `application/workflow.py` plus small service modules |
| `app/services/query_pipeline_v7.py` | experiment wrapper around a large legacy pipeline | workflow trace metadata and future experiment harness |
| `app/services/semantic_cache_v3.py` | data access and reuse policy partly entangled | `infra/cache_store.py`, `services/cache_router.py`, `services/reuse_validator.py` |
| `app/services/semantic_cache_manager.py` | operational lifecycle code mixed near runtime modules | future admin tooling outside the core package |
| `semantic_cache_lab_full/scripts/*` | benchmark and paper scripts in main tree | future `experiments/` package or standalone scripts |
| `app/services/rag_*` | retrieval logic versioned across many files | one evidence retriever interface in `domain/protocols.py` |
| `app/services/sql_rerank*` | generation and ranking logic tightly coupled to prompts | one SQL generator adapter returning candidate objects |
| `app/data/schema_config.json` + `app/data/join_rules.json` | runtime assets coupled to legacy services | `infra/schema_catalog.py` loaded by `application/runtime.py` |

## Migration Rule Of Thumb

If a file exists mainly to support runtime inference, it belongs in `src/nl2sql_cacheflow/`.
If it exists mainly to compare variants, run sweeps, or generate paper figures, it should stay outside the runtime package.
