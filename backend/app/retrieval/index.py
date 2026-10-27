import asyncio
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from ..documents.store import StoreUnavailable
from .chunking import chunk_spans


class ChunkIndex:
    def __init__(self, store, provider, settings):
        self.store, self.provider, self.settings = store, provider, settings
        identity = f"v1:cl100k_base:256:40:bm25-defaults:{settings.embedding_model}:"
        identity += str(settings.embedding_dimensions)
        self.profile = sha256(identity.encode()).hexdigest()[:12]
        self.collections = {
            strategy: f"{settings.document_collection_prefix}_chunks_{strategy}_{self.profile}"
            for strategy in ("a", "b")
        }
        self.lock = asyncio.Lock()
        self.initialized = False

    async def initialize(self):
        async with self.lock:
            if self.initialized:
                return
            for collection in self.collections.values():
                existing = await self.store.request("GET", collection, missing_ok=True)
                if existing is None:
                    await self.store.request(
                        "PUT",
                        collection,
                        body={
                            "vectors": {
                                "dense": {
                                    "size": self.settings.embedding_dimensions,
                                    "distance": "Cosine",
                                    "on_disk": True,
                                }
                            },
                            "sparse_vectors": {"bm25": {"modifier": "idf"}},
                            "on_disk_payload": True,
                        },
                    )
            self.initialized = True

    def chunks(self, revisions):
        chunks = {"a": [], "b": []}
        for revision in revisions:
            sentences = [
                (loc.start, loc.end) for loc in revision.locations if loc.kind == "sentence"
            ] or None
            for strategy in chunks:
                for start, end in chunk_spans(revision.text, strategy, sentences):
                    locations = [
                        loc.model_dump()
                        for loc in revision.locations
                        if loc.start < end and loc.end > start
                    ]
                    # Do not copy whole page text into every chunk payload.
                    for location in locations:
                        location.pop("text")
                    key = f"{self.profile}:{strategy}:{revision.revision_id}:{start}:{end}"
                    chunks[strategy].append(
                        {
                            "id": str(uuid5(NAMESPACE_URL, key)),
                            "payload": {
                                "document_id": revision.document_id,
                                "revision_id": revision.revision_id,
                                "strategy": strategy,
                                "text": revision.text[start:end],
                                "title": revision.title,
                                "start": start,
                                "end": end,
                                "locations": locations,
                                "metadata": revision.metadata,
                            },
                        }
                    )
        return chunks

    async def prepare(self, revisions):
        await self.initialize()
        chunks = await asyncio.to_thread(self.chunks, revisions)
        counts = {}
        for strategy, points in chunks.items():
            counts[strategy] = len(points)
            for start in range(0, len(points), 64):
                batch = points[start : start + 64]
                vectors = await self.provider.embed([point["payload"]["text"] for point in batch])
                indexed = [
                    {
                        **point,
                        "vector": {
                            "dense": vector,
                            "bm25": {"text": point["payload"]["text"], "model": "qdrant/bm25"},
                        },
                    }
                    for point, vector in zip(batch, vectors, strict=True)
                ]
                result = await self.store.request(
                    "PUT",
                    self.collections[strategy],
                    "/points?wait=true",
                    body={"points": indexed},
                )
                if not isinstance(result, dict) or result.get("status") != "completed":
                    raise StoreUnavailable
        return counts
