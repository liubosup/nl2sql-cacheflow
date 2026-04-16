# NL2SQL Cacheflow

`nl2sql-cacheflow/` is the clean project that replaces the mixed legacy layout in `Ai_nl2sql/`.
It keeps the useful ideas from the old production path and the cache-reuse experiments,
but drops versioned wrappers, one-off scripts, and cross-layer coupling.

## What We Are Keeping

1. Cache-first routing is valuable, but only with safety validation.
2. Schema-first evidence retrieval is the default SQL generation path.
3. SQL generation, cache reuse, execution, and experiment harnesses must be separate modules.

## What We Are Leaving Behind

1. Pipeline controllers that mix orchestration, persistence, logging, and prompting.
2. Versioned service files like `query_pipeline_v7.py` used as long-term architecture.
3. Experiment-only scripts living in the same package as production code.

## New Layout

- `src/nl2sql_cacheflow/domain`: canonical models and interfaces.
- `src/nl2sql_cacheflow/services`: reusable routing, safety, and generation logic.
- `src/nl2sql_cacheflow/infra`: deterministic local adapters and future external integrations.
- `src/nl2sql_cacheflow/application`: top-level cache-first workflow.
- `docs/experiment_findings.md`: what the previous experiments proved.
- `docs/legacy_mapping.md`: how old files map into the new structure.
- `tests/`: regression tests for the clean workflow.

## Current Status

The project now has a stable cache-first workflow with:

1. query normalization
2. vector-style cache routing
3. slot-based safety validation
4. schema-first evidence collection
5. candidate SQL generation
6. execution validation
7. write-back to cache with workflow trace metadata

The next active layer is now in place too:

1. schema catalog adapter
2. prompt-context builder
3. guarded SQL executor policy
4. legacy-backed runtime assembly

## How To Verify

```bash
python3 -m unittest discover -s tests -v
```

## Run The Web App

After installing dependencies:

```bash
uvicorn nl2sql_cacheflow.main:app --app-dir src --host 0.0.0.0 --port 8082 --reload
```

The rebuilt app exposes:

1. `/` for the main query UI
2. `/ask` for HTML form submission
3. `/analyze` for JSON API access
4. `/logs` for recent query history
5. `/classify_domain` for domain/table classification
6. `/wecom_query` for a WeCom-compatible query endpoint
7. `/download_csv` for the latest exported result file

## Optional Legacy Integrations

The rebuilt app can switch from safe local adapters to the legacy external integrations.

Set these environment variables before starting the app:

```bash
export NL2SQL_REBUILD_USE_LEGACY_LLM=1
export NL2SQL_REBUILD_USE_LEGACY_DB=1
export NL2SQL_REBUILD_USE_LEGACY_WECOM=1
export NL2SQL_REBUILD_LEGACY_ENV=local
```

Notes:

1. `NL2SQL_REBUILD_USE_LEGACY_LLM=1` uses the old `_call_llm` bridge.
2. `NL2SQL_REBUILD_USE_LEGACY_DB=1` uses the old SQL executor.
3. `NL2SQL_REBUILD_USE_LEGACY_WECOM=1` enables WeCom push from `/wecom_query`.
4. `NL2SQL_REBUILD_LEGACY_ENV` maps to the old config environment such as `local`, `test`, or `pro`.

## Standalone Assets

This repository vendors the required `schema_config.json` and `join_rules.json` under
`assets/legacy/`, so it can run independently even when the old `Ai_nl2sql/` repo is not present.
