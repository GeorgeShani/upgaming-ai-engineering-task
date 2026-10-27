"""Shared HTTP fakes for backend integration and browser smoke tests; no provider network."""

import json

import httpx
from fake_qdrant import FakeQdrant


def fake_services():
    storage = FakeQdrant()
    storage.response_mode = "valid"
    storage.response_calls = []

    def transport(request):
        if request.method == "GET" and (
            request.url.host == "api.openai.com" or request.url.path == "/collections"
        ):
            return httpx.Response(200, json={"result": {"collections": []}})
        if request.url.host == "api.openai.com":
            body = json.loads(request.content)
            if request.url.path.endswith("/responses"):
                storage.response_calls.append(body)
                if storage.response_mode == "provider_error":
                    return httpx.Response(500, text="private-provider-details")
                if (
                    storage.response_mode == "second_provider_error"
                    and "tools" in body
                    and len(body["input"]) > 1
                ):
                    return httpx.Response(500, text="private-provider-details")
                if "tools" in body:
                    if hasattr(storage, "plan_batches") and storage.plan_batches:
                        output = storage.plan_batches.pop(0)
                    elif len(body["input"]) == 1:
                        question = json.loads(body["input"][0]["content"])["question"]
                        output = [
                            {
                                "type": "function_call",
                                "call_id": "initial",
                                "name": "search_documents",
                                "arguments": json.dumps(
                                    {
                                        "query": question,
                                        "follow_up": None,
                                    }
                                ),
                            }
                        ]
                    else:
                        question = json.loads(body["input"][0]["content"])["question"]
                        output = [
                            {
                                "type": "function_call",
                                "call_id": "verification",
                                "name": "search_documents",
                                "arguments": json.dumps(
                                    {
                                        "query": question + " corroborating report",
                                        "follow_up": None,
                                    }
                                ),
                            }
                        ]
                    return httpx.Response(
                        200,
                        json={
                            "status": "completed",
                            "output": output,
                            "usage": {"input_tokens": 100, "output_tokens": 20},
                        },
                    )
                context = json.loads(body["input"])
                first = context["evidence"][0]
                claim = {
                    "text": first["text"][:400],
                    "citations": [
                        {
                            "evidence_id": first["evidence_id"],
                            "quote_id": next(
                                quote["quote_id"]
                                for quote in context["quote_choices"]
                                if quote["evidence_id"] == first["evidence_id"]
                            ),
                        }
                    ],
                }
                if storage.response_mode == "bad_quote":
                    claim["citations"][0]["quote_id"] = "Q999"
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

    return storage, httpx.MockTransport(transport)
