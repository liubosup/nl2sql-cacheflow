from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class QueryLogRecord:
    id: str
    question: str
    normalized_question: str
    sql: str
    summary: str
    result_rows: list[dict[str, Any]] = field(default_factory=list)
    status: str = "success"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reused_from_cache: bool = False
    main_table: str | None = None
    time_hint: str = ""
    query_info: str = ""
