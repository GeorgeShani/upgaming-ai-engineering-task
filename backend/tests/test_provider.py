import asyncio
import base64
import json
from array import array

import httpx
import pytest
from app.config import Settings
from app.providers import BudgetExceeded, OpenAIProvider, ProviderError, UsageLedger


def test_embedding_cache_survives_provider_restart_and_validates_dimensions(tmp_path):
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["dimensions"] == 384 and body["encoding_format"] == "base64"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": base64.b64encode(array("f", [0.01] * 384)).decode()}
                    for i, _ in enumerate(body["input"])
                ],
                "usage": {"prompt_tokens": 2, "total_tokens": 2},
            },
        )

    config = Settings(_env_file=None, openai_api_key="fixture", usage_db=tmp_path / "usage.db")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            one = OpenAIProvider(client, config)
            vectors, usage = await one.embed(["hello", "hello"], include_usage=True)
            assert len(vectors) == 2 and usage["api_calls"] == 1 and usage["input_tokens"] == 2
            two = OpenAIProvider(client, config)
            cached, usage = await two.embed(["hello"], include_usage=True)
            assert len(cached[0]) == 384 and usage["api_calls"] == 0
            assert usage["cache_hits"] == 1 and usage["estimated_cost_usd"] == 0

    asyncio.run(run())
    assert len(calls) == 1 and calls[0]["input"] == ["hello"]


def test_budget_reserves_before_network_and_keeps_uncertain_calls(tmp_path):
    ledger = UsageLedger(tmp_path / "usage.db", 0.1)
    ledger.reserve("embedding", 0.09)
    with pytest.raises(BudgetExceeded):
        ledger.reserve("embedding", 0.02)
    assert ledger.summary()["reserved_usd"] == pytest.approx(0.09)
    ledger.complete(1, 10, 0, 0.11)
    assert ledger.summary()["reserved_usd"] == pytest.approx(0.11)


@pytest.mark.parametrize("mode", ["http", "dimensions", "nan"])
def test_provider_errors_are_not_missing_evidence(tmp_path, mode):
    def handler(request):
        if mode == "http":
            return httpx.Response(429, text="private-provider-details")
        return httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": [0.1] * (2 if mode == "dimensions" else 384)}],
                "usage": {"prompt_tokens": "bad" if mode == "nan" else 1},
            },
        )

    config = Settings(_env_file=None, openai_api_key="fixture", usage_db=tmp_path / "usage.db")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ProviderError):
                await OpenAIProvider(client, config).embed(["source"])

    asyncio.run(run())
