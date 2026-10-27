"""python -m backend.app.index_cli estimate|run --help (from repository root)."""

import argparse
import asyncio
import hashlib
import json
import time
from itertools import batched
from pathlib import Path

import httpx

from .config import Settings
from .documents.store import QdrantDocumentStore, StoreUnavailable
from .providers import BudgetExceeded, OpenAIProvider, ProviderError, UsageLedger
from .retrieval.bulk import corpus_revision, import_batch, read_corpus, report_json
from .retrieval.chunking import chunk_spans, token_count
from .retrieval.index import ChunkIndex


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def estimate(args, config):
    report = {
        "corpus_sha256": digest(args.corpus),
        "documents": 0,
        "embedding_model": config.embedding_model,
        "dimensions": config.embedding_dimensions,
        "configurations": {key: {"chunks": 0, "tokens": 0} for key in ("a", "b")},
    }
    for document in read_corpus(args.corpus, args.limit):
        report["documents"] += 1
        revision = corpus_revision(document)
        sentences = [(loc.start, loc.end) for loc in revision.locations]
        for strategy, values in report["configurations"].items():
            spans = chunk_spans(document.text, strategy, sentences)
            values["chunks"] += len(spans)
            values["tokens"] += sum(token_count(document.text[a:b]) for a, b in spans)
    for values in report["configurations"].values():
        values["embedding_cost_upper_estimate_usd"] = (
            values["tokens"] * config.embedding_usd_per_million / 1e6
        )
        values["dense_vector_bytes_float32"] = values["chunks"] * config.embedding_dimensions * 4
    report["note"] = (
        "Before cache reuse; excludes payload, sparse vectors, HNSW and provider overhead."
    )
    return report


async def run(args, config):
    if not config.qdrant_url or not config.qdrant_api_key.get_secret_value():
        raise SystemExit("Configure Qdrant in .env first.")
    if not config.openai_api_key.get_secret_value():
        raise SystemExit("Configure OpenAI in .env first.")
    report = {
        "corpus_sha256": digest(args.corpus),
        "documents_seen": 0,
        "activated": 0,
        "skipped": 0,
        "chunks_written": {"a": 0, "b": 0},
    }
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        store = QdrantDocumentStore(client, config)
        provider = OpenAIProvider(client, config)
        index = ChunkIndex(store, provider, config)
        report["profile"] = index.profile
        report["collections"] = index.collections
        before = provider.ledger.summary()
        await store.initialize()
        await index.initialize()
        for batch in batched(read_corpus(args.corpus, args.limit), args.batch_size):
            for attempt in range(3):
                try:
                    result = await import_batch(batch, index)
                    break
                except StoreUnavailable:
                    if attempt == 2:
                        raise
                    print("Storage interrupted; retrying this idempotent batch.", flush=True)
                    await asyncio.sleep(1)
            report["documents_seen"] += len(batch)
            for key in ("activated", "skipped"):
                report[key] += result[key]
            for key in ("a", "b"):
                report["chunks_written"][key] += result["chunks"][key]
            report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            report["usage_before"] = before
            report["usage_after"] = provider.ledger.summary()
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(report_json(report), encoding="utf-8")
            print(
                json.dumps(
                    {
                        key: report[key]
                        for key in ("documents_seen", "activated", "skipped", "elapsed_seconds")
                    }
                ),
                flush=True,
            )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["estimate", "run", "usage"])
    parser.add_argument("--corpus", type=Path, default=Path("data/prepared/corpus.jsonl"))
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--batch-size", type=int, default=256, choices=range(1, 257), metavar="1..256"
    )
    parser.add_argument("--report", type=Path, default=Path("artifacts/indexing-report.json"))
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    config = Settings()
    if args.command == "usage":
        print(report_json(UsageLedger(config.usage_db, config.api_budget_usd).summary()))
        return
    try:
        report = (
            estimate(args, config) if args.command == "estimate" else asyncio.run(run(args, config))
        )
    except (StoreUnavailable, ProviderError, BudgetExceeded) as error:
        raise SystemExit(
            f"{type(error).__name__}: stopped safely. Re-run to resume; cached embeddings remain. "
            "The report contains the last fully completed batch, not staged writes."
        ) from None
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_json(report), encoding="utf-8")
    print(report_json(report))


if __name__ == "__main__":
    main()
