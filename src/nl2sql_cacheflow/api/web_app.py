from pathlib import Path
from typing import Any
from dataclasses import asdict
import os

from nl2sql_cacheflow.application.query_service import QueryApplicationService
from nl2sql_cacheflow.application.runtime import build_legacy_runtime_bundle
from nl2sql_cacheflow.infra.log_store import JsonlQueryLogStore


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Form, Request
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
        from fastapi.templating import Jinja2Templates
        from pydantic import BaseModel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI runtime dependencies are missing. Install the project dependencies first."
        ) from exc

    app = FastAPI(title="NL2SQL Rebuild")
    package_root = _resolve_app_root()
    templates = Jinja2Templates(directory=str(package_root / "templates"))
    app.mount("/static", StaticFiles(directory=str(package_root / "static")), name="static")

    runtime_bundle = build_legacy_runtime_bundle(root_dir=package_root.parent)
    csv_export_path = package_root / "runtime" / "last_detail.csv"
    service = QueryApplicationService(
        workflow=runtime_bundle.workflow,
        log_store=JsonlQueryLogStore(package_root / "runtime" / "query_logs.jsonl"),
        schema_catalog=runtime_bundle.schema_catalog,
        notifier=runtime_bundle.notifier,
        csv_export_path=csv_export_path,
    )

    class QueryRequest(BaseModel):
        question: str

    class DomainInput(BaseModel):
        question: str
        debug: bool = False

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"request": request, "suggestions": _default_suggestions()},
        )

    @app.post("/ask", response_class=HTMLResponse)
    async def ask_question(request: Request, question: str = Form(...)) -> Any:
        result = service.ask(question)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "question": question,
                "result": result,
                "suggestions": _default_suggestions(),
            },
        )

    @app.post("/analyze")
    async def analyze_query(req: QueryRequest) -> Any:
        return asdict(service.ask(req.question))

    @app.post("/wecom_query")
    async def wecom_query(req: QueryRequest) -> Any:
        return service.ask_wecom(req.question)

    @app.post("/classify_domain")
    async def classify_domain(input: DomainInput) -> Any:
        result = service.classify_domain(input.question)
        if input.debug:
            result["debug"] = {
                "source": "schema_catalog_match",
                "known_tables": len(runtime_bundle.schema_catalog.tables),
            }
        return result

    @app.get("/download_csv")
    async def download_csv() -> Any:
        if service.csv_export_path is None or not service.csv_export_path.exists():
            return JSONResponse({"error": "CSV文件不存在，请重新查询"}, status_code=404)
        return FileResponse(
            service.csv_export_path,
            media_type="text/csv",
            filename="query_detail.csv",
        )

    @app.get("/logs", response_class=HTMLResponse)
    async def show_logs(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="logs.html",
            context={"request": request, "logs": service.history()},
        )

    return app


def _default_suggestions() -> list[str]:
    return [
        "2024年订单数量是多少",
        "统计 2024 年华东区域 GMV",
        "昨天的 GMV 是多少",
        "北京瑰丽酒店去年4月交易订单明细",
        "今年每个月的 GMV",
    ]


def _resolve_app_root() -> Path:
    candidates = []
    env_root = os.getenv("NL2SQL_CACHEFLOW_HOME")
    if env_root:
        candidates.append(Path(env_root))
    candidates.extend(
        [
            Path.cwd(),
            Path(__file__).resolve().parents[3],
            Path(__file__).resolve().parents[4],
        ]
    )
    for candidate in candidates:
        if (candidate / "templates").exists() and (candidate / "static").exists():
            return candidate
    raise RuntimeError("Unable to locate application root with templates/ and static/ directories.")
