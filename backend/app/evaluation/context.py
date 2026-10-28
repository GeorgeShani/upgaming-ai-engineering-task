"""Frozen local inputs and read-only cloud corpus identity checks."""

import json
import subprocess
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from ..datasets.fixtures import load_fixtures
from ..datasets.preparation import verify_bundle
from ..retrieval.chunking import chunk_spans


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def local_context(fixtures=Path("fixtures"), prepared=Path("data/prepared")):
    verification = verify_bundle(prepared, fixtures)
    cases, _, manifest = load_fixtures(fixtures)
    documents = {}
    counts = {"a": 0, "b": 0}
    different = 0
    with (prepared / "corpus.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            doc = json.loads(line)
            documents[doc["document_id"]] = doc
            sentences = [(s["start"], s["end"]) for s in doc["segments"]]
            spans = {key: chunk_spans(doc["text"], key, sentences) for key in counts}
            for key in counts:
                counts[key] += len(spans[key])
            different += spans["a"] != spans["b"]
    return (
        cases,
        documents,
        {
            "verification": verification,
            "fixture_files": manifest["files"],
            "reference_review": manifest["reference_review"],
            "expected_active_chunks": counts,
            "documents_with_different_chunk_spans": different,
            "documents_with_identical_chunk_spans": len(documents) - different,
        },
    )


def code_identity(config, local):
    paths = sorted(Path("backend/app").rglob("*.py")) + [Path("uv.lock"), Path("pyproject.toml")]
    files = {path.as_posix(): sha256(path.read_bytes()).hexdigest() for path in paths}
    names = (
        "generation_model",
        "embedding_model",
        "embedding_dimensions",
        "api_budget_usd",
        "embedding_usd_per_million",
        "generation_input_usd_per_million",
        "generation_output_usd_per_million",
        "document_collection_prefix",
    )
    return {
        "code_files": files,
        "local": local,
        "settings": {name: getattr(config, name) for name in names},
        "runtime_packages": {
            name: version(name) for name in ("httpx", "pydantic", "fastapi", "tiktoken")
        },
    }


def git_revision():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


async def cloud_snapshot(store, index, documents):
    active, cursor = {}, None
    while True:
        result = await store.request(
            "POST",
            store.documents,
            "/points/scroll",
            body={
                "filter": {"must": [{"key": "deleted", "match": {"value": False}}]},
                "limit": 1000,
                "offset": cursor,
                "with_vector": False,
                "with_payload": [
                    "document_id",
                    "content_sha256",
                    "revision_id",
                    "index_profile",
                    "index_status",
                ],
            },
        )
        for point in result["points"]:
            item = point["payload"]
            key = item["document_id"]
            if key in active:
                raise ValueError("Cloud scroll returned a duplicate source ID.")
            active[key] = item
        cursor = result.get("next_page_offset")
        if cursor is None:
            break
    if set(active) != set(documents):
        raise ValueError(
            "Cloud active source IDs differ from the prepared corpus; do not evaluate."
        )
    for key, item in active.items():
        if (
            item["content_sha256"] != documents[key]["content_sha256"]
            or item["index_profile"] != index.profile
            or item["index_status"] != "ready"
        ):
            raise ValueError("Cloud source content/index profile is not ready or has changed.")
    counts = {}
    for key, collection in index.collections.items():
        result = await store.request("POST", collection, "/points/count", body={"exact": True})
        counts[key] = result["count"]
    return {
        "active_source_count": len(active),
        "active_manifests_sha256": digest(active),
        "profile": index.profile,
        "collections": index.collections,
        "physical_points": counts,
    }
