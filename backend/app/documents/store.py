import asyncio

import httpx

from ..config import Settings


class StoreUnavailable(Exception):
    """A dependency failure, distinct from missing documents or invalid uploads."""


class QdrantDocumentStore:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.base = str(settings.qdrant_url).rstrip("/")
        self.headers = {"api-key": settings.qdrant_api_key.get_secret_value()}
        self.documents = f"{settings.document_collection_prefix}_documents_v1"
        self.revisions = f"{settings.document_collection_prefix}_revisions_v1"
        self.initialized = False
        self.initialization_lock = asyncio.Lock()

    async def request(self, method, collection, suffix="", *, body=None, missing_ok=False):
        try:
            response = await self.client.request(
                method,
                f"{self.base}/collections/{collection}{suffix}",
                headers=self.headers,
                json=body,
                timeout=15.0,
            )
            if missing_ok and response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()["result"]
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise StoreUnavailable from error

    async def initialize(self):
        async with self.initialization_lock:
            if self.initialized:
                return
            for collection in (self.documents, self.revisions):
                existing = await self.request("GET", collection, missing_ok=True)
                if existing is None:
                    await self.request("PUT", collection, body={"vectors": {}})
            # Qdrant Cloud strict mode requires indexes for filtered queries.
            for field, schema in (("deleted", "bool"), ("content_sha256", "keyword")):
                await self.request(
                    "PUT",
                    self.documents,
                    "/index?wait=true",
                    body={"field_name": field, "field_schema": schema},
                )
            self.initialized = True

    async def put(self, collection, point_id, payload):
        result = await self.request(
            "PUT",
            collection,
            "/points?wait=true",
            body={
                "points": [{"id": point_id, "vector": {}, "payload": payload}],
            },
        )
        if not isinstance(result, dict) or result.get("status") != "completed":
            raise StoreUnavailable

    async def get_many(self, collection, ids):
        if not ids:
            return {}
        result = await self.request(
            "POST",
            collection,
            "/points",
            missing_ok=True,
            body={"ids": ids, "with_payload": True, "with_vector": False},
        )
        if result is None:
            return {}
        return {str(item["id"]): item["payload"] for item in result}

    async def get(self, collection, point_id):
        return (await self.get_many(collection, [point_id])).get(point_id)

    async def scroll(self, *, limit=20, cursor=None, digest=None):
        conditions = [{"key": "deleted", "match": {"value": False}}]
        if digest:
            conditions.append({"key": "content_sha256", "match": {"value": digest}})
        result = await self.request(
            "POST",
            self.documents,
            "/points/scroll",
            missing_ok=True,
            body={
                "filter": {"must": conditions},
                "limit": limit,
                "offset": cursor,
                "with_payload": True,
                "with_vector": False,
            },
        )
        if result is None:
            return [], None
        return [item["payload"] for item in result["points"]], result.get("next_page_offset")
