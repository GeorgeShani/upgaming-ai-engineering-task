"""Read-only corpus and active chunk audit; no embeddings, model calls, or cloud writes."""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from hashlib import sha256
from itertools import batched
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings
from app.datasets.preparation import verify_bundle
from app.documents.store import QdrantDocumentStore
from app.evaluation.context import cloud_snapshot, digest
from app.evaluation.state import save
from app.retrieval.bulk import corpus_revision, read_corpus
from app.retrieval.index import ChunkIndex


def identity(payload):
    return {key: payload[key] for key in ("document_id", "revision_id", "start", "end")} | {
        "text_sha256": sha256(payload["text"].encode()).hexdigest(),
    }


async def verify(prepared):
    verification = verify_bundle(prepared, Path("fixtures"))
    config = Settings()
    async with httpx.AsyncClient() as client:
        store = QdrantDocumentStore(client, config)
        index = ChunkIndex(store, None, config)
        documents, revisions = {}, {}
        expected = {"a": {}, "b": {}}
        for batch in batched(read_corpus(prepared / "corpus.jsonl"), 200):
            rows = [corpus_revision(document) for document in batch]
            for document, revision in zip(batch, rows, strict=True):
                documents[document.document_id] = {"content_sha256": document.content_sha256}
                revisions[document.document_id] = revision.revision_id
            for strategy, points in index.chunks(rows).items():
                for point in points:
                    assert point["id"] not in expected[strategy], "Duplicate expected chunk ID."
                    expected[strategy][point["id"]] = identity(point["payload"])
        assert len(documents) >= 50_000
        assert len({item["content_sha256"] for item in documents.values()}) == len(documents)
        before = await cloud_snapshot(store, index, documents)
        expected_manifests = {
            key: {
                "document_id": key,
                "content_sha256": value["content_sha256"],
                "revision_id": revisions[key],
                "index_profile": index.profile,
                "index_status": "ready",
            }
            for key, value in documents.items()
        }
        assert before["active_manifests_sha256"] == digest(expected_manifests), (
            "Active revision identities differ from the canonical corpus."
        )
        strategies = {}
        for strategy, collection in index.collections.items():
            found, cursor, physical, inactive = set(), None, 0, 0
            while True:
                result = await store.request(
                    "POST",
                    collection,
                    "/points/scroll",
                    body={
                        "limit": 1000,
                        "offset": cursor,
                        "with_vector": False,
                        "with_payload": ["document_id", "revision_id", "start", "end", "text"],
                    },
                )
                for point in result["points"]:
                    physical += 1
                    payload = point["payload"]
                    if revisions.get(payload["document_id"]) != payload["revision_id"]:
                        inactive += 1
                        continue
                    key = point["id"]
                    assert key not in found, "Duplicate active point during scroll."
                    assert key in expected[strategy], "Unexpected active chunk."
                    assert identity(payload) == expected[strategy][key], "Chunk content differs."
                    found.add(key)
                cursor = result.get("next_page_offset")
                if cursor is None:
                    break
            assert found == set(expected[strategy]), "Active chunks are missing."
            assert physical == before["physical_points"][strategy], "Index changed during audit."
            strategies[strategy] = {
                "expected_active": len(expected[strategy]),
                "actual_active": len(found),
                "physical_points": physical,
                "inactive_points": inactive,
                "active_point_ids_sha256": digest(sorted(found)),
                "source_revision_offsets_and_text_verified": True,
            }
        after = await cloud_snapshot(store, index, documents)
        assert after == before, "Corpus changed during read-only verification."
    return {
        "passed": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "Full canonical source/hash/profile identity and every eligible A/B chunk",
        "prepared": verification,
        "cloud": after,
        "strategies": strategies,
        "paid_calls": 0,
        "cloud_writes": 0,
        "canonical_revision_identity_verified": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=Path("data/prepared"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/deployment-corpus.json"))
    args = parser.parse_args()
    report = asyncio.run(verify(args.prepared))
    save(args.report, report)
    print(f"Verified {report['cloud']['active_source_count']} sources and both complete indexes.")


if __name__ == "__main__":
    main()
