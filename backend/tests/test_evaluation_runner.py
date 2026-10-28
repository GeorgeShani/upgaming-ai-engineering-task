import asyncio
from types import SimpleNamespace

import pytest
from app.config import Settings
from app.evaluation.runner import attempt, guard_budget, maximum_reservation, run_attempts
from app.providers import BudgetExceeded, ProviderError, UsageLedger


def test_budget_preflight_prevents_network_when_full_attempt_would_exceed_ceiling(tmp_path):
    config = Settings(_env_file=None)
    ledger = UsageLedger(tmp_path / "usage.db", 0.04)
    assert maximum_reservation(config) == pytest.approx(0.062592)
    with pytest.raises(BudgetExceeded):
        guard_budget(ledger, config)


def test_attempt_records_provider_failure_without_retry_or_gold_arguments(tmp_path):
    ledger = UsageLedger(tmp_path / "usage.db", 4.5)
    calls = []

    class Service:
        async def bounded_investigate(self, question, strategy):
            calls.append((question, strategy))
            ledger.reserve("planning", 0.01)
            raise ProviderError

    service = Service()
    row = asyncio.run(
        attempt(service, SimpleNamespace(recorded=[]), ledger, "case", "b", "Question?")
    )
    assert calls == [("Question?", "b")]
    assert row["result"] is None and row["error"] == "provider_failure"
    assert row["ledger_after"]["reserved_usd"] == 0.01
    assert row["ledger_before"]["reserved_usd"] == 0


def test_resuming_completed_receipts_does_not_make_another_model_call(tmp_path):
    config = Settings(_env_file=None)
    ledger = UsageLedger(tmp_path / "usage.db", 4.5)
    calls = []

    class Service:
        async def bounded_investigate(self, question, strategy):
            calls.append((question, strategy))
            return {"status": "answered"}

    async def run():
        cases = [SimpleNamespace(case_id="case", question="Only this question")]
        folder = tmp_path / "receipts"
        for _ in range(2):
            await run_attempts(
                Service(), SimpleNamespace(recorded=[]), ledger, cases, config, folder
            )

    asyncio.run(run())
    assert calls == [("Only this question", "a"), ("Only this question", "b")]
