from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SemanticSlots:
    entities: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    time_constraints: list[str] = field(default_factory=list)
    ordering: list[str] = field(default_factory=list)
    grouping: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QueryInput:
    question: str
    schema_id: str


@dataclass(slots=True)
class SchemaContext:
    schema_id: str
    dialect: str = "sqlite"
    tables: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TableSchema:
    name: str
    fields: dict[str, str]
    description: str = ""


@dataclass(slots=True)
class JoinPlan:
    need_join: bool = False
    join_table: str | None = None
    on: str | None = None
    fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class JoinRule:
    join_table: str
    on: str
    trigger_keywords: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    exclude_if_main_has: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedQuery:
    raw_question: str
    normalized_question: str
    schema_id: str
    slots: SemanticSlots
    candidate_tables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CacheEntry:
    question: str
    normalized_question: str
    schema_id: str
    sql: str
    slots: SemanticSlots
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceBundle:
    schema_summary: str
    join_hints: list[str] = field(default_factory=list)
    business_hints: list[str] = field(default_factory=list)
    cache_examples: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SqlCandidate:
    sql: str
    source: str
    score: float | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PromptContext:
    prompt: str
    main_table: str | None = None
    join_plan: JoinPlan = field(default_factory=JoinPlan)
    time_hint: str = ""


@dataclass(slots=True)
class ExecutionResult:
    valid: bool
    status: str
    sql: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class WorkflowTrace:
    normalized_question: str
    cache_similarity: float | None = None
    cache_selected_question: str | None = None
    cache_reuse_allowed: bool = False
    generation_evidence: EvidenceBundle | None = None
    generated_candidates: list[SqlCandidate] = field(default_factory=list)
    selected_strategy: str = "generate"
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InferenceResult:
    sql: str | None
    execution_result: Any = None
    reused_from_cache: bool = False
    trace: WorkflowTrace | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
