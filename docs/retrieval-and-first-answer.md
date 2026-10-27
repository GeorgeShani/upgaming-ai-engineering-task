# Slices 4 and 5: retrieve evidence, then answer from it

These slices implement two chunkers, persistent dense/BM25 search, our own rank fusion,
resumable local corpus indexing, and one cited-answer request. The React screen remains the
connection screen until slice 7. Use `/docs` for the new endpoint. Slice 6 adds model tool calls
and entity follow-up searches; the current response explicitly says `single_search_v1`.

## 1. Understand the stored objects

```text
Source document (canonical text and provenance)
  -> immutable revision
  -> configuration A chunks -> OpenAI dense vectors + Qdrant BM25 sparse vectors
  -> configuration B chunks -> OpenAI dense vectors + Qdrant BM25 sparse vectors
  -> activate the revision only after both configurations are prepared

Question -> question embedding -> top 30 dense + top 30 BM25
  -> reject deleted / inactive revisions -> custom RRF -> at most 8 chunks, 2 per document
  -> structured model claims -> validate IDs and literal quotes -> answer with references
```

The 50,024 prepared records are source documents, not chunks. Indexing produces 52,246 A chunks
and 52,307 B chunks for the unchanged prepared corpus. Uploads add separate records/chunks.
Canonical text lives in the revision collection; retrieval payloads contain only their chunk
text, offsets, title, intersecting locations, and source metadata. Imported locations use the
original zero-based HotpotQA sentence IDs. Uploaded pages/paragraphs retain their one-based numbers.

Configuration A uses `cl100k_base` BPE windows of 256 tokens with 40 overlap. Unicode boundaries
can shorten a window or change overlap slightly. B groups original dataset sentences, or a simple
punctuation-based sentence splitter for uploads, up to 256 tokens, overlapping one sentence.
Oversized sentences split into fragments; overlap is omitted when necessary to fit new content.
The fallback can misread abbreviations such as “Dr.”; it is deterministic, not linguistic analysis.

**Try:** Find a long source and compare A/B offsets in `ChunkIndex.chunks`. Verify that every
chunk equals `document.text[start:end]` and has at most 256 tokens. The Unicode/oversized-sentence
tests demonstrate the difficult boundaries. A token limit is different from a character limit.

## 2. Reproduce the resource estimate without paid calls

From the repository root, with the already prepared corpus:

```powershell
uv sync --frozen --group data
uv run python -m backend.app.dataset_cli verify
uv run python -m backend.app.index_cli estimate --report artifacts/my-index-estimate.json
```

The scan takes a few minutes and makes no provider calls. Compare with `docs/index-estimate.json`.
Both configurations together cost an estimated $0.245793 before exact embedding-cache reuse.
Dense float32 arrays alone use about 160.6 MB; this excludes Qdrant payload, sparse index, HNSW,
and database overhead. This is a capacity estimate, not a free-tier storage guarantee.

The first 1,000-record pilot took 184.732 seconds, or 5.41 records/sec. A linear estimate at that
rate is about 2.6 hours for the complete corpus. Later batching changes reduce round trips, but
network/free-tier performance varies. The committed pilot/resume reports include a genuine
connection failure and successful recovery; they are not final evaluation results.

## 3. Run, pause, and resume indexing

The configured `.env` needs OpenAI and Qdrant credentials. Do not paste them into commands or
the browser. Canonical text and indexes are durable in Qdrant; the cache/ledger is local SQLite
under ignored `data/usage.sqlite3`. Keep that file to retain embeddings and cost reservations.

Use one corpus importer and stop the web server during imports: the single-writer deployment
does not have a distributed lock. Do not run two imports simultaneously. A full run has already
been started during implementation; inspect its progress before launching another:

```powershell
Get-Content artifacts/index-full.log -Tail 5
Get-Content artifacts/index-full.json
Get-Content artifacts/index-full.error.log -Tail 5
```

The report counts completed batches in this run, including skipped records. `documents_seen`
is not an active-corpus count: resume can skip previous completions, tombstones, edited documents,
or content already retained under an upload ID. An incomplete last batch can leave staged data.

For a new foreground run, after the current importer exits:

```powershell
uv run python -m backend.app.index_cli run --limit 1000 --report artifacts/my-pilot.json
uv run python -m backend.app.index_cli run --report artifacts/my-full-run.json
uv run python -m backend.app.index_cli usage
```

`Ctrl+C` stops a foreground run. Re-run the same command to resume. Current completed manifests
are skipped, staged chunks use deterministic IDs, and exact chunk embeddings are cached across
A/B. A timeout can occur after a write committed, so resume reloads current manifests rather
than assuming failure. A tombstone is never resurrected; an edit is never overwritten by import.
Exact upload/import duplicates retain the first active source instead of adding a second document.

For the implementation's hidden background process, `artifacts/index-full.pid` identifies the
actual worker. If you want to pause it to verify the web app, inspect that process first:

```powershell
$indexWorker = [int](Get-Content artifacts/index-full.pid)
Get-CimInstance Win32_Process -Filter "ProcessId=$indexWorker" | Select-Object ProcessId,Name,CommandLine
# Only after confirming this is the python -m backend.app.index_cli run worker:
Stop-Process -Id $indexWorker
```

Stopping can leave staged chunks, which retrieval excludes. Stop the web server before resuming
with the foreground full-run command above. These are local process operations, not data deletion.

The CLI retries a deterministic storage batch at most twice. It stops on a model failure or
budget rejection. Retrying a timed-out model request manually may incur another charge; its
reservation is intentionally retained. The $4.50 local ceiling leaves contingency within the
$5 target. It does not include other API clients, enforce a provider account cap, or survive a
Render temporary-disk reset. Read current account usage before large future runs.

