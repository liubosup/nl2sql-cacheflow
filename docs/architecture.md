# Architecture Notes

## Why The Rebuild Exists

The legacy `Ai_nl2sql/` tree contains three different concerns in one place:

1. user-facing NL2SQL service logic
2. semantic-cache experiments and paper evaluation code
3. maintenance scripts, datasets, and benchmark outputs

That made iteration fast, but it also made the system hard to reason about.

## Target Architecture

The rebuilt system has four explicit layers:

1. `domain`
   - typed models such as `NormalizedQuery`, `CacheEntry`, `EvidenceBundle`
   - protocols for normalizers, cache stores, generators, and executors

2. `services`
   - pure business logic
   - cache routing
   - reuse safety validation
   - evidence-driven SQL generation

3. `infra`
   - embeddings
   - vector stores
   - schema catalogs and evidence retrieval
   - SQL execution adapters
   - optional LLM-backed equivalence checks

4. `application`
   - one orchestration workflow that chooses reuse or generation
   - workflow trace collection for observability and experiments

## Two Lines, One Orchestrator

The workflow still has two paths, but the boundaries are clean now.

### Reuse Path

1. normalize the query
2. embed and search cache candidates
3. apply similarity threshold
4. apply slot-level safety validation
5. optionally apply semantic equivalence validation
6. reuse SQL only when all gates pass

### Generation Path

1. normalize the query
2. retrieve schema and business evidence
3. generate one or more SQL candidates
4. execute and validate the selected candidate
5. write verified query-SQL pairs back into cache

## Design Rule

Semantic cache is not RAG.

- cache stores verified historical question-SQL pairs for reuse
- retrieval provides schema and business evidence for new SQL generation

This separation is the main architectural lesson carried over from the earlier experiments.

## Current Rebuild Boundary

The clean project now includes deterministic local versions of:

1. schema evidence retrieval
2. prompt construction
3. execution guarding

That gives us a stable seam for plugging in the real schema registry, real prompt templates,
and real database adapters later without changing the orchestration layer.
