import asyncio

from .fusion import fuse


class SearchService:
    def __init__(self, index, documents):
        self.index, self.documents = index, documents

    async def search(self, query, strategy):
        vector = (await self.index.provider.embed([query]))[0]

        async def candidates(using, value):
            result = await self.index.store.request(
                "POST",
                self.index.collections[strategy],
                "/points/query",
                body={
                    "query": value,
                    "using": using,
                    "limit": 30,
                    "with_payload": True,
                    "with_vector": False,
                },
            )
            return sorted(result["points"], key=lambda hit: (-hit["score"], str(hit["id"])))

        dense, sparse = await asyncio.gather(
            candidates("dense", vector),
            candidates("bm25", {"text": query, "model": "qdrant/bm25"}),
        )
        pairs = [(h["payload"]["document_id"], h["payload"]["revision_id"]) for h in dense + sparse]
        eligible = set(await self.documents.filter_active_revisions(pairs))
        # Filter BEFORE fusion/diversity selection. Never expose staged/deleted text.
        rankings = [
            [
                h
                for h in rows
                if (h["payload"]["document_id"], h["payload"]["revision_id"]) in eligible
            ]
            for rows in (dense, sparse)
        ]
        evidence = fuse(rankings)
        return {
            "query": query,
            "strategy": strategy,
            "profile": self.index.profile,
            "candidate_counts": {
                "dense": len(dense),
                "bm25": len(sparse),
                "active_dense": len(rankings[0]),
                "active_bm25": len(rankings[1]),
            },
            "evidence": [
                {
                    "evidence_id": f"E{i}",
                    "chunk_id": str(hit["id"]),
                    **hit["payload"],
                    "fusion_score": hit["fusion_score"],
                }
                for i, hit in enumerate(evidence, 1)
            ],
        }
