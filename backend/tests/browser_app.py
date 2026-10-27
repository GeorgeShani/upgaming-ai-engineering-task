"""Isolated real FastAPI routes with in-memory Qdrant/OpenAI fakes for browser tests."""

import tempfile
from pathlib import Path

from app.config import Settings
from app.main import create_app
from fake_services import fake_services

temporary = tempfile.TemporaryDirectory(prefix="investigation-browser-")
storage, transport = fake_services()
app = create_app(
    Settings(
        _env_file=None,
        openai_api_key="fixture-openai",
        qdrant_url="https://storage.example",
        qdrant_api_key="fixture-storage",
        demo_admin_token="browser-fixture-admin",
        usage_db=Path(temporary.name) / "usage.sqlite3",
    ),
    transport=transport,
)


@app.middleware("http")
async def mark_test_server(request, call_next):
    response = await call_next(request)
    response.headers["X-Test-Providers"] = "in-memory-only"
    return response


@app.post("/api/__test/reset")
async def reset_memory_fixture():
    """Test process only: this route is never registered on the production app."""
    for collection, points in storage.collections.items():
        points.clear()
        storage.vectors[collection].clear()
    storage.response_calls.clear()
    app.state.investigation_rate_limit.accepted.clear()
    return {"reset": "in-memory-only"}
