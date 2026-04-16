from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from nl2sql_cacheflow.application.workflow import CacheFirstNl2SqlWorkflow
from nl2sql_cacheflow.domain.logs import QueryLogRecord
from nl2sql_cacheflow.domain.models import ExecutionResult, QueryInput
from nl2sql_cacheflow.domain.protocols import SchemaCatalog
from nl2sql_cacheflow.infra.log_store import JsonlQueryLogStore


@dataclass(slots=True)
class QueryResponse:
    question: str
    sql: str
    result: list[dict[str, Any]]
    summary: str
    query_info: str
    time_range: str
    show_download: bool = False
    reused_from_cache: bool = False


class QueryApplicationService:
    def __init__(
        self,
        workflow: CacheFirstNl2SqlWorkflow,
        log_store: JsonlQueryLogStore,
        schema_catalog: SchemaCatalog | None = None,
        notifier: Any | None = None,
        schema_id: str = "legacy",
        csv_export_path: str | Path | None = None,
    ) -> None:
        self._workflow = workflow
        self._log_store = log_store
        self._schema_catalog = schema_catalog
        self._notifier = notifier
        self._schema_id = schema_id
        self._csv_export_path = Path(csv_export_path) if csv_export_path is not None else None

    def ask(self, question: str) -> QueryResponse:
        result = self._workflow.run(QueryInput(question=question, schema_id=self._schema_id))
        execution_result = result.execution_result
        rows = execution_result.rows if isinstance(execution_result, ExecutionResult) else []
        query_info = self._build_query_info(result)
        summary = self._build_summary(result, rows)
        time_hint = result.trace.generation_evidence.business_hints[0] if (
            result.trace and result.trace.generation_evidence and result.trace.generation_evidence.business_hints
        ) else (result.trace.generation_evidence.cache_examples[0] if result.trace and result.trace.generation_evidence and result.trace.generation_evidence.cache_examples else "")
        response = QueryResponse(
            question=question,
            sql=result.sql or "",
            result=rows,
            summary=summary,
            query_info=query_info,
            time_range=result.trace.normalized_question if result.trace else "",
            show_download=bool(rows and self._csv_export_path),
            reused_from_cache=result.reused_from_cache,
        )
        self._write_csv_export(rows)
        self._log_store.append(
            QueryLogRecord(
                id=uuid4().hex[:8],
                question=question,
                normalized_question=result.trace.normalized_question if result.trace else question,
                sql=response.sql,
                summary=response.summary,
                result_rows=rows,
                status="success" if getattr(execution_result, "valid", False) else "failed",
                reused_from_cache=result.reused_from_cache,
                main_table=self._extract_main_table(result),
                time_hint=time_hint,
                query_info=query_info,
            )
        )
        return response

    def history(self, limit: int = 50) -> list[QueryLogRecord]:
        return self._log_store.latest(limit=limit)

    def classify_domain(self, question: str) -> dict[str, str]:
        if self._schema_catalog is None:
            return {"domain": "unknown", "table": "unknown"}
        normalized = question.strip().lower()
        tokens = [token for token in normalized.replace(".", " ").split() if token]
        dummy_query = QueryInput(question=question, schema_id=self._schema_id)
        workflow_query = self._workflow._query_normalizer.normalize(dummy_query.question, dummy_query.schema_id)  # type: ignore[attr-defined]
        table = self._schema_catalog.match_main_table(workflow_query)
        table_name = table.name if table else "unknown"
        domain = table_name.split(".")[0] if "." in table_name else (tokens[0] if tokens else "general")
        return {"domain": domain, "table": table_name}

    def ask_wecom(self, question: str) -> dict[str, Any]:
        response = self.ask(question)
        payload = asdict(response)
        if self._notifier is not None:
            payload["push_result"] = self._notifier.send(
                f"【问】{question}\n【SQL】{response.sql}\n【答】{response.summary}"
            )
        else:
            payload["push_result"] = {"ok": False, "error": "notifier_not_configured"}
        return payload

    @property
    def csv_export_path(self) -> Path | None:
        return self._csv_export_path

    def _build_query_info(self, result: Any) -> str:
        if result.trace is None:
            return ""
        parts = [
            f"normalized_question: {result.trace.normalized_question}",
            f"strategy: {result.trace.selected_strategy}",
        ]
        if result.trace.cache_similarity is not None:
            parts.append(f"cache_similarity: {result.trace.cache_similarity:.4f}")
        if result.trace.generation_evidence is not None:
            parts.append("schema_evidence:")
            parts.append(result.trace.generation_evidence.schema_summary)
        return "\n".join(parts)

    def _build_summary(self, result: Any, rows: list[dict[str, Any]]) -> str:
        if result.reused_from_cache:
            return f"命中语义缓存，返回 {len(rows)} 条结果。"
        return f"已通过重建后的工作流生成 SQL，返回 {len(rows)} 条结果。"

    def _extract_main_table(self, result: Any) -> str | None:
        if result.trace is None or result.trace.generation_evidence is None:
            return None
        for line in result.trace.generation_evidence.schema_summary.splitlines():
            prefix = "main table: "
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return None

    def _write_csv_export(self, rows: list[dict[str, Any]]) -> None:
        if self._csv_export_path is None:
            return
        self._csv_export_path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            self._csv_export_path.write_text("no_data\n", encoding="utf-8")
            return
        fieldnames = list(rows[0].keys())
        with self._csv_export_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
