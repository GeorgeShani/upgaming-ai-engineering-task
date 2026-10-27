import json

import httpx
import pytest
from app.main import create_app
from fake_qdrant import FakeQdrant
from fastapi.testclient import TestClient
from test_document_management import AUTH, replace, settings, upload


@pytest.fixture
def indexed_api(tmp_path):
    storage = FakeQdrant()
    storage.response_mode = "valid"
    storage.response_calls = []

    def transport(request):
        if request.url.host == "api.openai.com":
            body = json.loads(request.content)
            if request.url.path.endswith("/responses"):
                storage.response_calls.append(body)
                if storage.response_mode == "provider_error":
                    return httpx.Response(500, text="private-provider-details")
                context = json.loads(body["input"])
                first = context["evidence"][0]
                claim = {
                    "text": "A fictional source fact.",
                    "citations": [
                        {
                            "evidence_id": first["evidence_id"],
                            "quote": first["text"],
                        }
                    ],
                }
                if storage.response_mode == "bad_quote":
                    claim["citations"][0]["quote"] = "An entirely invented quote."
                draft = {"status": "answered", "claims": [claim], "conflicting_claims": []}
                if storage.response_mode == "abstain":
                    draft = {
                        "status": "insufficient_evidence",
                        "claims": [],
                        "conflicting_claims": [],
                    }
                return httpx.Response(
                    200,
                    json={
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": json.dumps(draft)}],
                            }
                        ],
                        "usage": {"input_tokens": 200, "output_tokens": 40},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": i, "embedding": [0.01] * 384} for i, _ in enumerate(body["input"])
                    ],
                    "usage": {"prompt_tokens": 10},
                },
            )
        return storage(request)

    config = settings(openai_api_key="fixture-openai", usage_db=tmp_path / "usage.db")
    app = create_app(config, transport=httpx.MockTransport(transport))
    with TestClient(app) as client:
        yield client, storage, app


def search(api, strategy="a"):
    client, _, app = api
    return client.portal.call(app.state.search_service.search, "fictional fact", strategy)


def test_indexes_both_strategies_and_filters_superseded_deleted_and_staged(indexed_api):
    client, storage, app = indexed_api
    first = upload(client)
    assert first.status_code == 201 and first.json()["document"]["index_status"] == "ready"
    document_id = first.json()["document"]["document_id"]
    for strategy in ("a", "b"):
        trace = search(indexed_api, strategy)
        assert len(trace["evidence"]) == 1
        evidence = trace["evidence"][0]
        assert evidence["text"] == "A fictional source fact."
        assert evidence["locations"][0]["kind"] == "paragraph"
        assert evidence["document_id"] == document_id
        collection = app.state.search_service.index.collections[strategy]
        vector = next(iter(storage.vectors[collection].values()))
        assert len(vector["dense"]) == 384 and vector["bm25"]["model"] == "qdrant/bm25"
    updated = replace(client, document_id, first.headers["etag"], b"A changed source fact.")
    assert updated.status_code == 200
    assert [e["text"] for e in search(indexed_api)["evidence"]] == ["A changed source fact."]
    storage.fail_next = "manifest"
    failed = replace(client, document_id, updated.headers["etag"], b"Invisible staged source.")
    assert failed.status_code == 503
    assert [e["text"] for e in search(indexed_api)["evidence"]] == ["A changed source fact."]
    assert (
        client.delete(
            f"/api/documents/{document_id}",
            headers={
                **AUTH,
                "If-Match": updated.headers["etag"],
            },
        ).status_code
        == 204
    )
    assert search(indexed_api)["evidence"] == []
    assert len(storage.queries) == 10


def test_failed_chunk_preparation_never_activates_replacement(indexed_api):
    client, storage, _ = indexed_api
    first = upload(client)
    document_id = first.json()["document"]["document_id"]
    storage.fail_next = "chunk"
    result = replace(client, document_id, first.headers["etag"], b"Failed chunk preparation.")
    assert result.status_code == 503
    assert client.get(f"/api/documents/{document_id}").headers["etag"] == first.headers["etag"]
    assert search(indexed_api)["evidence"][0]["text"] == "A fictional source fact."


def test_reupload_repairs_pending_index_without_changing_content_revision(indexed_api):
    client, storage, app = indexed_api
    first = upload(client)
    identifier = first.json()["document"]["document_id"]
    manifest = storage.collections[app.state.document_service.store.documents][identifier]
    manifest["index_profile"] = "old-profile"
    assert client.get("/api/documents/" + identifier).json()["index_status"] == "pending"
    repeated = upload(client)
    assert repeated.status_code == 200 and repeated.json()["duplicate"]
    assert repeated.json()["document"]["index_status"] == "ready"
    assert repeated.headers["etag"] == first.headers["etag"]
