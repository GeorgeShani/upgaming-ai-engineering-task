import asyncio

import pytest
from app.investigations.tools import SearchTools, ToolProtocolError
from test_search_tools import Search, call


def test_source_verified_entity_is_added_when_the_model_omits_it_from_query():
    search = Search()
    tools = SearchTools(search, "a")

    async def run():
        await tools.run_round([call()], 1)
        await tools.run_round(
            [
                call(
                    "two",
                    "former name",
                    {
                        "evidence_id": "E1",
                        "entity": "America East Conference",
                    },
                )
            ],
            2,
        )
        assert search.queries == ["Vermont soccer", "America East Conference former name"]
        assert tools.traces[1]["query_adjusted"] is True
        assert tools.traces[1]["requested_query"] == "former name"
        assert tools.tool_calls == 2

    asyncio.run(run())


def test_adding_a_grounded_entity_cannot_exceed_query_length_limit():
    search = Search()
    tools = SearchTools(search, "a")

    async def run():
        await tools.run_round([call()], 1)
        with pytest.raises(ToolProtocolError):
            await tools.run_round(
                [
                    call(
                        "two",
                        "x" * 500,
                        {
                            "evidence_id": "E1",
                            "entity": "America East Conference",
                        },
                    )
                ],
                2,
            )
        assert len(search.queries) == 1

    asyncio.run(run())
