"""One serial, bounded attempt using the production services; never retry paid failures."""

import time
from datetime import UTC, datetime

from fastapi import HTTPException

from ..documents.store import StoreUnavailable
from ..providers import BudgetExceeded, ContextLimitExceeded, ProviderError
from ..retrieval.search import SearchService
from .state import attempt_order, recover_pending, save


class RecordingSearch(SearchService):
    def __init__(self, index, documents):
        super().__init__(index, documents)
        self.recorded = []

    async def search(self, query, strategy):
        result = await super().search(query, strategy)
        self.recorded.append(result)
        return result


def maximum_reservation(config):
    # Provider's existing 12k body limit, 20%+1024 input reservation margin;
    # planning outputs <=600+600, answer <=1200, <=3 queries of <=500 Unicode chars.
    return (
        3 * (int(12000 * 1.2) + 1024) * config.generation_input_usd_per_million
        + 2400 * config.generation_output_usd_per_million
        + 3 * 2000 * config.embedding_usd_per_million
    ) / 1e6


def guard_budget(ledger, config):
    if ledger.summary()["reserved_usd"] + maximum_reservation(config) > ledger.ceiling:
        raise BudgetExceeded


async def attempt(service, search, ledger, case_id, strategy, question):
    search.recorded.clear()
    row = {
        "case_id": case_id,
        "strategy": strategy,
        "question": question,
        "started_at": datetime.now(UTC).isoformat(),
        "ledger_before": ledger.summary(),
    }
    started = time.perf_counter()
    try:
        row.update(result=await service.bounded_investigate(question, strategy), error=None)
    except (
        HTTPException,
        ProviderError,
        StoreUnavailable,
        ContextLimitExceeded,
        BudgetExceeded,
    ) as error:
        labels = {
            ProviderError: "provider_failure",
            StoreUnavailable: "storage_failure",
            ContextLimitExceeded: "context_limit",
            BudgetExceeded: "budget_limit",
        }
        row.update(
            result=None,
            error=f"http_{error.status_code}"
            if isinstance(error, HTTPException)
            else labels[type(error)],
        )
        row["partial_searches"] = list(search.recorded)
    row.update(
        elapsed_ms=round((time.perf_counter() - started) * 1000), ledger_after=ledger.summary()
    )
    return row


async def run_attempts(service, search, ledger, cases, config, folder):
    folder.mkdir(parents=True, exist_ok=True)
    recover_pending(folder, ledger.summary())
    by_id = {case.case_id: case for case in cases}
    for key, strategy in attempt_order(by_id):
        target = folder / f"{key}-{strategy}.json"
        if target.exists():
            continue
        guard_budget(ledger, config)
        pending = folder / f"{key}-{strategy}.pending.json"
        save(
            pending,
            {
                "case_id": key,
                "strategy": strategy,
                "question": by_id[key].question,
                "started_at": datetime.now(UTC).isoformat(),
                "ledger_before": ledger.summary(),
            },
        )
        row = await attempt(service, search, ledger, key, strategy, by_id[key].question)
        save(target, row)
        pending.unlink()
        print(
            key,
            strategy.upper(),
            row["error"] or row["result"]["status"],
            f"{row['elapsed_ms']}ms",
            flush=True,
        )
        if row["error"]:
            raise ValueError(
                "Failed attempt saved without retry. "
                "Inspect it before resuming the remaining cases."
            )
