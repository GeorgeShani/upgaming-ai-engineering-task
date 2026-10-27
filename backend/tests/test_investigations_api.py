import json

import pytest
from test_document_management import AUTH, upload
from test_indexed_documents import indexed_api as indexed_api


def ask(client, **changes):
    return client.post(
        "/api/investigations",
        json={
            "question": "What does the fictional source report?",
            **changes,
        },
    )


def test_question_to_hybrid_search_to_validated_cited_answer(indexed_api):
    client, storage, _ = indexed_api
    created = upload(client)
    result = ask(client, strategy="b")
    assert result.status_code == 200
    data = result.json()
    assert data["status"] == "answered" and "[E1]" in data["answer"]
    assert data["claims"][0]["citations"][0]["quote"] == "A fictional source fact."
    assert data["evidence"][0]["document_id"] == created.json()["document"]["document_id"]
    assert len(data["search_trace"]) == 1 and len(storage.queries) == 2
    assert data["configuration"]["strategy"] == "b"
    assert data["usage"]["generation"]["input_tokens"] == 200
    sent = storage.response_calls[0]
    assert sent["store"] is False and sent["max_output_tokens"] == 1200
    assert sent["text"]["format"]["strict"] is True
    assert len(json.loads(sent["input"])["evidence"]) == 1
    assert "tools" not in sent  # Slice 5 is deliberately one search, not the slice 6 loop.


@pytest.mark.parametrize("mode", ["provider_error", "bad_quote"])
def test_provider_and_evidence_errors_are_errors_not_abstentions(indexed_api, mode):
    client, storage, _ = indexed_api
    upload(client)
    storage.response_mode = mode
    result = ask(client)
    assert result.status_code == 502
    assert "private-provider-details" not in result.text and "answer" not in result.json()
    assert len(storage.response_calls) == 1  # No hidden retry/cost.


def test_no_active_evidence_abstains_without_generation(indexed_api):
    client, storage, _ = indexed_api
    created = upload(client)
    identifier = created.json()["document"]["document_id"]
    assert (
        client.delete(
            "/api/documents/" + identifier,
            headers={
                **AUTH,
                "If-Match": created.headers["etag"],
            },
        ).status_code
        == 204
    )
    result = ask(client).json()
    assert result["status"] == "insufficient_evidence" and result["evidence"] == []
    assert not storage.response_calls


def test_abstention_validation_and_global_demo_rate_limit(indexed_api):
    client, storage, _ = indexed_api
    upload(client)
    storage.response_mode = "abstain"
    for _ in range(6):
        result = ask(client)
        assert result.status_code == 200 and result.json()["status"] == "insufficient_evidence"
    limited = ask(client)
    assert limited.status_code == 429 and limited.headers["retry-after"] == "60"


def test_invalid_questions_do_not_reach_paid_provider(indexed_api):
    client, storage, _ = indexed_api
    for change in (
        {"question": "   "},
        {"question": "x" * 1001},
        {"strategy": "c"},
        {"unexpected": True},
    ):
        assert ask(client, **change).status_code == 422
    assert not storage.response_calls


def test_replacement_during_generation_invalidates_answer(indexed_api):
    client, storage, app = indexed_api
    created = upload(client)
    identifier = created.json()["document"]["document_id"]
    original_generate = app.state.provider.generate

    async def generate_then_delete(*args):
        value = await original_generate(*args)
        await app.state.document_service.delete(identifier, created.headers["etag"])
        return value

    app.state.provider.generate = generate_then_delete
    result = ask(client)
    assert result.status_code == 409 and "answer" not in result.json()
