from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from nl2sql_cacheflow.domain.models import EvidenceBundle, ExecutionResult, NormalizedQuery, SqlCandidate
from nl2sql_cacheflow.domain.protocols import PromptBuilder


def _legacy_repo_root(root_dir: str | Path | None = None) -> Path:
    if root_dir is not None:
        root = Path(root_dir)
        if root.name == "Ai_nl2sql":
            return root
        candidate = root / "Ai_nl2sql"
        return candidate if candidate.exists() else root
    package_root = Path(__file__).resolve().parents[4]
    candidate = package_root / "Ai_nl2sql"
    return candidate if candidate.exists() else package_root


def _prepare_legacy_imports(root_dir: str | Path | None = None, env_name: str | None = None) -> Path:
    repo_root = _legacy_repo_root(root_dir)
    legacy_root = str(repo_root)
    if legacy_root not in sys.path:
        sys.path.insert(0, legacy_root)
    if env_name:
        os.environ["AI_NL2SQL_ENV"] = env_name
    return repo_root


def _extract_sql(text: str) -> str:
    cleaned = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    match = re.search(r"(select[\s\S]+)", cleaned, flags=re.IGNORECASE)
    return match.group(1).strip() if match else cleaned


@dataclass
class LegacyLlmSqlGenerator:
    prompt_builder: PromptBuilder
    root_dir: str | Path | None = None
    env_name: str | None = None
    backend: str | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate(self, query: NormalizedQuery, evidence: EvidenceBundle) -> list[SqlCandidate]:
        _prepare_legacy_imports(self.root_dir, self.env_name)
        from app.adapters.llm_bridge import _call_llm  # type: ignore
        from config import LLM_TYPE  # type: ignore

        prompt_context = self.prompt_builder.build(query, evidence)
        backend_name = self.backend or LLM_TYPE
        raw = _call_llm(prompt_context.prompt, backend=backend_name)
        sql = _extract_sql(raw)
        self.calls.append(
            {
                "backend": backend_name,
                "prompt": prompt_context.prompt,
                "raw": raw,
                "sql": sql,
            }
        )
        return [SqlCandidate(sql=sql, source=f"legacy-llm:{backend_name}", score=1.0)]


@dataclass
class LegacySqlExecutor:
    root_dir: str | Path | None = None
    env_name: str | None = None
    calls: list[str] = field(default_factory=list)

    def execute_and_validate(self, schema_id: str, sql: str) -> ExecutionResult:
        self.calls.append(sql)
        _prepare_legacy_imports(self.root_dir, self.env_name)
        try:
            from app.services.sql_executor import execute_sql  # type: ignore

            rows = execute_sql(sql)
            return ExecutionResult(valid=True, status="ok", sql=sql, rows=rows)
        except Exception as exc:
            return ExecutionResult(valid=False, status="error", sql=sql, error=str(exc))


@dataclass
class LegacyWeComNotifier:
    root_dir: str | Path | None = None
    env_name: str | None = None

    def send(self, message: str) -> dict[str, object]:
        _prepare_legacy_imports(self.root_dir, self.env_name)
        try:
            from app.adapters.wecom_push import message_push_robot  # type: ignore
            from config import ROBOT_WEBHOOK_KEY  # type: ignore

            response = message_push_robot(ROBOT_WEBHOOK_KEY, message)
            return {"ok": True, "status_code": getattr(response, "status_code", None)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
