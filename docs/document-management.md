# Slice 3: document ingestion and management

The document API is implemented. Use FastAPI's interactive interface at
http://127.0.0.1:8000/docs to verify it. The React document screen is scheduled for slice 7.
Slice 4 now imports the 50,024-record local corpus into persistent hybrid indexes; see
[the indexing walkthrough](retrieval-and-first-answer.md) for progress and resume commands.

## Start and configure

Run from the repository root:

```powershell
uv sync --frozen
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

The root `.env` needs `QDRANT_URL`, `QDRANT_API_KEY` with write access, and `DEMO_ADMIN_TOKEN`.
Use a long random token. The existing local token was preserved during this slice; no secret
was printed or committed. Restart Python after editing `.env`. Set the same variables in Render
when deploying. Mutation routes are disabled when no admin token is set.

Canonical extracted text and selected metadata are publicly readable through GET routes. This
is a shared demonstration corpus, not private per-user storage. Upload the supplied fictional
samples for verification. Original file binaries are not stored or downloadable through the API.

## Follow one upload

```text
Authorized multipart request
  -> whole request size cap
  -> bounded file read and format parser
  -> normalized canonical text, locations, SHA-256
  -> active-content duplicate check
  -> immutable revision written to Qdrant
  -> both chunk configurations prepared when OpenAI is configured
  -> document manifest points to that revision
```

The admin header is checked before multipart parsing. The file limit is 5,000,000 bytes, with
65,536 bytes allowed for multipart overhead. A streamed body is also counted, even if it has no
Content-Length. MIME types are allowlisted, PDF/DOCX signatures are checked, and TXT must be UTF-8.
There are limits on expanded DOCX archives, PDF decoded content, pages, nesting, blocks, and text.
Extracted canonical text is limited to 1,000,000 characters and 2,000 locations; PDFs are limited
to 200 pages, and DOCX expanded archive content to 20 MB. A file can fit the upload limit but
still exceed an extraction limit.
Parsing has one slot per process and runs in a worker thread so network routes can remain responsive.
This is not an OS-isolated parser sandbox for arbitrary hostile documents.

PDF extraction preserves one-based page numbers. DOCX preserves paragraph/table-row locations and
flattens cell text. TXT paragraphs are separated by blank lines. Locations point into normalized
text. Complex PDF reading order, Word headers/footers/tracked changes, original layout, and OCR
are not guaranteed. Textless or encrypted PDFs receive actionable errors rather than empty records.
Mixed PDFs report pages without extractable text in metadata, so partial extraction is visible.

## Verify with the interactive API

1. Open `/docs`, click **Authorize**, and paste only the value of `DEMO_ADMIN_TOKEN` from your
   local `.env`, without the `Bearer ` prefix. Swagger adds that prefix. Keep the token local.
2. Expand **POST /api/documents**, select **Try it out**, and upload
   `fixtures/uploads/incident.pdf`. Expect HTTP 201, `duplicate: false`, a document ID, a revision ID,
   and an `ETag` response header. With both providers configured, `index_status: ready` means
   both configurations were staged before activation. `pending` means the text needs indexing.
3. Upload `incident.docx` and `incident.txt`. Their normalized text matches the PDF. Expect HTTP 200,
   `duplicate: true`, and the same document/revision IDs. First-retained filename/locations remain.
4. Call **GET /api/documents**. It lists active document summaries, with `limit` from 1 to 100 and
   an optional `next_cursor` to pass as `cursor` for the next page.
5. Call **GET /api/documents/{document_id}**. Inspect canonical text, page locations, author/title
   metadata, and the quoted `ETag`, for example `"<revision UUID>"`.
6. Use **PUT** on the same document ID, select `incident-updated.txt`, and copy that exact ETag,
   including its quote characters, into **if-match**. Expect the same document ID, a new revision
   ID/ETag, and recovery time changed from 12 to 8 minutes. GET now returns TXT paragraph locations.
7. Retry an edit or delete using the old ETag. Expect HTTP 412: reload before making another change.
   Omitting If-Match on an otherwise valid mutation gives HTTP 428. An unchanged-content replacement
   is a duplicate/no-op; replacing with another active document's text gives HTTP 409.
8. Use **DELETE** with the current ETag. Expect HTTP 204. GET by ID returns 404 and the listing
   excludes it, including after restarting the app. Original revisions remain stored but inactive.
9. Remove Swagger authorization and try an upload. Expect HTTP 401 before its file is parsed.

## Why revisions and ETags?

A document ID is a stable management identity, independent of its content. A revision ID names one
immutable parsed snapshot. This differs from slice 2's content-derived prepared-record IDs;
the SHA-256 field is still shared for normalized deduplication.

The active manifest is one Qdrant point. Replacement stages the new revision first, then commits
its pointer. A failure before activation leaves the previous revision active. A failed new upload
can leave an unreferenced revision, but no visible document. Do not eagerly remove staged revisions
after a timeout: the pointer write might have succeeded even if acknowledgement was lost.
The client gets 503 on an unconfirmed write and should reload state before retrying.

ETag identifies the current revision. If-Match prevents a stale client from overwriting an edit.
An app-level lock serializes mutations within the planned single process. It is not cross-process
compare-and-swap; do not add multiple workers/replicas without a stronger concurrency design.
A transactional SQL store would make that easier, but introduces another database here.

Deletion writes a tombstone. Old revisions are retained, rather than physically erased. Cleanup
of old/orphan revisions is future maintenance, and storage use grows with replacements. The
`filter_active_revisions` gate rejects missing, deleted, and superseded revision candidates.
Slice 4 now applies it after retrieval and prepares both chunk configurations before activating
a replacement. Without OpenAI configured, parsing-only writes remain pending. Re-uploading
identical content with providers configured repairs a pending index without changing its revision.

## Storage and verification

The existing HTTPX client calls a small set of Qdrant REST endpoints. Avoiding an SDK keeps the
adapter small and the request shapes visible, at the cost of maintaining those shapes ourselves.
Two payload-only collections hold manifests and revisions, with no dummy embeddings. Payload
indexes support filtering under Qdrant Cloud strict mode. Reads do not create collections;
initialization happens lazily on the first authorized mutation. Provider failures return generic
503 responses, without exposing credentials or raw provider error bodies.

Run the offline checks:

```powershell
uv run --group data pytest -W error
uv run ruff check backend scripts
uv run ruff format --check backend scripts
uv run python -m backend.app.dataset_cli verify
```

These tests use an HTTP-level Qdrant fake and do not contact model or database providers.
The fixture generator is not involved; the frozen dataset evaluation pack remains unchanged.

For the same real-provider smoke check used during implementation:

```powershell
uv run python scripts/verify_document_management.py
```

This uses your configured Qdrant account, creates only a fictional sample, checks all three
formats and replacement, starts fresh app instances to read durable state, and soft-deletes the
new sample. It stops without modifying an already-active matching document. It leaves a
tombstone/revisions and writes its report to ignored `artifacts/ingestion-live-check.json`.
Since slice 4, this smoke script can make paid embedding calls when OpenAI is configured;
it makes no generation calls. The committed `docs/ingestion-verification.json` records the
historical slice-3 run before indexing existed, not a claim that later runs make no model calls.
