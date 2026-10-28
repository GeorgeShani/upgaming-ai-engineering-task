import asyncio
from types import SimpleNamespace

from app.retrieval.search import SearchService


def test_diagnostic_ranking_reaches_ten_documents_without_expanding_answer_context():
    class Provider:
        async def embed(self, texts, **options):
            return [[0.0]], {"api_calls": 0}

    class Store:
        async def request(self, *args, **kwargs):
            return {
                "points": [
                    {
                        "id": f"chunk-{i:02}",
                        "score": 20 - i,
                        "payload": {"document_id": f"doc-{i:02}", "revision_id": "r"},
                    }
                    for i in range(12)
                ]
            }

    class Documents:
        async def filter_active_revisions(self, pairs):
            return [pair for pair in pairs if pair[0] != "doc-00"]

    index = SimpleNamespace(
        provider=Provider(), store=Store(), collections={"a": "chunks"}, profile="test"
    )
    trace = asyncio.run(SearchService(index, Documents()).search("query", "a"))
    assert len(trace["evidence"]) == 8
    assert trace["document_ranking"] == [f"doc-{i:02}" for i in range(1, 11)]
    assert trace["document_ranking"][:8] == [e["document_id"] for e in trace["evidence"]]
