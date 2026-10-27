import asyncio
import json

import httpx
import pytest
from app.config import Settings
from app.providers import OpenAIProvider, ProviderError


def test_planner_uses_real_function_tool_contract_and_records_usage(tmp_path):
    requests = []
    call = {
        "type": "function_call",
        "call_id": "call_one",
        "name": "search_documents",
        "arguments": '{"query":"Vermont soccer","follow_up":null}',
    }

    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [call],
                "usage": {"input_tokens": 100, "output_tokens": 30},
            },
        )

    async def run():
        config = Settings(_env_file=None, openai_api_key="fixture", usage_db=tmp_path / "cost.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            provider = OpenAIProvider(client, config)
            output, usage = await provider.plan_searches(
                "Find evidence",
                [{"role": "user", "content": "Which conference does Vermont play in?"}],
                {
                    "type": "function",
                    "name": "search_documents",
                    "parameters": {"type": "object"},
                    "strict": True,
                },
                first_round=True,
            )
            assert output == [call] and usage["input_tokens"] == 100
            assert provider.ledger.summary()["calls"] == 1

    asyncio.run(run())
    body = requests[0]
    assert body["tools"][0]["name"] == "search_documents"
    assert body["tool_choice"] == "required" and body["parallel_tool_calls"] is False
    assert body["store"] is False and body["max_output_tokens"] == 600
    assert "text" not in body


@pytest.mark.parametrize("mode", ["refusal", "incomplete", "missing_usage", "negative_usage"])
def test_invalid_planning_responses_fail_without_silent_retry(tmp_path, mode):
    calls = []

    def transport(request):
        calls.append(request)
        data = {
            "status": "completed",
            "output": [],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        if mode == "refusal":
            data["output"] = [
                {
                    "type": "message",
                    "content": [
                        {"type": "refusal", "refusal": "cannot comply"},
                    ],
                }
            ]
        elif mode == "incomplete":
            data["status"] = "incomplete"
        elif mode == "missing_usage":
            data.pop("usage")
        else:
            data["usage"]["input_tokens"] = -1
        return httpx.Response(200, json=data)

    async def run():
        config = Settings(_env_file=None, openai_api_key="fixture", usage_db=tmp_path / "cost.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            with pytest.raises(ProviderError):
                await OpenAIProvider(client, config).plan_searches(
                    "Search", [], {}, first_round=True
                )

    asyncio.run(run())
    assert len(calls) == 1