**Try:** Resume the 1,000-record pilot after it already completed. Expect skipped records and
no additional embedding calls. Read `test_bulk_indexing.py` for interrupted activation, content
deduplication across uploads/imports, and preservation of deletions/edits.

## 4. Calculate the hybrid ranking yourself

Dense search finds semantically similar wording. BM25 rewards matching terms, accounting for
term frequency, length, and inverse document frequency. Qdrant's built-in `qdrant/bm25` runs on
the database side; both insert and query use the same defaults and its `idf` sparse modifier.
The server does not load a local embedding or sparse model.

Suppose a chunk ranks second in dense search and first in BM25:

```text
score = 1/(60+2) + 1/(60+1) = 0.032522...
```

Another chunk ranked first only in dense gets `1/61 = 0.016393...`. The first ranks above it.
We deduplicate each result list, sum reciprocal ranks, break ties by chunk ID, then apply the
eight-chunk / two-per-document caps. Similarity scores from the two methods have different
scales, which is why we combine ranks. An RRF score is not the probability a claim is true.

Old/staged/deleted chunk data remains physically present. The active gate prevents returning it,
but it can occupy candidate slots and influence BM25's collection-wide IDF. Garbage collection
or overfetching can improve recall later. Separate A/B collections keep their IDF statistics
independent. Changing the embedding model, dimensions, or chunk algorithm requires reindexing
under a new profile; old collections require deliberate maintenance and consume capacity.

## 5. Ask the first question and inspect what the model saw

After indexing has stopped or completed, start Python:

```powershell
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs, expand **POST /api/investigations**, choose **Try it out**, and send:

```json
{
  "question": "What recovery time was documented for fictional incident NOVA-DEVELOPMENT-01?",
  "strategy": "a"
}
```

Investigations do not require the document mutation token. Expect `status: answered`, a claim
reporting **11 minutes**, its supporting quote, and an `[E1]`-style reference. Evidence IDs are
local to this answer, not stable database IDs. API failures carry HTTP error codes and no answer.

1. Read `search_trace[0].query` and `candidate_counts`: both search methods requested 30.
2. Find the cited entry in `evidence`; read its title, chunk text, source metadata, and locations.
3. Copy its `document_id` into **GET /api/documents/{document_id}**. Compare revision IDs and verify
   that `source.text[start:end]` equals the evidence text.
4. Find the exact quoted excerpt. Then independently decide whether it supports the claim.
5. Open `backend/app/investigations/service.py`: the model receives the question and selected
   evidence IDs/titles/text as JSON, plus the fixed instructions and schema. It does not receive
   the whole corpus, evaluation answers, support labels, or hidden search reasoning.

For a scripted paid check:

```powershell
uv run python scripts/verify_first_answer.py
```

This reads one **development** question, calls the real API dependencies, checks the returned
claim against its expected short answer, fetches every cited source, and writes ignored raw
trace and compact report artifacts. The historical successful report is committed at
`docs/first-answer-verification.json`. The 40 final questions remain frozen and unexecuted.
Configuration A is provisional; deployment selection belongs to development evaluation later.

**Try:** Ask who approved that incident's rollback. It should return `insufficient_evidence`;
read the source to confirm why. This is a useful manual probe, not a guarantee that one-search
retrieval discovers every missing fact or conflict. Two-hop questions belong to slice 6.

## 6. Understand validation and error boundaries

| Result | Meaning |
| --- | --- |
| `answered` | Model returned cited claims that passed structural/quote checks |
| `insufficient_evidence` | Retrieved context could not support an answer; no fabricated claim |
| `conflicting_evidence` | Model reports incompatible claims citing at least two documents |
| HTTP 409 | Evidence changed during generation; retry against current revisions |
| HTTP 422 | Invalid question/configuration or context too large |
| HTTP 429 | Six-per-minute shared demo limit or another investigation is running |
| HTTP 502 | Provider failed/refused/incomplete, or output failed citation validation |
| HTTP 503 | Storage/configuration/local budget unavailable |
| HTTP 504 | Whole investigation exceeded 90 seconds |

The server validates known evidence IDs, exact quoted text, a citation on every returned claim,
and consistent status/claim arrays. It rechecks revision eligibility after generation.
Semantic support and actual contradictions require evaluation: a model can cite a real but
irrelevant quote. The prompt treats source text as untrusted data; this reduces prompt-injection
risk without proving the model will always ignore embedded instructions.

Generation has one call, 1,200 output tokens, no automatic paid retries, and an 8,000-token context
cap. The trace shows selected evidence, not private reasoning. Generation usage is per request;
embedding/indexing usage is in the local ledger. Cached embedding hits incur no new embedding call.

## 7. Run the independent checks before moving on

```powershell
uv run --group data pytest -W error
uv run ruff check backend scripts
uv run ruff format --check backend scripts
```

These tests use HTTP-level provider fakes and do not spend API credit. They cover chunk boundaries,
locations, RRF/diversity, cache/cost guards, failed staging/activation, resume, source deduplication,
stale/deleted exclusion, invalid citations, sanitized provider errors, rate limits, and evidence
changing during generation. The real smoke report is separate evidence of cloud compatibility.

Before slice 6, explain in your own words: document versus revision versus chunk; semantic versus
keyword retrieval; the reciprocal-rank calculation; what the model saw; and why a literal matching
quote is necessary but insufficient. Record your own explanation in the journal, leaving unclear
points as questions instead of checking off understanding automatically.

Official references used during implementation:
[Qdrant BM25](https://qdrant.tech/documentation/inference/inference-bm25/),
[OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[embedding pricing](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[generation model/pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini), and
[tiktoken](https://github.com/openai/tiktoken).
