from __future__ import annotations

from nl2sql_cacheflow.domain.models import EvidenceBundle, JoinPlan, NormalizedQuery, PromptContext


class SqlPromptBuilder:
    """Builds a compact runtime prompt context from normalized query evidence."""

    def build(self, query: NormalizedQuery, evidence: EvidenceBundle) -> PromptContext:
        main_table = self._extract_main_table_name(evidence.schema_summary)
        time_hint = ", ".join(query.slots.time_constraints)
        join_plan = JoinPlan(need_join=bool(evidence.join_hints))
        if evidence.join_hints:
            join_plan.on = evidence.join_hints[0]
            first_join = evidence.join_hints[0].split(" ON ", 1)[0]
            join_plan.join_table = first_join

        lines = [
            "You are an NL2SQL generator.",
            f"Question: {query.raw_question}",
            f"Normalized: {query.normalized_question}",
        ]
        if evidence.schema_summary:
            lines.extend(["Schema:", evidence.schema_summary])
        if evidence.business_hints:
            lines.extend(["Business rules:"] + [f"- {item}" for item in evidence.business_hints])
        if evidence.join_hints:
            lines.extend(["Join hints:"] + [f"- {item}" for item in evidence.join_hints])
        if time_hint:
            lines.append(f"Time hint: {time_hint}")
        lines.append("Return one executable SELECT statement only.")

        return PromptContext(
            prompt="\n".join(lines),
            main_table=main_table,
            join_plan=join_plan,
            time_hint=time_hint,
        )

    def _extract_main_table_name(self, schema_summary: str) -> str | None:
        prefix = "main table: "
        for line in schema_summary.splitlines():
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return None
