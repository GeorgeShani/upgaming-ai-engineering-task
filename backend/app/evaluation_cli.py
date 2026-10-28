"""Local comparative evaluation. Preflight/read/score are free; run makes paid calls."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .config import Settings
from .documents.service import DocumentService
from .documents.store import QdrantDocumentStore, StoreUnavailable
from .evaluation.context import cloud_snapshot, code_identity, digest, git_revision, local_context
from .evaluation.reporting import select_strategy, summarize
from .evaluation.runner import RecordingSearch, maximum_reservation, run_attempts
from .evaluation.state import attempt_order, exclusive_run, load_or_create, save
from .investigations.service import InvestigationService
from .providers import BudgetExceeded, OpenAIProvider
from .retrieval.index import ChunkIndex


def records_for(folder, cases):
    paths = [
        folder / f"{key}-{strategy}.json"
        for key, strategy in attempt_order(case.case_id for case in cases)
    ]
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths if path.exists()]


def selection_for(output, manifest, cases, canonical):
    development = [case for case in cases if case.split == "development"]
    records = records_for(output / "development", development)
    if len(records) != len(development) * 2:
        raise ValueError("Complete every development attempt before selecting a configuration.")
    summary, _ = summarize(records, {case.case_id: case for case in development}, canonical)
    path = output / "selection.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["identity"] != manifest["identity"] or previous[
            "development_receipts_sha256"
        ] != digest(records):
            raise ValueError("Development records changed after configuration selection.")
        return previous
    if any((output / "final").glob("final-*.json")):
        raise ValueError("Cannot select a configuration after final results exist.")
    selection = {
        "identity": manifest["identity"],
        "created_at": datetime.now(UTC).isoformat(),
        "selected_strategy": select_strategy(summary),
        "rule": "supported_tasks, multi_source_context, initial_recall10, then A",
        "development_receipts_sha256": digest(records),
        "development_summary": summary,
    }
    save(path, selection)
    return selection


async def execute(args):
    config = Settings()
    cases, documents, local = local_context()
    canonical = {key: doc["text"] for key, doc in documents.items()}
    provider = None
    output = args.output
    with exclusive_run(output):
        if args.command in {"select", "summarize"}:
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            if code_identity(config, local) != manifest["details"]["code_and_local"]:
                raise ValueError("Evaluation code/settings/input identity changed.")
            if args.command == "select":
                print(json.dumps(selection_for(output, manifest, cases, canonical), indent=2))
                return
            selected = [case for case in cases if case.split == args.split]
            rows = records_for(output / args.split, selected)
            summary, scores = summarize(rows, {case.case_id: case for case in selected}, canonical)
            save(
                output / args.split / "summary.json",
                {
                    "identity": manifest["identity"],
                    "split": args.split,
                    "expected_attempts": len(selected) * 2,
                    "recorded_attempts": len(rows),
                    "strategies": summary,
                },
            )
            save(output / args.split / "scores.json", scores)
            print(json.dumps(summary, indent=2))
            return
        if (
            not config.qdrant_url
            or not config.qdrant_api_key.get_secret_value()
            or not config.openai_api_key.get_secret_value()
        ):
            raise ValueError("Configure OpenAI and Qdrant before cloud preflight/evaluation.")
        async with httpx.AsyncClient(timeout=5.0) as client:
            provider = OpenAIProvider(client, config)
            store = QdrantDocumentStore(client, config)
            index = ChunkIndex(store, provider, config)
            snapshot = await cloud_snapshot(store, index, documents)
            details = {"code_and_local": code_identity(config, local), "cloud": snapshot}
            manifest = load_or_create(
                output / "manifest.json",
                {
                    "identity": digest(details),
                    "details": details,
                    "git_revision": git_revision(),
                    "created_at": datetime.now(UTC).isoformat(),
                    "ledger_before": provider.ledger.summary(),
                    "maximum_reservation_per_attempt_usd": maximum_reservation(config),
                    "planned_attempts": 96,
                },
            )
            if args.command == "preflight":
                previous = json.loads(
                    Path("docs/multistep-verification.json").read_text(encoding="utf-8")
                )["cases"]
                prior_mean = sum(
                    row["usage"]["estimated_total_cost_usd"] for row in previous
                ) / len(previous)
                projection = {
                    "based_on": "four earlier development smoke cases, not final results",
                    "mean_known_estimated_cost_usd": prior_mean,
                    "96_attempt_projection_with_30_percent_margin_usd": prior_mean * 96 * 1.3,
                    "96_attempt_maximum_reservations_usd": maximum_reservation(config) * 96,
                }
                save(output / "cost-projection.json", projection)
                print(
                    json.dumps(
                        {
                            "identity": manifest["identity"],
                            "cloud": snapshot,
                            "local": local,
                            "ledger": provider.ledger.summary(),
                            "ceiling_usd": config.api_budget_usd,
                            "maximum_reservation_per_attempt_usd": maximum_reservation(config),
                            "cost_projection": projection,
                            "warning": (
                                "Maximum reservations for all 96 may exceed remaining ceiling; "
                                "guard each attempt. This estimate is not an invoice."
                            ),
                        },
                        indent=2,
                    )
                )
                return
            if args.split == "final":
                if not (output / "selection.json").exists():
                    raise ValueError(
                        "Select the configuration from development before running final cases."
                    )
                selection_for(output, manifest, cases, canonical)
            selected = [case for case in cases if case.split == args.split]
            folder = output / args.split
            load_or_create(
                folder / "run.json",
                {
                    "identity": manifest["identity"],
                    "split": args.split,
                    "started_at": datetime.now(UTC).isoformat(),
                    "git_revision": git_revision(),
                    "ledger_before": provider.ledger.summary(),
                    "attempt_order": attempt_order(case.case_id for case in selected),
                },
            )
            search = RecordingSearch(index, DocumentService(store, index))
            service = InvestigationService(search, provider)
            try:
                await run_attempts(service, search, provider.ledger, selected, config, folder)
            finally:
                after = await cloud_snapshot(store, index, documents)
                consistent = after == manifest["details"]["cloud"]
                save(
                    folder / "checkpoint.json",
                    {
                        "identity": manifest["identity"],
                        "recorded_at": datetime.now(UTC).isoformat(),
                        "corpus_consistent": consistent,
                        "cloud": after,
                        "ledger_after": provider.ledger.summary(),
                    },
                )
                if not consistent:
                    raise ValueError(
                        "Corpus changed during evaluation; results are not a controlled comparison."
                    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run", "select", "summarize"))
    parser.add_argument("--split", choices=("development", "final"), default="development")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation"))
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except BudgetExceeded:
        raise SystemExit(
            "Stopped before the next attempt: insufficient remaining reservation budget."
        ) from None
    except StoreUnavailable:
        raise SystemExit("Storage preflight/checkpoint failed; no automatic retry.") from None
    except ValueError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
