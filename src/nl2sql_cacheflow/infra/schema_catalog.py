from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from nl2sql_cacheflow.domain.models import EvidenceBundle, JoinRule, NormalizedQuery, TableSchema


@dataclass(slots=True)
class LocalSchemaCatalog:
    tables: dict[str, TableSchema]
    join_rules: list[JoinRule] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized: dict[str, TableSchema] = {}
        for name, table in self.tables.items():
            if isinstance(table, TableSchema):
                normalized[name] = table
            else:
                normalized[name] = TableSchema(
                    name=table.get("name", name),
                    fields=table.get("fields", {}),
                    description=table.get("description", ""),
                )
        self.tables = normalized
        normalized_join_rules: list[JoinRule] = []
        for rule in self.join_rules:
            if isinstance(rule, JoinRule):
                normalized_join_rules.append(rule)
            else:
                required_fields = rule.get("required_fields", [])
                if isinstance(required_fields, str):
                    required_fields = [required_fields]
                exclude_if_main_has = rule.get("exclude_if_main_has", [])
                if isinstance(exclude_if_main_has, str):
                    exclude_if_main_has = [exclude_if_main_has]
                normalized_join_rules.append(
                    JoinRule(
                        join_table=rule["join_table"],
                        on=rule["on"],
                        trigger_keywords=list(rule.get("trigger_keywords", [])),
                        required_fields=list(required_fields),
                        exclude_if_main_has=list(exclude_if_main_has),
                    )
                )
        self.join_rules = normalized_join_rules

    @classmethod
    def from_json(cls, path: str | Path) -> "LocalSchemaCatalog":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        tables = {
            name: TableSchema(name=name, fields=value.get("fields", {}))
            for name, value in raw.items()
        }
        return cls(tables=tables)

    @classmethod
    def from_legacy_files(
        cls,
        schema_path: str | Path,
        join_rules_path: str | Path | None = None,
        business_rules: list[str] | None = None,
    ) -> "LocalSchemaCatalog":
        raw_schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        raw_join_rules = []
        if join_rules_path is not None and Path(join_rules_path).exists():
            raw_join_rules = json.loads(Path(join_rules_path).read_text(encoding="utf-8"))
        return cls(
            tables={
                name: TableSchema(name=name, fields=value.get("fields", {}))
                for name, value in raw_schema.items()
            },
            join_rules=raw_join_rules,
            business_rules=business_rules or [],
        )

    def match_main_table(self, query: NormalizedQuery) -> TableSchema | None:
        token_set = set(query.normalized_question.split())
        best_table: TableSchema | None = None
        best_score = -1
        for table in self.tables.values():
            table_tokens = set(table.name.lower().replace(".", " ").split())
            field_tokens = set(table.fields.keys())
            score = len(token_set & table_tokens) * 3 + len(token_set & field_tokens)
            if any(candidate in table.name for candidate in query.candidate_tables):
                score += 2
            if score > best_score:
                best_table = table
                best_score = score
        return best_table

    def build_evidence(self, query: NormalizedQuery, k: int) -> EvidenceBundle:
        main_table = self.match_main_table(query)
        if main_table is None:
            return EvidenceBundle(schema_summary="", business_hints=self.business_rules[:k])

        field_lines = [f"- {name}: {typ}" for name, typ in list(main_table.fields.items())[:k]]
        join_hints = self._match_join_hints(query, main_table)
        return EvidenceBundle(
            schema_summary=f"main table: {main_table.name}\n" + "\n".join(field_lines),
            join_hints=join_hints[:k],
            business_hints=self.business_rules[:k],
            cache_examples=[f"candidate tables: {', '.join(query.candidate_tables)}"]
            if query.candidate_tables
            else [],
        )

    def _match_join_hints(self, query: NormalizedQuery, main_table: TableSchema) -> list[str]:
        hits: list[str] = []
        question = query.raw_question
        main_fields_lower = {field.lower() for field in main_table.fields}
        for rule in self.join_rules:
            if not any(keyword in question for keyword in rule.trigger_keywords):
                continue
            if any(field.lower() in main_fields_lower for field in rule.exclude_if_main_has):
                continue
            required_fields = ", ".join(rule.required_fields) if rule.required_fields else "n/a"
            hits.append(f"{rule.join_table} ON {rule.on} FIELDS {required_fields}")
        return hits
