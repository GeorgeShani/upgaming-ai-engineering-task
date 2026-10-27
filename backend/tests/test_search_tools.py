import asyncio
import json

import pytest
from app.investigations.tools import SearchTools, ToolProtocolError


def call(identifier="one", query="Vermont soccer", follow_up=None, **changes):
    return {
        "type": "function_call",
        "call_id": identifier,
        "name": "search_documents",
        "arguments": json.dumps({"query": query, "follow_up": follow_up}),
        **changes,
    }


class Search:
    def __init__(self):
        self.queries = []

    async def search(self, query, strategy):
        self.queries.append(query)
        bridge = "America East Conference" in query
        return {
            "query": query,
            "strategy": strategy,
            "profile": "fixture",
            "candidate_counts": {"dense": 1, "bm25": 1},
            "evidence": [
                {
                    "evidence_id": "E1",
                    "chunk_id": "conference" if bridge else "soccer",
                    "document_id": "doc-two" if bridge else "doc-one",
                    "revision_id": "r1",
                    "title": "Conference" if bridge else "Vermont soccer",
                    "text": (
                        "America East Conference was known as the North Atlantic Conference."
                        if bridge
                        else "Vermont soccer competes in the America East Conference."
                    ),
                    "fusion_score": 0.03,
                    "start": 0,
                    "end": 70,
                    "locations": [],
                    "metadata": {},
                }
            ],
        }


def test_entity_follow_up_replays_actual_tool_result_and_keeps_ids_stable():
    search = Search()
    runner = SearchTools(search, "a")

    async def run():
        first = await runner.run_round([call()], 1)
        assert first[0]["call_id"] == "one" and first[0]["type"] == "function_call_output"
        assert json.loads(first[0]["output"])["evidence"][0]["evidence_id"] == "E1"
        await runner.run_round(
            [
                call(
                    "two",
                    "America East Conference former name",
                    {"evidence_id": "E1", "entity": "America East Conference"},
                )
            ],
            2,
        )
        final = runner.selected_evidence()
        assert {e["evidence_id"] for e in final} == {"E1", "E2"}
        assert {e["document_id"] for e in final} == {"doc-one", "doc-two"}
        assert runner.traces[1]["follow_up"]["evidence_id"] == "E1"
        with pytest.raises(ToolProtocolError):
            await runner.run_round([call("three")], 3)

    asyncio.run(run())
    assert len(search.queries) == 2


@pytest.mark.parametrize(
    "mode",
    [
        "too_many",
        "bad_name",
        "bad_json",
        "extra_argument",
        "blank",
        "long",
        "fake_anchor",
        "ungrounded_entity",
        "query_omits_entity",
        "reused_id",
        "missing_first_call",
    ],
)
def test_invalid_requests_are_rejected_before_any_search_in_that_round(mode):
    search = Search()
    runner = SearchTools(search, "a")

    async def run():
        if mode == "missing_first_call":
            with pytest.raises(ToolProtocolError):
                await runner.run_round([], 1)
            assert not search.queries
            return
        await runner.run_round([call()], 1)
        request = call("two", "America East Conference history")
        if mode == "bad_name":
            request["name"] = "delete_documents"
        elif mode == "bad_json":
            request["arguments"] = "{broken"
        elif mode == "extra_argument":
            request["arguments"] = '{"query":"soccer","follow_up":null,"collection":"private"}'
        elif mode == "blank":
            request = call("two", "   ")
        elif mode == "long":
            request = call("two", "x" * 501)
        elif mode in ("fake_anchor", "ungrounded_entity", "query_omits_entity"):
            request = call(
                "two",
                "America East Conference history",
                {
                    "evidence_id": "E999" if mode == "fake_anchor" else "E1",
                    "entity": "Unseen Corporation"
                    if mode == "ungrounded_entity"
                    else "Vermont soccer",
                },
            )
        elif mode == "reused_id":
            request["call_id"] = "one"
        requests = (
            [request]
            if mode != "too_many"
            else [
                call("two"),
                call("three"),
                call("four"),
            ]
        )
        with pytest.raises(ToolProtocolError):
            await runner.run_round(requests, 2)
        assert len(search.queries) == 1

    asyncio.run(run())


def test_three_call_budget_and_duplicate_queries_do_not_repeat_search():
    search = Search()
    runner = SearchTools(search, "a")

    async def run():
        await runner.run_round([call()], 1)
        await runner.run_round([call("two"), call("three", "America East Conference")], 2)
        assert runner.tool_calls == 3
        assert len(search.queries) == 2 and runner.traces[1]["executed"] is False
        assert len({e["evidence_id"] for e in runner.selected_evidence()}) == 2

    asyncio.run(run())
