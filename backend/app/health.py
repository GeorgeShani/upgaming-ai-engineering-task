import asyncio
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.config import Settings


class DependencyHealth(BaseModel):
    status: Literal["unconfigured", "reachable", "unavailable"]
    message: str


class HealthReport(BaseModel):
    status: Literal["ready", "degraded"]
    app: Literal["running"] = "running"
    dependencies: dict[str, DependencyHealth]


async def probe(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> DependencyHealth:
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError:
        # Never return provider response bodies: they can contain sensitive configuration.
        return DependencyHealth(status="unavailable", message="Provider rejected the access check.")
    except httpx.RequestError:
        return DependencyHealth(
            status="unavailable", message="Provider connection failed or timed out."
        )
    return DependencyHealth(status="reachable", message="Read-only access check passed.")


async def check_health(settings: Settings, client: httpx.AsyncClient) -> HealthReport:
    async def openai() -> DependencyHealth:
        key = settings.openai_api_key.get_secret_value()
        if not key:
            return DependencyHealth(
                status="unconfigured", message="Set OPENAI_API_KEY on the server."
            )
        results = await asyncio.gather(
            *(
                probe(
                    client,
                    f"https://api.openai.com/v1/models/{quote(model, safe='')}",
                    {"Authorization": f"Bearer {key}"},
                )
                for model in (settings.generation_model, settings.embedding_model)
            )
        )
        return next((r for r in results if r.status != "reachable"), results[0])

    async def qdrant() -> DependencyHealth:
        key = settings.qdrant_api_key.get_secret_value()
        if not settings.qdrant_url or not key:
            return DependencyHealth(
                status="unconfigured", message="Set QDRANT_URL and QDRANT_API_KEY on the server."
            )
        return await probe(
            client, f"{str(settings.qdrant_url).rstrip('/')}/collections", {"api-key": key}
        )

    ai, database = await asyncio.gather(openai(), qdrant())
    dependencies = {"openai": ai, "qdrant": database}
    ready = all(item.status == "reachable" for item in dependencies.values())
    return HealthReport(status="ready" if ready else "degraded", dependencies=dependencies)
