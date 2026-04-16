# Experiment Findings

This file translates the previous work in `Ai_nl2sql/` and `semantic_cache_lab_full/`
into decisions for the clean rebuild.

## Legacy Inputs Reviewed

- `Ai_nl2sql/app/services/query_pipeline.py`
- `Ai_nl2sql/app/services/query_pipeline_v7.py`
- `Ai_nl2sql/app/services/semantic_cache_v3.py`
- `Ai_nl2sql/app/services/semantic_cache_manager.py`
- `Ai_nl2sql/semantic_cache_lab_full/`

## Findings We Are Preserving

1. The cache-first idea is useful for repeated intents.
   Legacy evidence:
   `query_pipeline.py` tries cache lookup before generation, which reduces cost and latency.

2. Reuse cannot depend on embedding similarity alone.
   Legacy evidence:
   `semantic_cache_v3.py` already moved beyond pure top-1 vector match and added equivalence checks.

3. The experiment wrapper was valuable as instrumentation, not as architecture.
   Legacy evidence:
   `query_pipeline_v7.py` added flags, timing, and experiment logs, but it still depended on one large legacy pipeline.

4. Schema-first generation is the stable baseline.
   Legacy evidence:
   both the old service path and the Spider evaluation scripts revolve around schema context, joins, time parsing, and SQL generation.

## Rebuild Decisions

1. Keep one canonical workflow instead of `v2`, `v6`, `v7`, lab, and paper-specific controllers.
2. Keep cache routing and safety validation as first-class modules.
3. Keep experiment instrumentation, but attach it as workflow trace metadata instead of a separate wrapper pipeline.
4. Keep benchmark scripts outside the runtime package.

## What Is Explicitly Not In Scope For The Core Package

1. FastAPI pages and legacy UI templates
2. one-off benchmark shell scripts
3. FAISS/MySQL operational commands in the core workflow
4. paper-specific evaluation heuristics embedded in runtime code
