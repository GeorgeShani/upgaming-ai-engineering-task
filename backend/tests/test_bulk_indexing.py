from pathlib import Path

import pytest
from app.documents.store import StoreUnavailable
from app.retrieval.bulk import import_batch, read_corpus
from test_document_management import AUTH, replace
from test_indexed_documents import indexed_api as indexed_api


def test_bulk_resume_preserves_edits_tombstones_and_source_sentence_ids(indexed_api):
    client, storage, app = indexed_api
    index = app.state.search_service.index
    client.portal.call(index.store.initialize)
    documents = list(read_corpus(Path("fixtures/source-documents.jsonl"), 3))
    first = client.portal.call(import_batch, documents, index)
    assert first["activated"] == 3
    repeated = client.portal.call(import_batch, documents, index)
    assert repeated["activated"] == 0 and repeated["skipped"] == 3
    identifier = documents[0].document_id
    original = client.get("/api/documents/" + identifier)
    assert original.json()["format"] == "dataset"
    assert original.json()["locations"][0]["kind"] == "sentence"
    changed = replace(client, identifier, original.headers["etag"], b"User edited the source.")
    assert changed.status_code == 200
    deleted_id = documents[1].document_id
    deleted = client.get("/api/documents/" + deleted_id)
    assert (
        client.delete(
            "/api/documents/" + deleted_id,
            headers={
                **AUTH,
                "If-Match": deleted.headers["etag"],
            },
        ).status_code
        == 204
    )
    resumed = client.portal.call(import_batch, documents, index)
    assert resumed["activated"] == 0
    assert client.get("/api/documents/" + identifier).json()["text"] == "User edited the source."
    assert client.get("/api/documents/" + deleted_id).status_code == 404


def test_interrupted_bulk_activation_reuses_cached_embeddings_on_resume(indexed_api):
    client, storage, app = indexed_api
    index = app.state.search_service.index
    client.portal.call(index.store.initialize)
    documents = list(read_corpus(Path("fixtures/source-documents.jsonl"), 2))
    storage.fail_next = "manifest"
    with pytest.raises(StoreUnavailable):
        client.portal.call(import_batch, documents, index)
    assert client.get("/api/documents").json()["items"] == []
    before = index.provider.ledger.summary()["calls"]
    assert client.portal.call(import_batch, documents, index)["activated"] == 2
    assert index.provider.ledger.summary()["calls"] == before
