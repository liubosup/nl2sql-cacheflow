from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from nl2sql_cacheflow.domain.logs import QueryLogRecord


class JsonlQueryLogStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def append(self, record: QueryLogRecord) -> None:
        payload = asdict(record)
        payload["created_at"] = record.created_at.isoformat()
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def latest(self, limit: int = 50) -> list[QueryLogRecord]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        records: list[QueryLogRecord] = []
        for line in reversed(lines[-limit:]):
            if not line.strip():
                continue
            payload = json.loads(line)
            payload["created_at"] = datetime.fromisoformat(payload["created_at"])
            records.append(QueryLogRecord(**payload))
        return records
