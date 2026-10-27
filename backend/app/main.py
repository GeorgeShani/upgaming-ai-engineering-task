from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.health import HealthReport, check_health

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
            yield

    app = FastAPI(title="AI Investigation Engine", version="0.1.0", lifespan=lifespan)

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
