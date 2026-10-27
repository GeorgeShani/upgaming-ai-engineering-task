"""Local-only corpus import. Stop the web process while this single writer runs."""

import json
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from ..datasets.models import Document
from ..documents.models import DocumentSummary, Location, Revision


def corpus_revision(document):
    return Revision(
        document_id=document.document_id,
        revision_id=str(uuid5(NAMESPACE_URL, "corpus:v1:" + document.content_sha256)),
        filename=document.document_id + ".json",
        format="dataset",
        title=document.title,
        text=document.text,
        content_sha256=document.content_sha256,
        locations=[
            Location(kind="sentence", number=s.sentence_id, start=s.start, end=s.end, text=s.text)
            for s in document.segments
        ],
        metadata={key: str(value) for key, value in document.source.model_dump().items()},
        created_at=datetime.now(UTC).isoformat(),
    )


def read_corpus(path, limit=None):
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if limit is not None and index >= limit:
                break
            yield Document.model_validate_json(line)


async def import_batch(documents, index):
    store = index.store
    manifests = await store.get_many(store.documents, [doc.document_id for doc in documents])
    # An upload may already contain a corpus passage under a random management ID.
    # Preserve exact deduplication across the upload/import boundary too.
    missing_hashes = [doc.content_sha256 for doc in documents if doc.document_id not in manifests]
    other_ids = {}
    if missing_hashes:
        cursor = None
        while True:
            duplicates, cursor = await store.scroll(
                limit=256, cursor=cursor, digests=missing_hashes
            )
            other_ids.update({item["content_sha256"]: item["document_id"] for item in duplicates})
            if not cursor:
                break
    revisions, pending, skipped = [], [], 0
    for document in documents:
        old = manifests.get(document.document_id)
        if not old and document.content_sha256 in other_ids:
            skipped += 1
            continue
        if old and (
            old.get("deleted") is not False
            or old.get("content_sha256") != document.content_sha256
            or (old.get("index_status") == "ready" and old.get("index_profile") == index.profile)
        ):
            # Never resurrect a tombstone or overwrite an edit on resume.
            skipped += 1
            continue
        if old:
            raw = await store.get(store.revisions, old["revision_id"])
            revision = Revision.model_validate(raw)
        else:
            revision = corpus_revision(document)
        revisions.append(revision)
        now = datetime.now(UTC).isoformat()
        summary = DocumentSummary(
            document_id=revision.document_id,
            revision_id=revision.revision_id,
            filename=revision.filename,
            title=revision.title,
            format=revision.format,
            content_sha256=revision.content_sha256,
            created_at=revision.created_at,
            updated_at=now,
            index_status="ready",
            index_profile=index.profile,
        )
        pending.append((revision.document_id, {**summary.model_dump(), "deleted": False}))
    if not revisions:
        return {"activated": 0, "skipped": skipped, "chunks": {"a": 0, "b": 0}}
    await store.put_many(store.revisions, [(r.revision_id, r.model_dump()) for r in revisions])
    counts = await index.prepare(revisions)
    # Commit only after every revision and both configurations have been stored.
    # Partial/ambiguous batch activation is safe to resume through deterministic IDs.
    await store.put_many(store.documents, pending)
    return {"activated": len(revisions), "skipped": skipped, "chunks": counts}


def report_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"
