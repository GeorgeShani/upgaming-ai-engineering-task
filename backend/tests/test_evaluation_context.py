import asyncio
from types import SimpleNamespace

import pytest
from app.evaluation.context import cloud_snapshot


@pytest.mark.parametrize(
    "changed", [None, "content_sha256", "index_profile", "index_status", "missing"]
)
def test_cloud_identity_requires_the_same_ready_corpus_before_any_paid_calls(changed):
    class Store:
        documents = "documents"

        async def request(self, method, collection, suffix, **kwargs):
            if suffix == "/points/count":
                return {"count": 1}
            payload = {
                "document_id": "one",
                "content_sha256": "sha",
                "revision_id": "r",
                "index_profile": "profile",
                "index_status": "ready",
            }
            if changed and changed != "missing":
                payload[changed] = "changed"
            return {"points": [] if changed == "missing" else [{"payload": payload}]}

    index = SimpleNamespace(profile="profile", collections={"a": "a", "b": "b"})
    work = cloud_snapshot(Store(), index, {"one": {"content_sha256": "sha"}})
    if changed:
        with pytest.raises(ValueError, match="Cloud"):
            asyncio.run(work)
    else:
        assert asyncio.run(work)["active_source_count"] == 1
