import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.documents.routes import router as document_router
from app.documents.security import DocumentMutationBoundary
from app.documents.service import DocumentService
from app.documents.store import QdrantDocumentStore, StoreUnavailable
from app.health import HealthReport, check_health
from app.investigations.routes import DemoRateLimit
from app.investigations.routes import router as investigation_router
from app.investigations.service import InvestigationService
from app.providers import BudgetExceeded, OpenAIProvider, ProviderError
from app.retrieval.index import ChunkIndex
from app.retrieval.search import SearchService

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    frontend_dist: Path = FRONTEND_DIST,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings if settings is not None else Settings()
        async with httpx.AsyncClient(timeout=5.0, transport=transport) as client:
            app.state.http_client = client
            config = app.state.settings
            app.state.parsing_slots = asyncio.Semaphore(1)
            app.state.search_service = None
            app.state.investigation_service = None
            app.state.investigation_slots = asyncio.Semaphore(1)
            app.state.investigation_rate_limit = DemoRateLimit()
            app.state.provider = None
            app.state.document_service = None
            if config.qdrant_url and config.qdrant_api_key.get_secret_value():
                store = QdrantDocumentStore(client, config)
                indexer = None
                if config.openai_api_key.get_secret_value():
                    app.state.provider = OpenAIProvider(client, config)
                    indexer = ChunkIndex(store, app.state.provider, config)
                app.state.document_service = DocumentService(store, indexer)
                if indexer:
                    app.state.search_service = SearchService(indexer, app.state.document_service)
                    app.state.investigation_service = InvestigationService(
                        app.state.search_service, app.state.provider
                    )
            yield

    app = FastAPI(title="AI Investigation Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(DocumentMutationBoundary, settings=lambda: app.state.settings)
    app.include_router(document_router)
    app.include_router(investigation_router)

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, error: ProviderError):
        return JSONResponse({"detail": "Model provider failed. No answer was produced."}, 502)

    @app.exception_handler(BudgetExceeded)
    async def budget_error(request: Request, error: BudgetExceeded):
        return JSONResponse({"detail": "Local API spending limit reached."}, 503)

    @app.exception_handler(StoreUnavailable)
    async def storage_error(request: Request, error: StoreUnavailable):
        return JSONResponse(
            {"detail": "Document storage is unavailable. Retry the operation."}, 503
        )

    @app.get("/api/live")
    async def live() -> dict[str, str]:
        """Process liveness for the hosting platform; no external API calls."""
        return {"status": "running"}

    @app.get("/api/health", response_model=HealthReport, responses={503: {"model": HealthReport}})
    async def health(request: Request) -> JSONResponse:
        report = await check_health(request.app.state.settings, request.app.state.http_client)
        return JSONResponse(
            report.model_dump(),
            status_code=200 if report.status == "ready" else 503,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/", include_in_schema=False, response_model=None)
    async def index() -> FileResponse | JSONResponse:
        if not (frontend_dist / "index.html").is_file():
            return JSONResponse(
                {"detail": "Build the frontend with npm run build in frontend/."}, 503
            )
        return FileResponse(frontend_dist / "index.html")

    # Scope static serving to /assets: unknown /api routes must remain JSON 404s.
    if (frontend_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    return app


app = create_app()
