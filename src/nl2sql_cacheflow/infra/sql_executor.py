from __future__ import annotations

import re
from dataclasses import dataclass, field

from nl2sql_cacheflow.domain.models import ExecutionResult


_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b",
    flags=re.IGNORECASE,
)


@dataclass
class GuardedSqlExecutor:
    rows_by_sql: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def execute_and_validate(self, schema_id: str, sql: str) -> ExecutionResult:
        self.calls.append(sql)
        if sql is None or not sql.strip():
            return ExecutionResult(valid=False, status="invalid", sql=sql or "", error="empty_sql")
        if not sql.strip().lower().startswith("select"):
            return ExecutionResult(valid=False, status="rejected", sql=sql, error="only_select_allowed")
        if _FORBIDDEN_SQL.search(sql):
            return ExecutionResult(valid=False, status="rejected", sql=sql, error="forbidden_keyword")
        rows = self.rows_by_sql.get(sql, [])
        return ExecutionResult(valid=True, status="ok", sql=sql, rows=rows)
