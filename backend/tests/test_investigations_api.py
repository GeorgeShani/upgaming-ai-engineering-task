import json

import pytest
from app.documents.store import StoreUnavailable
from test_document_management import AUTH, upload
from test_indexed_documents import indexed_api as indexed_api
from test_search_tools import call


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
    assert len(data["search_trace"]) == 2 and len(storage.queries) == 4
    assert data["configuration"]["strategy"] == "b"
    assert data["usage"]["generation"]["input_tokens"] == 200
    assert data["workflow"] == "bounded_tools_v1"
    assert data["execution"]["searches"] == 2 and data["execution"]["llm_calls"] == 3
    assert len(data["usage"]["planning"]) == 2
    planner = storage.response_calls[0]
    assert planner["tools"][0]["name"] == "search_documents"
    assert planner["tool_choice"] == "required"
    replay = storage.response_calls[1]["input"]
    assert replay[-1]["type"] == "function_call_output"
    assert replay[-1]["call_id"] == "initial"
    sent = storage.response_calls[-1]
    assert sent["store"] is False and sent["max_output_tokens"] == 1200
    assert sent["text"]["format"]["strict"] is True
    assert len(json.loads(sent["input"])["evidence"]) == 1
    assert "tools" not in sent  # Final synthesis cannot start another retrieval round.


@pytest.mark.parametrize("mode", ["provider_error", "bad_quote"])
def test_provider_and_evidence_errors_are_errors_not_abstentions(indexed_api, mode):
    client, storage, _ = indexed_api
    upload(client)
    storage.response_mode = mode
    result = ask(client)
    assert result.status_code == 502
    assert "private-provider-details" not in result.text and "answer" not in result.json()
    assert len(storage.response_calls) == (1 if mode == "provider_error" else 3)


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
    assert len(storage.response_calls) == 1
    assert all("tools" in call for call in storage.response_calls)


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


def test_over_budget_tool_batch_does_not_execute_any_search_in_second_round(indexed_api):
    client, storage, _ = indexed_api
    upload(client)
    storage.plan_batches = [[call()], [call("two"), call("three"), call("four")]]
    response = ask(client)
    assert response.status_code == 502 and "answer" not in response.json()
    assert len(storage.queries) == 2 and len(storage.response_calls) == 2


def test_second_planner_failure_is_not_an_abstention(indexed_api):
    client, storage, _ = indexed_api
    upload(client)
    storage.response_mode = "second_provider_error"
    response = ask(client)
    assert response.status_code == 502 and "private-provider-details" not in response.text
    assert len(storage.response_calls) == 2


def test_storage_failure_stops_workflow_without_generation(indexed_api):
    client, storage, app = indexed_api

    async def fail(*args):
        raise StoreUnavailable

    app.state.search_service.search = fail
    response = ask(client)
    assert response.status_code == 503 and "answer" not in response.json()
    assert len(storage.response_calls) == 1


def test_local_budget_blocks_planning_before_network(indexed_api):
    client, storage, app = indexed_api
    app.state.provider.ledger.ceiling = 0
    assert ask(client).status_code == 503
    assert not storage.response_calls and not storage.queries


def test_busy_investigation_rejects_instead_of_queueing_paid_work(indexed_api):
    client, storage, app = indexed_api
    slots = app.state.investigation_slots
    client.portal.call(slots.acquire)
    try:
        assert ask(client).status_code == 429
        assert not storage.response_calls
    finally:
        client.portal.call(slots.release)
