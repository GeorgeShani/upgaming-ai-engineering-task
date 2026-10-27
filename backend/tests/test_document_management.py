import httpx
import pytest
from app.config import Settings
from app.documents.security import MAX_REQUEST_BYTES
from app.main import create_app
from fake_qdrant import FakeQdrant
from fastapi.testclient import TestClient
from test_document_parsing import docx_bytes, pdf_bytes

AUTH = {"Authorization": "Bearer fixture-admin-token"}


def settings(**overrides):
    values = {
        "qdrant_url": "https://storage.example",
        "qdrant_api_key": "fixture-storage-key",
        "demo_admin_token": "fixture-admin-token",
        "openai_api_key": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def api():
    storage = FakeQdrant()
    app = create_app(settings(), transport=httpx.MockTransport(storage))
    with TestClient(app) as client:
        yield client, storage, app


def upload(client, content=b"A fictional source fact.", filename="incident.txt"):
    return client.post("/api/documents", headers=AUTH, files={"file": (filename, content)})


def replace(client, document_id, etag, content):
    return client.put(
        f"/api/documents/{document_id}",
        headers={**AUTH, "If-Match": etag},
        files={"file": ("updated.txt", content)},
    )


def active(api, candidates):
    client, _, app = api
    return client.portal.call(app.state.document_service.filter_active_revisions, candidates)


def test_upload_list_inspect_replace_delete_and_revision_gate(api):
    client, _, _ = api
    created = upload(client)
    assert created.status_code == 201
    original = created.json()["document"]
    identifier = original["document_id"]
    assert original["index_status"] == "pending"
    read = client.get(f"/api/documents/{identifier}")
    assert read.json()["text"] == "A fictional source fact."
    assert read.json()["locations"][0]["number"] == 1
    assert read.headers["etag"] == created.headers["etag"]
    assert len(client.get("/api/documents").json()["items"]) == 1
    updated = replace(client, identifier, read.headers["etag"], b"Changed fictional fact.")
    assert updated.status_code == 200
    current = updated.json()["document"]
    assert current["document_id"] == identifier
    assert current["revision_id"] != original["revision_id"]
    pairs = [(identifier, original["revision_id"]), (identifier, current["revision_id"])]
    assert active(api, pairs) == [pairs[1]]
    removed = client.delete(
        f"/api/documents/{identifier}", headers={**AUTH, "If-Match": updated.headers["etag"]}
    )
    assert removed.status_code == 204 and not removed.content
    assert client.get(f"/api/documents/{identifier}").status_code == 404
    assert client.get("/api/documents").json()["items"] == []
    assert active(api, pairs) == []


def test_cross_format_duplicates_return_the_existing_document(api):
    client, _, _ = api
    first = upload(client, pdf_bytes(), "incident.pdf")
    second = upload(client, docx_bytes(), "same.docx")
    assert first.status_code == 201 and second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["document"]["document_id"] == second.json()["document"]["document_id"]


def test_replacing_with_another_documents_content_is_a_conflict(api):
    client, _, _ = api
    first = upload(client)
    second = upload(client, b"Another fact.")
    identifier = second.json()["document"]["document_id"]
    result = replace(client, identifier, second.headers["etag"], b"A fictional source fact.")
    assert result.status_code == 409
    assert result.json()["detail"]["document_id"] == first.json()["document"]["document_id"]
    assert client.get(f"/api/documents/{identifier}").json()["text"] == "Another fact."


@pytest.mark.parametrize("phase", ["revision", "manifest"])
def test_failed_replacement_keeps_previous_revision_usable(api, phase):
    client, storage, _ = api
    original = upload(client)
    identifier = original.json()["document"]["document_id"]
    storage.fail_next = phase
    result = replace(client, identifier, original.headers["etag"], b"Uncommitted content.")
    assert result.status_code == 503 and "private-provider-details" not in result.text
    read = client.get(f"/api/documents/{identifier}")
    assert read.headers["etag"] == original.headers["etag"]
    assert read.json()["text"] == "A fictional source fact."
    manifest = storage.collections["investigation_documents_v1"][identifier]
    revisions = storage.collections["investigation_revisions_v1"]
    pairs = [(identifier, key) for key in revisions]
    assert active(api, pairs) == [(identifier, manifest["revision_id"])]


def test_ambiguous_write_timeout_never_leaves_a_dangling_active_pointer(api):
    client, storage, _ = api
    original = upload(client)
    identifier = original.json()["document"]["document_id"]
    storage.fail_next = "after_manifest"
    result = replace(client, identifier, original.headers["etag"], b"Complete new content.")
    assert result.status_code == 503
    assert client.get(f"/api/documents/{identifier}").json()["text"] == "Complete new content."


def test_invalid_replacement_and_stale_versions_do_not_modify_document(api):
    client, _, _ = api
    original = upload(client)
    identifier = original.json()["document"]["document_id"]
    invalid = replace(client, identifier, original.headers["etag"], b"\x00binary")
    assert invalid.status_code == 422
    assert client.delete(f"/api/documents/{identifier}", headers=AUTH).status_code == 428
    assert replace(client, identifier, '"stale"', b"Fact.").status_code == 412
    updated = replace(client, identifier, original.headers["etag"], b"New content.")
    assert updated.status_code == 200
    assert (
        client.delete(
            f"/api/documents/{identifier}", headers={**AUTH, "If-Match": original.headers["etag"]}
        ).status_code
        == 412
    )


def test_state_survives_new_application_instance(api):
    client, storage, _ = api
    original = upload(client)
    identifier = original.json()["document"]["document_id"]
    with TestClient(create_app(settings(), transport=httpx.MockTransport(storage))) as restarted:
        assert (
            restarted.get(f"/api/documents/{identifier}").json()["text"]
            == "A fictional source fact."
        )
        assert len(restarted.get("/api/documents").json()["items"]) == 1


def test_list_cursor_pages_do_not_repeat_and_limits_are_validated(api):
    client, _, _ = api
    ids = {
        upload(client, text).json()["document"]["document_id"]
        for text in (b"First.", b"Second.", b"Third.")
    }
    seen, cursor = [], None
    for _ in range(3):
        page = client.get(
            "/api/documents", params={"limit": 1, **({"cursor": cursor} if cursor else {})}
        ).json()
        seen.extend(item["document_id"] for item in page["items"])
        cursor = page["next_cursor"]
    assert len(seen) == 3 and set(seen) == ids and cursor is None
    assert client.get("/api/documents?limit=101").status_code == 422
    assert client.get("/api/documents/not-a-uuid").status_code == 422


def test_unauthorized_invalid_multipart_is_rejected_before_parsing(api):
    client, storage, _ = api
    result = client.post(
        "/api/documents",
        content=b"not-multipart",
        headers={"Content-Type": "multipart/form-data; boundary=missing"},
    )
    assert result.status_code == 401
    assert storage.collections == {}


def test_unconfigured_admin_disables_mutations_and_missing_storage_is_explicit():
    with TestClient(create_app(settings(demo_admin_token="", qdrant_url=None))) as client:
        assert upload(client).status_code == 503
        assert client.get("/api/documents").status_code == 503


def test_streamed_request_size_is_bounded_even_without_content_length(api):
    client, _, _ = api
    response = client.post(
        "/api/documents", headers=AUTH, content=iter([b"x" * MAX_REQUEST_BYTES, b"x"])
    )
    assert response.status_code == 413


def test_file_size_has_its_own_limit_inside_multipart(api):
    client, _, _ = api
    assert upload(client, b"x" * 5_000_001).status_code == 413


def test_failed_first_upload_does_not_publish_an_orphan_revision(api):
    client, storage, _ = api
    storage.fail_next = "manifest"
    assert upload(client).status_code == 503
    assert client.get("/api/documents").json()["items"] == []
    revisions = storage.collections["investigation_revisions_v1"]
    pairs = [(revision["document_id"], key) for key, revision in revisions.items()]
    assert pairs and active(api, pairs) == []
    assert upload(client).status_code == 201


def test_two_edits_using_the_same_etag_cannot_both_commit(api):
    import asyncio

    from app.documents.parsing import parse_upload

    client, _, app = api
    original = upload(client)
    identifier = original.json()["document"]["document_id"]

    async def competing_writes():
        manager = app.state.document_service
        return await asyncio.gather(
            *(
                manager.save(
                    parse_upload("update.txt", content), identifier, original.headers["etag"]
                )
                for content in (b"First competing update.", b"Second competing update.")
            ),
            return_exceptions=True,
        )

    results = client.portal.call(competing_writes)
    assert sum(not isinstance(result, Exception) for result in results) == 1
    failure = next(result for result in results if isinstance(result, Exception))
    assert failure.status_code == 412


def test_wrong_admin_token_and_disallowed_mime_do_not_write(api):
    client, storage, _ = api
    denied = client.post(
        "/api/documents",
        headers={"Authorization": "Bearer wrong"},
        files={"file": ("incident.txt", b"Fact.")},
    )
    assert denied.status_code == 401 and storage.collections == {}
    wrong_type = client.post(
        "/api/documents", headers=AUTH, files={"file": ("incident.txt", b"Fact.", "text/html")}
    )
    assert wrong_type.status_code == 415 and storage.collections == {}
    accepted = client.post(
        "/api/documents",
        headers=AUTH,
        files={"file": ("incident.txt", b"Fact.", "Text/Plain; charset=utf-8")},
    )
    assert accepted.status_code == 201


def test_incomplete_manifest_is_not_treated_as_active(api):
    client, storage, _ = api
    original = upload(client).json()["document"]
    identifier = original["document_id"]
    storage.collections["investigation_documents_v1"][identifier].pop("deleted")
    assert client.get(f"/api/documents/{identifier}").status_code == 404
    assert active(api, [(identifier, original["revision_id"])]) == []
