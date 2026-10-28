import asyncio
import json
from types import SimpleNamespace

import pytest
from app.investigations.service import InvestigationService
from fastapi import HTTPException
from test_search_tools import Search, call


class Documents:
    async def filter_active_revisions(self, pairs):
        return pairs


class Provider:
    def __init__(self):
        self.settings = SimpleNamespace(
            embedding_model="fixture-embedding",
            embedding_dimensions=384,
            generation_model="fixture-generation",
        )
        self.planning, self.final_context = [], None

    async def plan_searches(self, instructions, inputs, tool, *, first_round):
        self.planning.append(inputs.copy())
        if first_round:
            output = [call()]
        else:
            prior = json.loads(inputs[-1]["output"])
            assert "America East Conference" in prior["evidence"][0]["text"]
            output = [
                call(
                    "two",
                    "America East Conference former name",
                    {
                        "evidence_id": prior["evidence"][0]["evidence_id"],
                        "entity": "America East Conference",
                    },
                )
            ]
        return output, {"input_tokens": 100, "output_tokens": 20, "estimated_cost_usd": 0.0001}

    async def generate(self, instructions, context, schema):
        self.final_context = json.loads(context)
        evidence = self.final_context["evidence"]
        by_text = {e["text"]: e["evidence_id"] for e in evidence}
        assert len(evidence) == 2
        claims = [
            {
                "text": text,
                "citations": [
                    {
                        "evidence_id": key,
                        "quote_id": next(
                            quote["quote_id"]
                            for quote in self.final_context["quote_choices"]
                            if quote["evidence_id"] == key and quote["quote"] == text
                        ),
                    }
                ],
            }
            for text, key in by_text.items()
        ]
        return {"status": "answered", "claims": claims, "conflicting_claims": []}, {
            "input_tokens": 200,
            "output_tokens": 40,
            "estimated_cost_usd": 0.001,
        }

    async def verify(self, instructions, context, schema):
        report = json.loads(context)
        return {
            "claims": [
                {
                    "claim_index": c["claim_index"],
                    "verdict": "supported",
                    "reason": "supported",
                    "comparison": None,
                }
                for c in report["claims"]
            ],
            "answers_question": True,
            "conflict_supported": True,
        }, {"input_tokens": 50, "output_tokens": 20, "estimated_cost_usd": 0.0002}


def test_second_search_is_derived_from_first_result_and_answer_cites_both_sources():
    search, provider = Search(), Provider()
    search.documents, search.index = Documents(), SimpleNamespace(profile="fixture")
    result = asyncio.run(
        InvestigationService(search, provider).bounded_investigate(
            "What was the former name of the conference Vermont soccer plays in?", "a"
        )
    )
    assert result["status"] == "answered"
    assert "North Atlantic Conference" in result["answer"]
    assert [t["round"] for t in result["search_trace"]] == [1, 2]
    assert result["execution"]["searches"] == 2 and result["execution"]["llm_calls"] == 4
    assert {c["evidence_id"] for claim in result["claims"] for c in claim["citations"]} == {
        "E1",
        "E2",
    }
    assert result["usage"]["estimated_model_cost_usd"] == pytest.approx(0.0014)
    assert len(provider.planning) == 2


def test_final_context_preserves_conflicting_sources_and_requires_two_documents():
    search, provider = Search(), Provider()
    search.documents, search.index = Documents(), SimpleNamespace(profile="fixture")
    original_search = search.search

    async def reports(query, strategy):
        trace = await original_search(query, strategy)
        first = trace["evidence"][0]
        trace["evidence"] = [
            {
                **first,
                "document_id": f"doc-{value}",
                "chunk_id": f"chunk-{value}",
                "title": "Fictional retry report",
                "text": f"At 12:00 UTC, payment-router had a retry limit of {value} attempts.",
            }
            for value in (3, 5)
        ]
        return trace

    async def plan(*args, first_round):
        output = (
            [call(query="payment-router retry limit")]
            if first_round
            else [call("two", query="payment-router retry limit corroboration")]
        )
        return output, {"input_tokens": 10, "output_tokens": 10, "estimated_cost_usd": 0.0001}

    search.search, provider.plan_searches = reports, plan
    original = provider.generate

    async def conflicting(*args):
        draft, usage = await original(*args)
        draft["status"] = "conflicting_evidence"
        draft["conflicting_claims"], draft["claims"] = draft["claims"], []
        return draft, usage

    provider.generate = conflicting
    result = asyncio.run(
        InvestigationService(search, provider).investigate("Fixture conflict?", "a")
    )
    assert result["status"] == "conflicting_evidence"
    assert len(result["conflicting_claims"]) == 2 and "[E1]" in result["answer"]
    assert "3 attempts" in result["answer"] and "5 attempts" in result["answer"]
    # This checks preservation/status contracts, not semantic contradiction detection.


def test_timeout_is_explicit_and_does_not_claim_missing_evidence(monkeypatch):
    from app.investigations import service as module

    monkeypatch.setattr(module, "WORKFLOW_TIMEOUT_SECONDS", 0.01)
    engine = InvestigationService(None, None)

    async def hang(*args):
        await asyncio.Event().wait()

    engine.investigate = hang
    with pytest.raises(HTTPException) as error:
        asyncio.run(engine.bounded_investigate("question", "a"))
    assert error.value.status_code == 504


def test_literal_quote_does_not_allow_an_unsupported_claim_to_reach_the_user():
    search, provider = Search(), Provider()
    search.documents, search.index = Documents(), SimpleNamespace(profile="fixture")
    original = provider.generate

    async def unsupported(*args):
        draft, usage = await original(*args)
        draft["claims"][0]["text"] = "America East Conference was founded in 1801."
        return draft, usage

    async def verify(*args):
        return {
            "claims": [
                {
                    "claim_index": i,
                    "verdict": "unsupported" if i == 0 else "supported",
                    "reason": "unsupported_value" if i == 0 else "supported",
                    "comparison": None,
                }
                for i in range(2)
            ],
            "answers_question": False,
            "conflict_supported": False,
        }, {"input_tokens": 50, "output_tokens": 20, "estimated_cost_usd": 0.0002}

    provider.generate, provider.verify = unsupported, verify
    result = asyncio.run(InvestigationService(search, provider).investigate("Question?", "a"))
    assert result["status"] == "insufficient_evidence"
    assert result["claims"] == []
    assert "1801" not in result["answer"]
    assert result["verification"]["outcome"] == "withheld"
