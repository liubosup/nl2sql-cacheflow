from __future__ import annotations

from dataclasses import dataclass, field

from nl2sql_cacheflow.domain.models import EvidenceBundle, NormalizedQuery, SqlCandidate
from nl2sql_cacheflow.domain.protocols import PromptBuilder


@dataclass
class HeuristicSqlGenerator:
    prompt_builder: PromptBuilder
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate(self, query: NormalizedQuery, evidence: EvidenceBundle) -> list[SqlCandidate]:
        prompt_context = self.prompt_builder.build(query, evidence)
        table = prompt_context.main_table or self._fallback_table(query)
        sql = self._render_sql(query, table)
        self.calls.append(
            {
                "normalized_question": query.normalized_question,
                "main_table": table,
                "prompt": prompt_context.prompt,
                "sql": sql,
            }
        )
        return [SqlCandidate(sql=sql, source="heuristic-generator", score=0.5)]

    def _render_sql(self, query: NormalizedQuery, table: str) -> str:
        metric = query.slots.metrics[0] if query.slots.metrics else ""
        select_expr = "COUNT(*) AS value" if metric == "count" else "*"
        if metric in {"sum", "total"}:
            target_field = "gmv" if "gmv" in query.normalized_question else "amount"
            select_expr = f"SUM({target_field}) AS value"
        if metric in {"avg", "average"}:
            target_field = "gmv" if "gmv" in query.normalized_question else "amount"
            select_expr = f"AVG({target_field}) AS value"
        if metric in {"max", "min"}:
            target_field = "gmv" if "gmv" in query.normalized_question else "amount"
            select_expr = f"{metric.upper()}({target_field}) AS value"

        where_parts: list[str] = []
        for token in query.slots.time_constraints:
            if token.isdigit() and len(token) == 4:
                where_parts.append(f"create_year = '{token}'")
        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        limit_clause = "" if select_expr != "*" else " LIMIT 20"
        return f"SELECT {select_expr} FROM {table}{where_clause}{limit_clause}"

    def _fallback_table(self, query: NormalizedQuery) -> str:
        return query.candidate_tables[0] if query.candidate_tables else "unknown_table"
