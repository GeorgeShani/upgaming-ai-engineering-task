# Engineering journal

This journal records the real implementation and learning process. AI may draft explanations and
code; only George fills in his understanding and independent work. A checkpoint stays pending
until that review actually happens.

## Session 1: Connect the browser to Python

### What changed

A small React/TypeScript page calls `GET /api/health`. FastAPI returns a typed report about the
application and read-only access to OpenAI and Qdrant. `/api/live` reports only process liveness.
Production serves the React build and API from the same Python process. Vite proxies `/api` to
Python during development. A Dockerfile and Render blueprint describe the production build.

### Why

We need to prove that the pieces can communicate before adding ingestion or RAG. Keeping the
production UI and API on one origin avoids a second deployment and cross-origin configuration.
The server reads secrets; the browser sees only a small status report.

Liveness and dependency readiness answer different questions. If OpenAI is unavailable, Render
should not continually restart a healthy Python process. Render therefore checks `/api/live`;
the setup page checks `/api/health` and can display degraded dependencies.

### Alternatives and drawbacks

- Separate frontend hosting is valid, but adds a second deployment and API origin configuration.
- Gradio would be quicker, but React was chosen to use George's existing web experience.
- Calling OpenAI from React would expose a credential to every visitor. Provider requests belong
  on the server.
- Making a paid generation request on every health check would waste tokens. We read model
  metadata instead. This checks access, not actual generation capacity or remaining credit.
- Creating a client for every provider request discards connection pooling. FastAPI's lifespan
  creates one HTTP client and closes it when the application stops.

### Trace a concrete request

1. The browser loads the React page and requests `/api/health`.
2. In development Vite forwards that request to `127.0.0.1:8000`. In production the request goes
   directly to the same FastAPI server that served the page.
3. FastAPI reads server configuration. Missing credentials produce `unconfigured`, with no network
   request. With credentials, it checks both configured OpenAI models and Qdrant's collections API.
4. Independent checks run concurrently. A rejected request or timeout becomes `unavailable`.
   Raw provider errors and secrets never appear in the response.
5. The server returns HTTP 200 if all access checks pass, or HTTP 503 with a structured degraded
   report otherwise. React deliberately handles that expected 503 and displays the report.

`async` allows other work while a request waits for network I/O. It does not make CPU-heavy
document parsing faster. `asyncio.gather` lets independent access checks wait concurrently.
Pydantic validates configuration and describes the JSON contract; TypeScript describes the
browser's expected shape. The browser's type is not runtime validation of arbitrary JSON.

### Verification

- `uv run pytest -W error`: 9 passed. All provider responses use a fake HTTP transport; these
  results do not claim that a real cloud connection succeeded.
- `uv run ruff check backend` and `uv run ruff format --check backend`: passed after correcting
  formatting and import order.
- `npm run build` in `frontend`: TypeScript and production build passed with Vite 8.3.5.
- Actual browser at `http://127.0.0.1:8000`: React loaded from FastAPI, displayed both providers
  as needing setup, and refreshed successfully. Browser error/warning logs were empty.
- Tests cover 401/429/500 responses, timeout handling, redaction, both model access requests,
  unconfigured services without outbound calls, and preservation of API 404 responses.
- The installed Starlette test client preferred `httpx2`; added that as a development dependency
  after checking the installed source and current FastAPI documentation. No warning suppression.
- Docker image build was not run: the Docker Desktop engine is stopped. The same frontend build
  was served by Python locally; that does not replace verification of the actual container.
- At the first foundation commit, real provider access was pending. George subsequently added
  credentials; the follow-up verification below records the actual access results. No public
  Render demo URL has been verified.

### My understanding (George writes this)

- [ ] I ran the app locally and opened the API docs.
- [ ] I found the browser's `/api/health` request in the Network panel.
- [ ] I can explain why HTTP 503 here does not mean the Python process crashed.
- [ ] I can point to the code that keeps secrets on the server.
- [ ] I can explain why a metadata check does not prove generation or indexing works.
- [ ] I changed one visible label, rebuilt, and explained which code runs in the browser.

My explanation:

> Pending George's review.

Questions I still have:

> Pending George's review.

### AI contribution

Codex drafted the plan files, foundation code, tests, deployment configuration, and this
explanation. No claim of independent coding or understanding is made for George.

### Resume point

Run the README's local commands, inspect the request trace above, and complete the understanding
checklist. Provider access is now verified; public deployment remains pending. Session 2 follows
George's review.

## Session 1 follow-up: credentials and preview

### What changed and why

George added provider credentials to the local configuration. The previous Python process still
held the settings it loaded at startup, so Codex restarted that managed process to load them.
Secrets were not printed, committed, or sent to the browser.

Added `npm run preview`, with npm's `prepreview` lifecycle running the production build first.
Both Vite modes share the same `/api` proxy configuration. Preview listens on 127.0.0.1:4173
with a strict port so a second invocation cannot silently start on another port.

Alternative: require a separate `npm run build` before every preview. That is conventional, but
easy to forget while reviewing changes. Automatically rebuilding costs a few seconds and makes
the result easier to reproduce. Vite already inherits the dev proxy by default; naming the shared
proxy explicitly makes the two local modes visible in one short configuration.

### Observed verification

- Read-only OpenAI checks passed for both configured models.
- The first Qdrant check failed to connect or timed out. A subsequent direct check resolved DNS
  and returned HTTP 200 in approximately 1.17 seconds. No credentials or timeout were changed.
  This observation does not establish the cause of the initial network failure.
- After restarting Python, the actual React page on port 4173 showed both providers connected.
- `/api/live` through preview returned HTTP 200 and `{"status":"running"}`.
- An unknown `/api` route through preview returned HTTP 404, rather than frontend HTML.
- Browser warning/error logs were empty. Backend tests: 9 passed with warnings as errors.
  Python lint/format checks passed; preview's automatic TypeScript/build step passed.
- Metadata access still does not prove generation credit, database write access, or indexing.
- Public Render deployment and the actual Docker image check remain outstanding.

### AI contribution and independent work

George supplied the credentials. Codex added preview configuration, restarted the managed local
API, verified read-only access, and drafted the walkthrough below. George's understanding
checklist remains unchecked until he completes it himself.

## Session 1 hands-on walkthrough

### 1. Start the Python process from the repository root

Both local processes may already be running from the assisted verification. Do not start a second
copy on the same port. When reproducing the setup from stopped processes, use two terminals.

In terminal A, from the repository root:

```powershell
uv sync --frozen
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Uvicorn is the HTTP server process. `app.main:app` identifies the FastAPI object inside
`backend/app/main.py`; `--app-dir backend` makes that Python package importable. The host binds
to this computer only. `--reload` restarts Python when watched source files change; manually
restart after editing `.env` rather than relying on the file watcher to see it.

During startup the lifespan function creates `Settings()` and one shared HTTPX `AsyncClient`.
Settings reads the root `.env` and environment variables; actual environment variables take
precedence. The HTTP client reuses connections and has a five-second timeout. On shutdown, the
context manager closes its connections.

### 2. Start the built frontend preview

In terminal B, also starting at the repository root:

```powershell
cd frontend
npm ci
npm run preview
```

`npm ci` installs locked dependencies and is mainly needed for a fresh checkout or a changed
lockfile. `prepreview` type-checks and builds React into `frontend/dist`; `preview` serves those
files on http://127.0.0.1:4173. Source edits require restarting preview so it rebuilds.
For live frontend editing, `npm run dev` instead uses Vite's development server on port 5173.

### 3. Follow one request through the code

```text
Browser: GET http://127.0.0.1:4173/api/health
  -> Vite proxy: GET http://127.0.0.1:8000/api/health
  -> FastAPI route: check_health(settings, shared_http_client)
  -> OpenAI model metadata + Qdrant collection metadata
  <- JSON report + HTTP 200 or 503
  <- React state update and rerender
```

Read `frontend/src/App.tsx`: `useEffect` calls `refresh` when the component mounts; the button
calls it again. `fetch('/api/health')` is a relative URL, so the browser contacts its own origin
on port 4173. `frontend/vite.config.ts` forwards only the `/api` path prefix to Python without
removing that prefix. This avoids needing browser CORS configuration for these local requests.

FastAPI's route in `backend/app/main.py` calls `check_health` in `backend/app/health.py`.
When the JSON returns, `setHealth(report)` stores it in React state and triggers rendering.
Loading, dependency problems, and inability to contact Python have separate UI behaviour.
`AbortController` cancels the in-flight browser request if the component is removed. It does
not necessarily cancel provider work Python has already begun.

In production there is no Vite proxy: FastAPI serves the compiled page and receives the API
request on the same origin. This preview step exercises the built frontend and local proxy,
not the Render deployment or Docker container.

### 4. Understand the two checks

| Check | Work performed | Meaning |
| --- | --- | --- |
| `/api/live` | No external work; returns 200 | Python can handle this route |
| `/api/health` | GET metadata for both OpenAI models and GET Qdrant collections | Configured read-only provider access passes now, or a dependency needs attention |

For each provider, `unconfigured` means required settings are absent; `reachable` means its
read-only HTTP checks passed; `unavailable` means connection failure, timeout, or a rejected
HTTP status. `asyncio.gather` waits for independent requests concurrently. No answer generation,
embedding creation, database writes, or token-consuming model inference occurs here.

Overall HTTP 200 means all access checks passed. HTTP 503 means a structured degraded report.
React explicitly accepts this expected 503 and displays the dependency statuses. If Python
cannot be contacted at all, React shows the API connection error instead. A 503 alone does
not mean the Python process crashed. Render checks `/api/live` so a provider outage does not
trigger needless process restarts.

### 5. Verify it yourself

1. Open http://127.0.0.1:4173 and check that both providers say Connected.
2. Open browser DevTools > Network, select Fetch/XHR, then click Check connections.
   Inspect `/api/health`: the browser URL uses port 4173; the response is JSON with `ready`;
   its request headers do not contain your provider keys. Those headers are added by Python
   only when making its separate external requests.
3. Open http://127.0.0.1:8000/docs, expand GET /api/health, and use Try it out > Execute.
   This exercises FastAPI directly and bypasses React and Vite.
4. From a terminal, compare both routes directly and through the proxy:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/live
Invoke-RestMethod http://127.0.0.1:4173/api/live
Invoke-RestMethod http://127.0.0.1:4173/api/health | ConvertTo-Json -Depth 5
```

5. Run the backend checks from the repository root:

```powershell
uv run pytest -W error
uv run ruff check backend
uv run ruff format --check backend
```

The tests substitute fake provider responses, so these commands do not test real credentials
and do not call the external APIs. They protect healthy, missing, rejected, and timed-out states.
The browser's Connected result is the separate real integration check.

6. As a failure exercise, stop the Python terminal with Ctrl+C but leave preview running.
   Click Check connections: the UI should say it could not check the API. Restart Python and
   click again to recover. A proxy error while Python is stopped is expected.
7. As a code exercise, change the visible connection button label in `App.tsx`, restart preview,
   and explain why restarting Python was unnecessary for that frontend-only edit.

### 6. Explain it back before Session 2

Write your own answers in the understanding section above:

- Which process serves the page on port 4173, and which process handles the API on port 8000?
- Why can the browser call `/api/health` without knowing the backend's port?
- Where are provider keys read, and which requests include them?
- Why can `/api/live` return 200 while `/api/health` returns 503?
- What important capabilities remain unproven even when both providers show Connected?

If any answer is unclear, trace that part again before adding ingestion or retrieval code.

## Session 2, checkpoint A: source records and evidence contracts

### Git history and working agreement

George explicitly authorized starting slice 2. The earlier understanding checklist remains his
to complete; starting this slice does not claim that he has answered those questions.

The remote initially had no `main`; the first pushed branch had become GitHub's default. We
established `main` at the existing planning commit, opened foundation PR #1, and rebase-merged it.
Main now contains one linear chain of commits, with no merge commit. Slice 2 starts on
`codex/dataset-fixtures` from that result. GitHub rebase merging changes commit hashes, so the
old foundation branch's hashes differ from the equivalent commits now on main.

### What changed and why

The dataset boundary now separates immutable source records from evaluation cases. Source records
contain a title, canonical text, content hash, provenance, and sentence locations. Evaluation
cases contain questions, expected answers/statuses, and labelled evidence. Strict models reject
unexpected fields, including accidental question/answer labels on a source record.

Normalize text with Unicode NFKC and whitespace collapse, then hash it with SHA-256. Derive a
stable UUID from that hash. Two occurrences of the same normalized passage therefore count once,
even under different titles. Distinct text under the same title remains distinct. The first
selected occurrence supplies provenance; duplicate occurrence counts are retained, not every
alternate occurrence's metadata. These immutable preparation IDs do not yet implement mutable
uploaded-document identities or revisions; that lifecycle belongs to slice 3.

Sentence IDs retain HotpotQA's original zero-based numbering, including gaps from empty sentences.
Character offsets refer to canonical text, not the raw Wikipedia page. A validator checks the
hash, identifier, and locations together. Normalization gives consistent identity, but is not
semantic near-duplicate detection.

### Alternatives and trade-offs

- Hashing filenames would count repeated passages multiple times. Text hashing avoids that but
  deliberately treats whitespace/compatibility Unicode differences as equivalent.
- Random UUIDs are useful for mutable user documents but do not identify repeated source content.
- A random sample would be less order-biased, but requires another sampling rule and often a
  larger scan. A fixed revision and deterministic source order are simpler for this deadline.
- HotpotQA provides native bridge/comparison questions and sentence evidence. RAGBench offers
  other domains, but would require different label handling. This benchmark is not a representative
  measure of all business investigations.
- The Datasets library supports pinned-revision streaming. Its PyArrow/Pandas dependencies are
  in the optional `data` group, rather than the deployed web application's runtime requirements.

### Verification and AI contribution

Six source-boundary tests cover normalized deduplication, changed content, sentence locations,
malformed context arrays, label separation, and native support extraction. They pass. The earlier
foundation suite also remains green. Before merging PR #1, deliberately inverting the readiness
condition caused its targeted test to fail; the original code was restored.

Codex drafted these models and tests and fetched the dataset documentation. George has not yet
completed independent verification of this slice. No embeddings or answer generation have run.

### My understanding (George writes this)

- [ ] I can distinguish a QA dataset row, a source passage, and a future retrieval chunk.
- [ ] I can explain why repeated source text does not increase the 50,000-record count.
- [ ] I can find one source's dataset revision and original sentence IDs.
- [ ] I can explain why the evaluation question and answer must stay out of corpus records.

> Pending George's review.

## Session 2, checkpoint B: corpus preparation and frozen evaluation

### What changed

Offline commands now freeze reference cases, prepare a corpus, verify it, and render a readable
question/evidence review sheet. Corpus output lives under ignored `data/prepared/`; small source
fixtures, reference labels, provenance, and a verification report are committed. Nothing has
been indexed into Qdrant or embedded yet. The web interface remains the connection page.

### Actual preparation results

The verified output contains 50,000 unique normalized HotpotQA passages and 24 fictional records:
50,024 source records total, before any chunking. Training selection consumed 5,457 QA rows and
skipped 4,313 repeated source occurrences. The final corpus is 86,321,736 bytes. Its SHA-256 is
`7fb92aae4a89727ca1d274d23ee25ba1dfafa052808fce75086f17c7c088c5eb`.

The frozen set contains 40 final cases (8 simple, 12 bridge, 8 comparison, 6 absent, 6 conflict)
and 8 development cases. There are 72 small source fixtures: 48 HotpotQA support passages and
24 fictional records. Every labelled document ID, original sentence ID, and quote matches a
canonical source in the full corpus. Reference correctness still needs George's review; data
integrity checks cannot establish that a question is unambiguous or every reference is complete.

The dataset library retried one Windows socket error while reading training data and completed.
Its unauthenticated-download and Windows cache/symlink notices did not prevent preparation.
No model inference or embedding charges were incurred by these preparation commands.

### Trace one bridge question

`final-bridge-01` asks which government position was held by the woman who played Corliss Archer
in Kiss and Tell. The first source, `Kiss and Tell (1945 film)`, sentence 0, identifies Shirley
Temple as the actress. The second, `Shirley Temple`, sentence 1, names Chief of Protocol among
her adult roles. The native HotpotQA answer is `Chief of Protocol`.

This is the future two-search mechanism: find the actress, then search for her government role.
It does not require a knowledge graph or multiple agents. The source also mentions ambassador
roles, which illustrates why a single benchmark reference may not exhaust all valid answers.
Review ambiguity before interpreting exact-match scores. This slice preserves the source label
without claiming it is the only defensible wording.

For `final-conflict-01`, two explicitly fictional reports give retry limits of 3 and 5 attempts
for the same service, case, and timestamp. Neither report has precedence. The expected status is
`conflicting_evidence`, not a guessed winner. For the missing-approver questions, the unique
fictional case has no approver recorded; evidence and gold answer are intentionally empty.

### Choices and alternatives

- Native HotpotQA labels make multi-document cases reproducible. Fictional cases provide clear
  absence/conflict conditions without claiming real incidents occurred.
- We seed required support passages before adding training-context distractors. This deliberately
  guarantees evidence is present; it measures retrieval/answering conditional on that membership,
  not unbiased coverage of arbitrary questions. The fixed source-order subset is order-biased.
- Questions and labels are separate from source JSONL. Copying a whole QA row into an index could
  retrieve the answer key instead of connecting evidence. Strict source models reject those fields.
- JSONL is inspectable and streamable before a database is introduced. SQLite could support local
  transactions, but would not establish the final cloud index and is unnecessary for this step.
- Frozen file hashes detect accidental edits; they are integrity checks, not proof of correct
  reference answers. LF attributes keep hashes stable across Windows and Unix checkouts.
- Development examples are available for later tuning. The final 40 stay fixed while choosing
  chunking settings. Small synthetic patterns and public benchmark facts limit generalization.
- Preparation refuses existing outputs and publishes a complete directory only after success.
  It restarts deterministically after failure; resumable embedding/index writes are slice 4 work.

### Reproduce and verify

Run from the repository root:

```powershell
uv run --group data python -m backend.app.dataset_cli verify
uv run python -m backend.app.dataset_cli review
uv run --group data pytest -W error
```

`verify` checks the existing full corpus without downloading or using model APIs. `review` builds
`docs/evaluation-fixtures.md` from the frozen labels without network access. To reproduce the
corpus in another directory, use `prepare --output data/reproduced`, followed by verification
and comparison of corpus hashes. Never overwrite the reference files to improve a score.

The automated suite currently has 25 passing tests. New cases protect normalized identity,
provenance, native evidence extraction, label leakage, deterministic output bytes, exact category
counts, missing gold documents, cross-split duplicates, tampered corpus/labels, partial output,
overwrite refusal, revision mismatch, and conflicts without a single gold answer.
Deliberately inverting the deduplication condition made its targeted test fail; the original
condition was restored. A separate fixture regeneration from the same pinned validation data
produced identical hashes for all three frozen JSONL files. An actual second `prepare` invocation
against the existing output was refused before any network download or file overwrite.

### My understanding (George writes this)

- [ ] I ran `verify` and inspected the real record counts and corpus hash.
- [ ] I traced the bridge example from question to two source sentences.
- [ ] I checked a simple, comparison, conflict, and absent case in the review sheet.
- [ ] I can explain what integrity checks prove and why gold correctness remains a human check.
- [ ] I can explain why 50,024 source records are not 50,024 vectors or retrieval chunks.
- [ ] I can explain the subset bias and why gold documents were deliberately included.

> Pending George's review. Do not mark reference review complete on his behalf.

### AI contribution and resume point

Codex drafted the source pipeline, fixtures, tests, review sheet, and documentation, downloaded
the public pinned data, and executed integrity checks. George's independent reference review
and explanation are pending. Review these artifacts before slice 3's document lifecycle work.
Public deployment remains an outstanding item from the first slice.

## Session 2 guided review: selection, identity, and evaluation

### Working branch and current verification

George requested working directly on main from now on. PR #2 was already rebase-merged when this
review began. Codex fetched the remote and fast-forwarded the local main branch; no history was
rewritten. Future verified changes go directly on main unless George requests another workflow.
The full corpus verifier and all 25 tests passed again on main. George's understanding and gold
reference review remain pending; neither is inferred from this walkthrough.

### Step 1: Distinguish three units of data

A HotpotQA row contains a question, answer, several context passages, and supporting-fact labels.
A source record is one of those passages, with its title and provenance. A retrieval chunk will
be a piece of a source record created later, in slice 4. We have 50,024 source records now, not
50,024 QA rows, chunks, embeddings, or indexed vectors.

Only context passages become corpus records. The question, answer, and support labels become
evaluation fixtures separately. This prevents the future search engine from retrieving its own
answer key. The originating QA record ID is retained as provenance, without copying its labels.

### Step 2: Follow selection in execution order

1. `dataset-selection.json` pins HotpotQA's `distractor` configuration to the immutable revision
   `1908d6afbbead072334abe2965f91bd2709910ab`.
2. The one-time fixture generator selects the first valid validation questions in source order:
   12 bridge and 8 comparison final cases, then 2 of each category for development. Multi-source
   cases must reference at least two distinct source documents. Skips would be recorded; none
   were needed for this selection.
3. The prepared-record map starts with 72 committed source fixtures: 48 native support passages
   plus 24 fictional records. Only the 48 native passages count toward the HotpotQA target.
4. Stream training rows in source order. Extract their context passages, normalize them, and add
   unseen content until the HotpotQA count is exactly 50,000. Thus 49,952 newly selected training
   passages join the 48 native seeds. Synthetic records are outside that quota.
5. Sort all 50,024 records by stable document ID and write JSONL, then record counts and hashes
   in the manifest. Publish the output directory only after its files are complete.

The actual run consumed 5,457 training rows and skipped 4,313 repeated passage occurrences.
The library streams the upstream data, but preparation retains the selected records in memory;
this is bounded local work, not constant-memory processing on the free web server.

Why this choice: a fixed revision and order are straightforward to reproduce. Random sampling
could reduce ordering bias but needs a fixed sampling rule/seed and potentially a wider scan.
Seeding evidence avoids confusing retrieval failure with an accidentally absent source. The cost
is a benchmark deliberately conditioned on evidence being present, rather than unbiased corpus
coverage. Both custom development and final native questions come from HotpotQA's validation
split; our evaluation split names are distinct from the upstream split names.

### Step 3: Trace deduplication with a real example

The following was executed against `normalize_text`, `content_hash`, and `document_id`:

```text
"  Payment\nrouter\tfailed. " -> "Payment router failed."
"Payment router failed."     -> "Payment router failed."
```

Both produce SHA-256 prefix `24d7906cc20f` and document ID
`5210b38e-c0ea-5a79-8498-0bddd59655bc`. `Payment router recovered.` instead produces prefix
`773913ce0f88` and ID `240cf7d5-7d41-5585-8b83-5d48b2a592ee`.

The pipeline first applies Unicode NFKC compatibility normalization, then collapses whitespace
and trims its ends. SHA-256 fingerprints the normalized text. A deterministic UUID derived from
that fingerprint is the lookup key in a dictionary. If the key is already present, increment the
duplicate counter and skip the occurrence; otherwise retain the record.

Titles are not part of the hash, so the same normalized passage under another title still counts
once. Different text under the same title remains separate. We do not lowercase or detect
paraphrases, so this is normalized exact deduplication, not semantic deduplication. The first
retained occurrence supplies provenance; retaining every alternate occurrence is not implemented.
These content IDs describe immutable prepared records, not yet mutable upload identities.

Alternative: filename hashes would miss the same text in differently named files. Random IDs
would not expose repeated content. Semantic similarity could find paraphrases but introduces
thresholds, model work, and a risk of merging distinct evidence, including contradictory versions.

### Step 4: Understand the fixtures as test inputs, not test results

Each evaluation case stores a question, category, expected status, reference answer when one
exists, and evidence labels. A label names a document ID, original zero-based sentence ID, and
exact normalized quote. Sources retain canonical character offsets, so the quote can be checked
against stored text. These offsets are not positions in today's live Wikipedia page.

| Category | Final | Development | Expected behaviour |
| --- | ---: | ---: | --- |
| Simple | 8 | 2 | Return a recorded fictional recovery time |
| Bridge | 12 | 2 | Link native evidence across documents |
| Comparison | 8 | 2 | Compare native evidence from multiple documents |
| Unanswerable | 6 | 1 | Report insufficient evidence for an unrecorded approver |
| Conflict | 6 | 1 | Show incompatible fictional reports without choosing a winner |

The 8 development questions support future configuration choices. Keep the 40 final questions
fixed while tuning. Distinct question IDs/text are enforced across those splits; background
documents can overlap. Passing the 25 Python tests means the preparation/validation code passes
its tests. It does not mean the investigation engine answered 25 questions: generation and the
evaluation runner do not exist yet.

Fixture hashes detect accidental drift against the manifest. They do not prove that a reference
answer is true, complete, or the only valid answer. A legitimate reference correction should be
explicit and versioned before evaluation, rather than silently tailored to a model's output.

### Step 5: Inspect one example of each important behaviour

- `final-bridge-01`: film passage identifies Shirley Temple; her biography names Chief of
  Protocol. Read both sources. The biography also names ambassador roles, so discuss whether
  other answers should count before later exact-match grading.
- `final-comparison-01`: the Scott Derrickson and Ed Wood passages each identify American
  nationality. Both sources are needed to justify the reference answer `yes`.
- `final-conflict-01`: two fictional reports say 3 versus 5 attempts for the same retry setting,
  service, and timestamp. Neither has priority; the expected status is conflicting evidence.
- `final-unanswerable-01`: a fictional incident has a documented recovery time but no recorded
  approver. A valid response should abstain, not guess an employee name.

### Step 6: Verify it yourself from the repository root

```powershell
git branch --show-current
uv run python -m backend.app.dataset_cli verify
uv run --group data pytest -W error
```

Expected: main; verified true; 50,000 HotpotQA passages; 24 fictional records; 40 final and 8
development cases; corpus hash beginning `7fb92aae4a89`; 25 passing tests. These commands do not
call model inference APIs or require rebuilding the corpus.

Inspect one source record and the first final question without reading the entire 86 MB file:

```powershell
Get-Content data/prepared/corpus.jsonl -TotalCount 1 | ConvertFrom-Json | Format-List
Get-Content fixtures/evaluation/final.jsonl -TotalCount 1 | ConvertFrom-Json | Format-List
```

Regenerate/open the readable review sheet if useful:

```powershell
uv run python -m backend.app.dataset_cli review
```

Check the four cases above against their quotes and sentence IDs. Confirm that a source record
has no question, gold answer, or supporting-fact label fields. The schema rejects those fields;
the original QA ID in provenance is not an answer label. The verifier checks all records, not
only the displayed example.

Optional reproducibility exercise, if you want another download/scan and another 86 MB output:

```powershell
uv run --group data python -m backend.app.dataset_cli prepare --output data/reproduced
uv run python -m backend.app.dataset_cli verify --output data/reproduced
```

Use a fresh output directory; preparation refuses existing outputs. Compare its corpus hash
with the existing one. A prior full-corpus run, the small deterministic test, and a separate
matching fixture regeneration are already recorded; a second full-corpus reproduction is optional.

### Your checkpoint before the next slice

Explain in your own words: why 5,457 rows can produce 50,000 unique passages; why a changed retry
value must survive deduplication; why gold labels stay outside the corpus; why a valid quote is
not proof of an unambiguous answer; and what the 8/40 split protects. Record your findings or
questions in your understanding section. Those checkboxes remain yours to complete.

Codex drafted this walkthrough and re-ran the verification. No ingestion, chunking, embedding,
or investigation features were added during this review.

## Session 3, checkpoint A: parsing files into canonical text

### What changed and why

Working directly on main, moved the existing canonical normalization/hash helpers into `app/text.py`
so dataset preparation and runtime uploads share one implementation. The corpus hash remains
unchanged. Added parsers for PDF, DOCX, and UTF-8 TXT, with canonical text locations and selected
title/author metadata. Filenames are display metadata, never filesystem destinations.

PDF locations are one-based page numbers. DOCX locations identify body paragraphs and table rows.
PDF metadata also reports page count and any pages without extractable text, making partial
extraction visible when a document mixes readable text and scanned or blank pages.
Table cells are flattened as text, including nested tables within bounded depth. TXT paragraphs
are separated by blank lines. Character offsets refer to normalized text, not original binary
bytes. PDF reading order and Word tracked changes/headers are not guaranteed layout fidelity.

Pypdf and python-docx are explicit, format-specific dependencies. A universal conversion service
could cover more formats and OCR, but adds deployment/runtime requirements. Image-only and
encrypted PDFs receive clear errors. File extensions, signatures, encoding, decoded PDF streams,
DOCX ZIP expansion, text length, page count, and block count are bounded. Parsing runs off the
event loop, with one parse slot per app process. These are bounded demo parsers, not OS-isolated
workers for arbitrary hostile files.

### Verification and alternatives

Thirteen parser tests cover all formats, cross-format normalized identity, exact locations,
DOCX tables, metadata, malformed/empty/encrypted/textless inputs, UTF-8 Georgian text, size limits,
archive expansion, and safe filename handling. A Windows test-runner issue exposed automatic
test IDs expanding a 5 MB input into a path; short explicit IDs fixed the harness. It was not a
parser failure. Dataset verification and the original tests still pass after sharing helpers.

Exact normalization deduplicates identical extracted text; different reading order or paraphrases
remain distinct. OCR and semantic deduplication are later possibilities, not hidden capabilities.

Codex drafted these changes and tests. George's hands-on review remains pending.

## Session 3, checkpoint B: durable document lifecycle

### What changed and why

POST/GET/PUT/DELETE document routes now store canonical text and metadata in Qdrant, not the
ephemeral web filesystem. Two payload-only collections hold stable document manifests and
immutable parsed revisions. We reuse HTTPX for the small REST adapter; a Qdrant SDK would add
convenient typed operations, but also another dependency. Necessary payload indexes were created
for Cloud strict-mode filters. Read requests do not create collections.

A document has a stable management UUID. Its content fingerprint supports exact deduplication;
its revision UUID identifies one parsed snapshot. Uploading the same normalized text in another
format returns the existing active document, preserving the first filename and locations.
Replacing with changed text preserves the document ID and changes the revision ID. Replacing
with another active document's text is rejected with 409; unchanged text is a duplicate/no-op.

Replacement writes the complete parsed revision first, then switches one manifest point. If
preparation or the pointer write fails before commit, the old revision remains active. A timeout
can mean the pointer write actually succeeded; return 503 and reload state rather than deleting
the prepared revision. Orphaned, superseded, and deleted revisions are never eligible unless an
active manifest points to them. There is no physical garbage collection in this version.

Deletion writes a tombstone, so fresh app instances and future retrieval can still identify the
document as deleted. A SQL transaction could provide stronger cross-process coordination, but
would add a second database. This app serializes mutations with a process-local lock and requires
the previous revision's quoted ETag in If-Match for replacement/deletion. Missing preconditions
return 428; stale ones return 412. The design supports the planned single process, not multiple
workers/replicas without a stronger concurrency mechanism.

### Authentication, request limits, and current indexing boundary

The existing local DEMO_ADMIN_TOKEN was preserved. Mutations require its bearer header before
multipart parsing begins. The entire streamed request is bounded, including requests without
Content-Length; file bytes have their own 5 MB limit. Missing admin configuration disables writes.
Provider keys stay server-side. Public GET routes expose the shared demo corpus's extracted text
and selected metadata; this is not private per-user storage.

Parsed documents report `index_status: pending`. No chunks, vectors, or embeddings were created.
Slice 4 must insert revision-scoped index preparation before pointer activation and call the
existing active-revision gate after retrieval. Tests exercise that gate with candidate pairs;
they do not pretend an actual semantic search was performed. The 50,024-record dataset remains
local and its frozen fixture hashes remain unchanged.

### Verified results

- 56 offline tests pass with warnings treated as errors. They include parser boundaries, early
  authentication, whole-body and file limits, cross-format duplicates, cursor pagination, stale
  edits, concurrent edits, rejected replacement content, uncommitted revisions, and ambiguous
  write timeouts. An HTTP-level fake exercises actual Qdrant request shapes without credentials.
  Deliberately inverting the active/deleted revision gate failed its lifecycle test; the original
  condition was restored before the full suite passed again.
- Real Qdrant verification uploaded a PDF, recognized DOCX/TXT duplicates, inspected page locations,
  replaced text, and rejected a stale delete. New app instances read the replacement and continued
  to hide the document after deletion. The sample was soft-deleted; its tombstone and revisions
  remain. This proves actual provider write/read behaviour, separately from the mock tests.
- No generation/embedding calls occurred. The report is `docs/ingestion-verification.json`.
- The interactive `/docs` page shows all five management operations and a real upload file picker.
  Browser warning/error logs were empty during that check. React management UI remains slice 7.
- PDF/DOCX fixtures are explicitly binary in Git attributes, preventing line-ending conversion
  from corrupting PDF cross-reference offsets on Windows checkouts.

### Walk through it yourself

Use `docs/document-management.md` and `fixtures/uploads/`. In Swagger, authorize with your local
admin token, upload the PDF, upload its two equivalent formats, GET the document and its ETag,
replace using `incident-updated.txt`, reject a stale edit, then delete with the current ETag.
The supplied updated file changes recovery time from 12 to 8 minutes. Re-read after restarting
Python. The reproducible real-provider smoke command is:

```powershell
uv run python scripts/verify_document_management.py
```

It touches only newly created fictional sample data and stops before modifying a pre-existing
matching document. The offline suite is `uv run --group data pytest -W error`.

### My understanding (George writes this)

- [ ] I uploaded all three formats and inspected locations and metadata.
- [ ] I can distinguish document identity, revision identity, and content hash.
- [ ] I can explain why a replacement is staged before its pointer changes.
- [ ] I reproduced missing/stale If-Match errors and understand which edit they protect.
- [ ] I confirmed replacement/deletion survive a fresh app instance.
- [ ] I understand tombstones retain data and are not physical erasure.
- [ ] I can explain why parsed text is still pending indexing and how slice 4 will add it.

> Pending George's review. No understanding checkbox is completed on his behalf.

### AI contribution and resume point

Codex drafted and verified the implementation, tests, fixtures, and documentation. The walkthrough
and independent explanation are George's checkpoint before slice 4. Known limits are no OCR or
original binary downloads, imperfect complex document layout, process-local mutation locking,
no revision garbage collection, and no OS-level parser sandbox. Public Render deployment remains
pending. Future verified work continues directly on main as George requested.

## Template for later sessions

### What changed
### Why
### Alternatives and drawbacks
### Trace a concrete input
### Verification, including failures
### My understanding (George writes this)
### AI contribution and independent changes
### Resume point

## Session 4 — checkpoint A: chunk boundaries, fusion, and provider costs

**What changed:** `backend/app/retrieval/chunking.py` implements fixed 256-token windows
with 40-token overlap and sentence groups targeting 256 tokens with one-sentence overlap.
Oversized sentences split into bounded fragments. `fusion.py` combines ranks with
`1 / (60 + rank)`, deduplicates each list, breaks ties by chunk ID, and caps evidence at
eight chunks / two per document. `providers.py` adds bounded REST calls, a SQLite embedding
cache, and a conservative local usage ledger.

**Why:** Keep token limits and rank fusion explicit enough to inspect without an orchestration
framework. Character offsets point back to canonical source text. BPE tokens sometimes end
inside a Unicode character; windows cut only at shared token/character boundaries, so overlap
can differ slightly from 40 tokens for such text. Sentence overlap is dropped when retaining
it would prevent new content from fitting; oversized sentence overlap uses a fragment.

**Alternative:** Character windows are simpler but do not enforce model token limits.
A local sparse embedding model adds runtime downloads and memory. Raw score addition mixes
incompatible score scales. An in-memory cache loses progress on restart.

**Mechanism:** A chunk ranked second in dense and first in keyword results scores
`1/62 + 1/61 = 0.032522...`. That is a relevance ranking score, not answer confidence.
Embedding cache keys include model, dimensions, and exact chunk text; identical texts in
both configurations share their embedding while retaining separate chunk identities.

**Verification:** Wrote failing tests before the implementations; eight algorithm/provider
tests now pass. Tests cover Unicode coverage, sentence splitting/overlap, rank fusion,
diversity, persistent cache reuse, budget rejection, malformed vectors, and provider failures.
No paid calls at this checkpoint. `tiktoken` is the only added runtime dependency.

**My understanding (George):** [ ] Trace one window; [ ] calculate the fusion example;
[ ] explain why a timeout keeps its cost reservation. Not yet independently reviewed.

**AI contribution:** Codex drafted implementation/tests and ran them. George's verification
and explanations remain pending. No final evaluation questions were run.

**Resume point:** Add Qdrant dense/BM25 collections, stage chunks before revision activation,
and build a resumable local importer. Then measure 1,000 source records before bulk work.

## Session 4 — checkpoint B: persistent hybrid indexes and resumable import

**What changed:** Two versioned Qdrant chunk collections hold named `dense` vectors and
BM25 sparse vectors. `ChunkIndex.prepare` stages both before document activation.
`SearchService` requests 30 candidates per method, checks current manifests, and applies
custom fusion/diversity. Chunks carry canonical offsets and page/paragraph or original
HotpotQA sentence IDs; canonical text stays in the revision collection.

**Why:** Separate collections let us compare A/B without changing models or retrieval settings.
Qdrant's built-in `qdrant/bm25` computes sparse term weights; its IDF modifier gives rarer
terms more weight. It avoids loading a sparse model in Render's small process. Collection
names include a profile fingerprint so different embedding dimensions/models do not mix.

**Alternative:** One collection with a strategy filter saves a collection, but mixes BM25
corpus statistics between configurations. A distributed transaction is unnecessary here:
stage immutable data, activate one pointer, and reject inactive pairs at retrieval time.

**Mechanism:** A replacement stores canonical revision R2, writes its A/B chunks, then switches
the manifest from R1 to R2. If the last write fails, R2 chunks remain invisible. After deletion,
either revision fails the active gate. Old/staged chunks remain physically stored, so they can
occupy top-30 candidate slots and affect BM25 IDF; future garbage collection/overfetch can
improve recall. Filtering guarantees exclusion, not perfect candidate recall.

**Verification:** HTTP-level tests exercise both index shapes, original source locations,
replacement/deletion, failed chunk staging, failed activation, and resume without re-embedding.
The fake checks request contracts; a real-cloud pilot will separately verify provider support.
The importer never resurrects a tombstone or overwrites a modified document on resume.

**My understanding (George):** [ ] Explain staged versus active data; [ ] identify dense,
BM25 and fusion responsibilities; [ ] explain why IDF and old chunks can affect recall.

**AI contribution:** Codex drafted and tested this checkpoint; George's review remains pending.

**Resume point:** Finish the local corpus resource estimate, pilot 1,000 records, record actual
throughput and costs, then begin the full resumable run if it fits the remaining target.
Stop the web process while importing: both are writers and this version has no distributed lock.

### Session 4 — pilot measurement and a real interruption

The full no-API scan measured 50,024 records, A=52,246 chunks / 6,148,592 tokens,
B=52,307 chunks / 6,141,058 tokens. At $0.02 per million embedding tokens, their
combined estimate before reuse is $0.245793. Dense float32 vectors alone total
160,593,408 bytes; payloads, BM25, HNSW and database overhead are additional.
See `docs/index-estimate.json`; prices checked against the OpenAI embedding model page.

The first 1,000-record real-cloud pilot completed in 184.732 seconds (5.41 records/sec),
wrote 1,042 A / 1,043 B chunks, and used 135,273 paid embedding tokens ($0.00270546).
A linear projection at that initial rate is about 2.6 hours for the full corpus. This is
an estimate, not a deadline guarantee; free-tier load, network and batch sizes matter.
Most short sources produce identical A/B chunks, so the shared embedding cache materially
reduces cost. That does not make the chunking comparison invalid: different long-source
boundaries still produce different candidates, and both indexes stay independent.

A later larger-batch run lost a Qdrant connection after 1,792 active records. It stopped
before activating the incomplete batch. A resume reached 2,000 in 14.662 seconds, activating
208 and skipping 1,792, with **zero additional embedding calls**: the interrupted batch's
embeddings had already been cached. Reports preserve both observations. This is actual
failure/recovery evidence rather than a simulated success claim.

Optimization: deduplicate texts across both configurations before embedding, request compact
base64 float32 embeddings (also used by OpenAI's Python client), batch local cache reads,
close SQLite connections explicitly, and allow two concurrent idempotent chunk writes.
The local CLI retries a failed storage batch at most twice; model requests are never
silently retried. Larger batches save round trips but increase per-request memory and network
size. The app's canonical revision is still activated only after both configurations settle.
George has not yet independently reproduced this run or reviewed these decisions.

## Session 5 — first validated cited answer

**What changed:** `POST /api/investigations` runs one hybrid search and one structured Responses
API generation. The model returns atomic claims with exact quotes and evidence IDs. The server
constructs answer text from those validated claims. It returns active source offsets, source
locations, a search trace, model/profile/prompt settings, latency, and generation usage.

**Why:** A first end-to-end path makes it possible to inspect what the model actually received
before introducing a tool loop. The trace exposes searches and evidence, never private model
reasoning. Claims require citations; unknown IDs, invented quotes, invalid status combinations,
and uncited claims fail with HTTP 502. Provider errors also remain errors, never abstention.

**Alternative:** Free-form prose with citation-looking strings is easier to prompt, but makes
it harder to validate every returned claim. Another LLM judge could check semantic entailment,
but adds cost, latency, and another fallible model; semantic citation accuracy stays an explicit
evaluation/manual-review responsibility. Exact quote validity alone does not prove support.

**Mechanism:** On the real development question about NOVA-DEVELOPMENT-01, hybrid search gave
E1 to the relevant fictional incident source. The model returned its 11-minute recovery claim
and a literal supporting quote. The server checked that quote against E1, rechecked active
revision eligibility after generation, then displayed the claim with `[E1]`.

**Verification:** `uv run python scripts/verify_first_answer.py` returned HTTP 200, answered,
11 minutes, 4,915 ms, 1,038 input / 79 output generation tokens, estimated generation $0.001134.
The script fetched each cited canonical document again and verified revision IDs and chunk
character offsets. Raw trace/context evidence is in ignored `artifacts/first-cited-answer.json`;
a compact committed report is `docs/first-answer-verification.json`. This checks one development
example; it is not a final evaluation or proof of general factual accuracy.

Reliability limits: one generation call, no automatic paid retries, 1,200 output tokens,
8,000 input-context tokens, eight evidence chunks, 90-second whole-workflow timeout. A global
one-process limit permits six investigations per minute and one concurrent investigation.
The local ledger defaults to $4.50 to leave contingency within the $5 target. Its file/cache
is local and can disappear on Render restart; it is not an account-wide hard spending cap.
Prices must be updated with model changes. A provider refusal/incomplete response becomes 502.
If evidence is deleted/replaced during generation the result becomes 409 instead of showing
an outdated answer. Empty eligible evidence skips generation and returns insufficient_evidence.

**My understanding (George):** [ ] Open the raw trace; [ ] locate the exact model context;
[ ] follow E1 to canonical source text; [ ] distinguish citation integrity from semantic support;
[ ] explain why a provider failure differs from missing evidence. All remain pending.

**AI contribution:** Codex drafted the service, tests, smoke script, and documentation and ran
them with configured providers. George has not yet independently reviewed the implementation.
No final question was sent to a model. The UI remains the foundation screen until slice 7.

**Resume point:** Review slices 4/5 using `docs/retrieval-and-first-answer.md`. Slice 6 will
introduce the validated `search_documents` tool and bounded entity-follow-up retrieval;
this checkpoint deliberately reports `workflow: single_search_v1`.

### Slices 4/5 — final review and background run

The full import was launched locally as a hidden background Python worker after the pilots and
fixture-source import; progress is in `artifacts/index-full.json` / `.log`, errors in
`artifacts/index-full.error.log`, and its worker ID in `artifacts/index-full.pid`. At this entry
it has passed 5,000 source rows; **the complete cloud corpus is not yet claimed**. It continues
independently while the machine stays awake. The walkthrough documents inspection, pause,
resume, and stopping the web writer during imports. The committed local source corpus hash
and frozen fixtures were not changed.

Final self-review covered correctness, module boundaries, input/secret handling, bounded calls,
query and storage contracts, memory, and explanation quality. The quote-membership condition
was deliberately inverted: the focused citation suite failed, then passed after restoration.
This checks that the tests can detect a broken validator, rather than merely execute it.
The implementation suite has 83 passing tests with warnings treated as errors; Ruff checks pass.
A real cloud pilot/recovery and a real cited-answer smoke check complement the HTTP-level fakes.
Docker/Render/public deployment are still unverified; no claim of a deployed application is made.
George's independent learning checkboxes remain unchecked. Slice 6 has not been started.

## Session 6 — checkpoint A: tool-calling provider boundary

**What changed:** Added a real Responses API function-calling request alongside structured
answer generation. The first planning request requires one tool call; the second can request
follow-up searches. Both use the same conservative usage ledger, sanitized provider errors,
600-token planning output caps, and no automatic paid retries. Refused, incomplete, malformed,
or invalid-usage responses fail explicitly instead of masquerading as missing evidence.

**Why:** The model proposes queries; application code remains responsible for validation,
execution, and limits. Reusing the existing REST/usage boundary keeps credentials server-side
and accounts for planning cost as well as final generation.

**Alternative:** A framework-managed agent loop would save some plumbing but add abstractions
and make the two-round/three-search rule less visible. JSON describing hypothetical searches
without actual function calls would not demonstrate the assignment's tool-calling requirement.

**Mechanism:** The API receives a strict `search_documents` function schema. A returned
`function_call` has a call ID, name, and JSON arguments. Python will execute the approved search
and return a `function_call_output` with the same call ID. That evidence becomes the next
planning request's context; no hidden reasoning is exposed in the public trace.

**Verification:** Five new provider tests were red before implementation. They now verify tool
request shape, usage recording, refused/incomplete responses and failure without retries.
Existing first-answer and embedding tests also remain green. No new paid call yet.

**My understanding (George):** [ ] Explain a model function request versus Python execution;
[ ] explain why strict JSON schema does not replace server validation. Review pending.

**AI contribution:** Codex drafted and ran this checkpoint; no independent George verification
is inferred. **Resume point:** Implement the host's bounded tool dispatcher and evidence pool.

The previous background run completed in 1,987.588 seconds, processing all 50,024 prepared rows.
It activated 47,953 and skipped 2,071 already imported sources; a separate read-only exact Qdrant
count now confirms **50,024 active documents**. The ledger after the bulk run recorded estimated
actual API cost $0.138972. `docs/index-full.json` preserves that run; cost includes prior calls,
not only its newly activated rows. Full corpus audit/evaluation and deployment remain later work.

### Session 6 — checkpoint B: bounded dispatcher and evidence identity

`SearchTools` validates the complete model-requested batch before executing it. It accepts only
`search_documents`, rejects extra/invalid arguments, enforces one initial search, at most two
rounds / three requested searches, and rejects reused call IDs. Duplicate normalized queries
reuse a prior result instead of spending another embedding/search call. Follow-up arguments
name an earlier evidence ID and an exact entity from that source; the query must include it.
This checks grounding of the query, not whether its inferred relationship is true.

Search-local evidence IDs are reassigned into one request-wide namespace, so E1 never changes
meaning across rounds. Final context merges query rankings with RRF and preserves a grounded
bridge source plus the top result of its follow-up, retaining the eight-chunk / two-per-document
cap. This small anchor reservation prevents repeated first-hop hits from crowding out the bridge.
Alternative: simply sum result ranks and trust all supporting sources to survive; simpler, but
can discard the very first document needed to justify a two-document answer.

Thirteen new dispatcher tests cover actual result replay, stable IDs, entity grounding, search
and round limits, forbidden tool names, malformed/extra/blank/long arguments, duplicate IDs,
and deduplicated query execution. These tests began red before the dispatcher existed.
George's hands-on explanation remains pending. Resume: connect this tested dispatcher to the
investigation endpoint and exercise the two-round path, conflicts, abstention, and failures.

### Session 6 — checkpoint C: real multi-step workflow and development failures

**What changed:** The investigation endpoint now executes a real `search_documents` function
loop. One initial search is followed, when evidence exists, by one required verification round
with one or two searches. The host permits at most two rounds, three tool requests/searches,
three LLM requests (two planning plus synthesis), and three query embedding requests. Duplicate
queries reuse their results. Empty first-round evidence ends early without synthesis. All calls
share a 90-second deadline, existing six-per-minute / one-concurrent-request demo limits,
input-context/payload limits, output limits, and local cost reservations. The response records
planning, generation, and query embedding usage separately, including cache hits and total cost.

**Why / final decision:** The initial adaptive planner could say ready too early. In a real
Egeberg development run it identified the Nixon administration but the final answer supplied
presidential years using an Egeberg quote that did not establish those years. Citation integrity
alone did not catch semantic misuse. We therefore require a second verification search when
there is evidence. This costs an extra retrieval for simple questions; the alternative adaptive
stop is cheaper but was less reliable in observed development checks. It still does not prove
semantic correctness. Independent labelled citation review remains necessary in slice 8.

**Quote decision and observed failures:** Early generation inserted an editorial ellipsis into
an otherwise relevant quotation, and exact-substring validation correctly rejected it. Stronger
prompt wording alone did not reliably prevent this. A schema enum containing literal quotations
then hit a real provider HTTP 400 `invalid_json_schema` for double quotation marks in an enum
string. We replaced literal-quote generation with **quote ID selection**: Python offers exact
chunk/fragment and sentence excerpts as context, the model chooses Q IDs, Python checks each
Q ID's association with its E ID, resolves the original string, and checks it against source text.
Only short ASCII IDs enter schema enums. Quotes containing quotation marks remain intact in
context and output. Tiny sources such as `Paris` can now be quoted; an arbitrary eight-character
minimum did not establish support and could create an empty quote catalogue for valid short text.

The catalogue includes complete <=1,000-character fragments plus up to 16 choices per source
(or enough to retain every fragment). Shorter sentence choices improve readability. Its extra
context increases input tokens; selecting IDs reduces generated output and avoids transcription
errors. The source text, IDs, and exact excerpts are verifiable, but entailment is still a model
and evaluation responsibility. The public response retains literal `citations[].quote` strings.

Provider HTTP 503 failures were also observed during development and returned sanitized 502s.
They did not become abstentions or trigger automatic paid retries. Manual diagnostic attempts
are included in the local ledger; they are not hidden or presented as a perfect first run.
The final prompt version is `bounded_tools_quote_ids_v1`; final evaluation questions were untouched.

**Real mechanism and verification:** `uv run python scripts/verify_multistep.py` passed all four
**development** cases. It verified known answers/statuses, literal quotes, canonical chunk offsets,
active revisions, both labelled supporting documents for bridges, both conflict sources, and
an actual evidence-grounded entity follow-up. The committed `docs/multistep-verification.json`
contains the observed queries, usage, model/prompt settings and citation checks.

- Vermont soccer -> America East Conference -> North Atlantic Conference, with both documents cited.
- Roger O. Egeberg -> `Nixon administration` discovered in E1 -> Richard Nixon's 1969–1974 presidency,
  citing the Egeberg source (E1) and newly retrieved Nixon source (E9). E IDs stay stable; E2–E8
  were other first-round candidates, so a new source can legitimately be E9.
- Fictional retry reports preserved 3 attempts and 5 attempts as conflicting_evidence.
- Missing rollback approver returned insufficient_evidence with no factual claims.
- An isolated HTTP fake demonstrated a provider failure returning 502, with no real failed request
  required for that probe. Future probes use a separate local ledger, not the real spending ledger.

Observed latencies were 9,840 / 5,525 / 7,044 / 6,727 ms. The four successful questions' total
estimated API cost was $0.02102288. The ledger after the run recorded estimated known usage
$0.19985242 and conservative reservations $0.44259367, including prior indexing and diagnostics;
uncertain/failed calls keep reservations. These are application estimates, not an invoice or
account-wide spending cap. The corpus was not re-embedded for this slice.

**Review:** Unit/integration tests cover max-three requests, max-two rounds, full-batch validation
before side effects, grounded entities, stable IDs, global evidence caps, malformed/refused provider
outputs, source/quote-ID mismatches, schema/context limits, budget rejection before network,
provider/storage errors, concurrency/rate limits, evidence changing mid-answer, and deadlines.
Deliberately removing the search-budget guard made the over-budget test fail; restoration passes.
This confirms the test detects that specific missing safety condition.

**My understanding (George):** [ ] Trace E1 -> second query -> E9; [ ] explain why required
verification was chosen; [ ] follow Q IDs to literal source strings in the saved context/draft;
[ ] inspect both conflict sources; [ ] distinguish absence, model failure, and semantic misuse.
These remain unchecked. **AI contribution:** Codex implemented, diagnosed, tested, and documented
this work; George has not yet independently verified it. **Resume point:** Follow
`docs/multi-step-investigation.md`; begin slice 7 only when George requests it.

Final slice-6 verification: **120 tests pass** with warnings treated as errors; Ruff lint and
format checks pass. Final self-review also hardened malformed provider message handling and
ensured recorded reservations never fall below known returned usage cost. The successful
four-case report was captured before these defensive changes; model prompts/tool behavior
were unchanged by them. The frozen final fixtures and prepared corpus were not modified.

## Session 7 — checkpoint A: React workflows and API boundaries

**What changed:** Added Investigate/Documents views, a typed same-origin API client, paginated
source lists, in-memory admin access, file upload/dedup feedback, source inspection, ETag-based
replacement/deletion, cited claim/status rendering, and expandable search traces. The shared
native dialog shows retrieved evidence separately from current canonical text. The existing
quiet green/neutral palette and compact type hierarchy were retained; no UI framework was added.

**Why:** Two views and a shared source viewer keep state ownership visible. React state is enough
at this size; routing/global stores would add concepts without solving an immediate requirement.
Both views stay mounted so navigating does not discard a question, result or entered token.
The token is masked and held in memory, never local/session storage; server validation remains
authoritative. No credentials are compiled into the frontend. Browser FormData supplies its own
multipart boundary, and edits copy the server's exact quoted ETag into If-Match.

**Mechanism:** Upload -> server metadata -> open source by returned ID, even if that UUID is not
on page one of the large corpus. A quick-access last-upload link persists across views. A cited
claim opens an E-ID snapshot, then fetches the canonical source; changed revisions are labelled
and deleted sources retain only the retrieved snapshot. Text renders as React text, not HTML.
Python offsets count Unicode code points, so highlight slicing uses Array.from instead of raw
UTF-16 string indices; a Georgian/emoji test verifies the difference.

**Alternatives:** Optimistic deletion would feel faster but could hide a failed write. Persisting
the admin token would avoid re-entry but retain a credential after the page closes. Rendering
model text as HTML/Markdown introduces avoidable injection risks. Cursor pagination avoids loading
50,024 sources into the browser but does not provide title search or a total count in this slice.

**Verification:** Frontend build/typecheck and four Node unit tests pass. Two Playwright browser
checks pass against the compiled Vite preview and real FastAPI routes with shared HTTP provider
fakes: upload -> ask -> citation -> trace -> delete, plus duplicate upload and replacement.
The answered desktop screen had no axe violations; page runtime errors were empty. These checks
prove integration, not model answer quality. A separate live-provider UI smoke is still pending.
The test transport was extracted from existing backend integration tests instead of duplicated;
those 15 relevant backend tests remain green. Test-only reset/header markers live in browser_app,
which is never registered on the production FastAPI app.

**My understanding (George):** [ ] Trace fetch/FormData/If-Match; [ ] explain memory state versus
server state; [ ] compare a citation snapshot to a changed current revision. Not independently
verified yet. **AI contribution:** Codex drafted components, styles, helpers and tests and ran them.
**Resume point:** Exercise stale writes, errors, pagination, safe text, keyboard/mobile access,
then run one bounded live-provider browser smoke and document the final walkthrough.

## Session 7 — checkpoint B: integration failures and completed verification

**What changed:** Completed stale-write reloads, source snapshot warnings, last-upload access,
loading/empty/error states, safe text rendering, keyboard focus restoration, mobile layouts,
question validation, observable query adjustments, test tooling and the walkthrough in
`docs/react-workflows.md`. Session 7's implementation boxes are checked; George's are not.

**Why and alternatives:** An HTTP failure must not look like an insufficient-evidence answer.
Client validation now explicitly says nothing was submitted; provider/rate-limit errors describe
the failure and never automatically repeat a paid request. A native dialog supplies focus
containment and Escape behavior without a modal library. A new deletion-focus test exposed a
race: requestAnimationFrame could focus the background while the modal trap was still active.
Restoring focus on the native close event fixes the mechanism, with Documents as the fallback
when the source's opener disappears. Timed delays would only hide this timing dependency.

**Live failure and fix:** Initial paid browser attempts displayed HTTP 502 correctly, but did
not complete the investigation. A diagnostic with a uniquely labelled fictional source isolated
the cause: the model supplied an entity found literally in E1 while its query used the case ID
and recovery-time wording without that exact entity. The old cross-field guard rejected it.
The server now prepends a source-verified entity when necessary; entities still require a valid
prior evidence ID and literal source match. The adjusted query must remain <=500 characters,
and the whole batch is validated before any search. The trace records proposed and executed
queries. Two tests protect successful grounding and rejection of an oversized adjusted query.
Rejecting every omitted entity was brittle; accepting unverified entities would lose the
evidence constraint. This fix preserves grounding and call limits without another model retry.

**Concrete mechanism:** A unique UI case source documents recovery after 17 minutes. Upload
returns its document/revision; the question retrieves it, makes a verified follow-up search,
and returns an answered claim citing that actual source. Opening the citation verifies a
canonical highlight. Deleting only that newly created source returns 204; GET then returns 404.
The existing 50,024-source corpus was not replaced or re-embedded. Diagnostic/smoke sources
were cleaned up through normal deletion; tombstones/history remain by design.

**Verification:** The successful real-provider browser run returned 17 minutes in **6,494 ms**.
Its investigation estimate was **$0.00448099**; upload plus question added **$0.00448239** to
known ledger usage. The saved ledger after the run shows **$0.20992536** estimated known usage
and **$0.48744711** conservative reservations, including earlier failed/diagnostic work.
Reservations for uncertain calls are retained. These are application estimates, not an invoice
or account-wide cap. See `docs/browser-live-verification.json`; final fixtures were untouched.

The final isolated suite passes **20 browser tests**, **4 frontend unit tests** and the backend
suite passes **121 tests**. Typecheck/build, Prettier, Ruff lint/format and diff checks pass.
Browser coverage includes upload/question/citation/trace/delete, duplicate/replacement,
412 reload/review, changed/deleted citation snapshots, token clearing/server rejection,
escaped markup, pagination, late-response races, conflict/absence statuses, request limits,
validation and 429/502/503 without automatic retries. Real routes use shared in-memory HTTP
provider fakes; selected UI state tests stub API JSON. The test-only reset is never registered
on the production app, and fixture markers are verified before reset. These tests do not
establish real model quality. The paid smoke is separate and opt-in.

Axe found zero violations in the sampled answered/dialog states and at widths 320/768/1024/1440;
screenshots were inspected. This is not a full manual accessibility certification. Replacing
code-point slicing with UTF-16 splitting made the Unicode highlight unit test fail; restoring
the implementation passed. A final real-preview read-only load has no browser warnings/errors.
The favicon 404 found in that check was fixed with an empty inline favicon.

**Tooling failure:** Nested npm commands resolved an unrelated incomplete npm installation in
`C:\Users\HP\node_modules`, missing `@npmcli/redact`. Preview now calls local tsc/Vite directly;
Playwright likewise starts local compiler/Vite binaries rather than recursively invoking npm.
The outer normal npm commands work; no home/global installation was changed. Test startup
failed before this fix and passed afterward. Formatting was committed separately from behavior
so the functional changes remain reviewable; browser fixtures are also type-checked.

**My understanding (George):** [ ] Run the new walkthrough; [ ] trace FormData/ETag and server
authorization; [ ] inspect old evidence versus a new revision; [ ] distinguish validation,
provider failure and insufficient evidence; [ ] explain the follow-up query adjustment.
These remain unverified by George. **AI contribution:** Codex drafted, diagnosed, tested and
documented the implementation, including the real-provider check. No independent authorship
or understanding is inferred from passing automated tests.

**Limits and resume point:** The typed client is not a full runtime schema validator; shared
demo administration is not user accounts; source listing has no title search. Quote identity
does not establish semantic support, and conflict detection still needs measured evaluation.
Follow `docs/react-workflows.md` for your checkpoint. Slice 8 is comparative evaluation,
followed by public deployment verification and delivery/rehearsal. None was started here.

## Session 8 — checkpoint A: define the measurement before observing scores

**What changed:** Added tested offline metric functions and a separate top-ten document
ranking in search traces. The production model still receives no more than eight chunks.
`docs/evaluation-methodology.md` freezes scoring, denominators, A/B order and development-only
selection rules before any slice-8 comparison. Work continues directly on main.

**Why / alternative:** Recall@10 cannot be calculated from an eight-chunk evidence list.
We rank the already-fetched active candidates with the same RRF and deduplicate documents for
diagnostics. Increasing model context to ten would alter the system being measured. Report
initial-query ranking, multi-search diagnostic fusion and actual final-context source coverage
separately. MRR rewards the first gold hit, while all-source coverage exposes broken bridges.

**Mechanism / verification:** For required documents {one,two}, ranking [noise,one,other,two]
has Recall@5=1 and reciprocal rank=1/2. A no-gold unanswerable case has undefined retrieval
recall, not a free perfect score. Tests also guard ten-document diagnostics with the unchanged
eight-chunk cap, deleted-candidate exclusion, document deduplication, RRF reuse/ties, prose
penalties and the official yes/no F1 rule. Seven focused tests pass after the initial missing-
implementation failure; Ruff lint/format passes. Read-only cloud checks find 50,024 active
documents and 52,250/52,311 physical A/B points (including retained old test revisions).

**Cost:** Before evaluation, estimated known ledger usage is $0.20992536; conservative
reservations are $0.48744711 against a $4.50 local ceiling. No indexing/model calls were made
by those cloud count checks. Model pricing was checked against official documentation.

**My understanding (George):** [ ] Calculate the example; [ ] explain MRR versus complete
source coverage; [ ] explain why exact quotes do not prove a claim. **AI contribution:** Codex
designed/drafted the measurement and tests; George's label review remains pending.
**Resume point:** Build the guarded resumable runner, run development A/B, freeze its selection,
then run the final set once under each configuration without tuning against the outcomes.

## Session 8 — checkpoint B: guarded runner and corpus preflight

**What changed / why:** Added a local `evaluation_cli` with preflight, paid serial run,
development-only selection and offline summaries. Atomic per-attempt receipts survive pauses;
an OS-released SQLite file lock prevents concurrent runs in the same output directory. A
pending interrupted attempt becomes an uncertain failure instead of an automatic paid retry.
Code/settings/fixture/cloud hashes must match on resume. All paid calls reuse the production
bounded investigation service; no gold answer or support label is passed to it. Public HTTP
admission limits are untouched. A failure is saved and stops the command for inspection.

**Alternatives:** A public batch endpoint would expose an expensive long request. In-memory
progress would lose paid results on interruption. Silently retrying failed calls could duplicate
cost and favor easy successful outputs in reported metrics. A generic evaluation framework
would add dependencies and obscure the small scoring rules we need to explain.

**Verification:** The backend suite passed 140 tests; the subsequent selection-integrity test
also passes. New tests protect cloud source/hash/profile readiness, budget rejection before
network, no automatic provider retry, exact question-only arguments, receipt reuse, exclusive
locking, interrupted work, final-before-selection rejection and selection hash immutability.
Ruff lint/format passes. The runner and scoring code were committed before model experiments.

Read-only preflight matched all active cloud source IDs/content hashes/profiles to the prepared
corpus. Expected active chunks are A=52,246 and B=52,307; physical cloud counts are 52,250 and
52,311 because four retained inactive test chunks exist in each collection. 47,952/50,024 source
records have identical chunk spans; 2,072 differ. This weakens causal claims about small A/B
differences. The corpus/fixture hashes remain the frozen values from slice 2.

**Budget / mechanism:** Each question may reserve at most $0.045624 at current rates under
the existing request/output limits. The command checks that full allowance before submitting.
The four earlier development smoke cases averaged $0.00525572; 96 attempts with 30% margin
project $0.655913856. Worst-case aggregate reservations could exceed available headroom, so
this is a projection and per-attempt guards still apply. No budget ceiling was increased.

**My understanding (George):** [ ] Explain resume versus retry; [ ] inspect a raw receipt and
its ledger delta; [ ] explain active versus physical chunks. **AI contribution:** Codex wrote
and tested these tools and ran cloud preflight. Independent reference/understanding review is
still pending. **Resume point:** Run development A/B, freeze the selection, then measure final.

## Session 8 — checkpoint C: freeze A before final testing

**Observed development results:** All 16 attempts are retained. A has 8 successful responses,
0 API failures, 6/8 supported-task checks, and 4/5 multi-source final-context coverage. B has
7 successful responses, 1 HTTP 502, 5/8 supported-task checks, and 3/5 multi-source context
coverage. Both have 100% mechanical citation validity among returned citations; failed outputs
do not receive a free citation score. Development cost estimates are A=$0.04405243 and
B=$0.04223703, including known usage on the failure.

**Decision / mechanism:** The predeclared first criterion selects A (6 versus 5 supported-task
checks). `docs/evaluation/selection.json` records the development receipt hash and selection
time, 2026-10-28 06:57:38 UTC (10:57:38 Asia/Tbilisi). Commit `d1ce1db` preserves that choice
and the raw development outputs before the final run. The existing A default remains selected;
final outcomes will not choose a different winner.

**Failure / limitations:** B's development conflict attempt returned HTTP 502 after both report
sources had been retrieved. Its receipt retains partial searches and cost, but only the HTTP
status, so it cannot distinguish every model/schema/evidence failure cause. It was not retried.
After inspecting it, the command resumed only absent cases; prompts/code were unchanged.
Development Buck-Tick A gave only “Japanese rock band,” missing the requested Fujioka/Gunma
location; B included that location but neither cited the separately labelled Hayden source.
Both documentary answers correctly expressed “not both American” without a literal “no,”
illustrating why the lexical supported-task proxy is not a human accuracy percentage.

**Reference review:** Before final calls, Codex inspected the native labelled passages and
recorded nine wording/label caveats in `docs/evaluation-reference-caveats.md`. Labels were not
edited. In particular, British does not alone entail English, and a numerical instrument/person
ratio is not specified by a “multi-instrumentalist” description. Keep raw scores and review
such abstentions/answers against actual text. George's independent label review remains pending.

**My understanding (George):** [ ] Inspect the decision timestamp and first final timestamp;
[ ] explain why 6/8 is a conservative mechanical check; [ ] inspect the failed receipt.
**AI contribution:** Codex ran/scored development, reviewed the failure and source caveats,
froze A and started the final run. **Resume point:** Complete one final attempt per case/config,
reproduce offline scores, review disputed claims and write measured findings without tuning.

## Session 8 — checkpoint D: final results, semantic failures and reproduction

**What changed / outcome:** All 96 planned attempts are complete: 16 development and 80 final.
No case/configuration was retried. A remains the development-selected default, despite some
stronger final retrieval results for B. `docs/evaluation-report.md` contains measured tables;
`docs/evaluation/` contains every raw attempt, scored row, phase checkpoint, hash and selection.
The walkthrough explains reproduction and hand calculations. Session 8's implementation boxes
are checked; George's learning/review checkbox remains unchecked.

**Observed final measurements:** Initial Document Recall@10 A=86.8%, B=89.7%; MRR@10
A=0.892, B=0.912 across 34 labelled cases. Diagnostic all-search Recall@10 is 92.6%/94.1%.
Both required sources reach final context in 22/26 multi-source A cases versus 23/26 B; both
are cited in 21/26 versus 20/26. A/B supported-task proxies are 32/40 and 31/40, **not human
semantic accuracy**. Both match expected status on 38/40. A has two final HTTP 502s (conflict
01/06); B has one (comparison 06). Development B's conflict error makes four errors overall.
Receipts retain partial retrieval and usage; exact failure subtypes were not captured.

**Metrics versus meaning:** Returned quote/ID/canonical-offset validity is 59/59 A and 58/58 B.
Labelled citation alignment is 57/59 and 56/58. Neither proves entailment. Reading all native
claims/quotes found unsupported US population figures citing Germany/world population, a wrong-
band citation, a reversed age comparison, and British→English origin inference. The wrong age
still contains the expected name and passes the automatic proxy. Some correct negative/implicit
positive comparisons fail literal yes/no checks. All prose EM scores are zero; full-response
token F1 is 0.221/0.195 and last-claim F1 0.224/0.208. Explanatory wording and lack of a dedicated
short-answer field make these imperfect lexical measures. These weaknesses are documented,
not hidden by extracting gold-dependent substrings or claiming automatic correctness.

**Qualitative evidence:** `docs/evaluation/qualitative-review.md` identifies Codex as the
reviewer and records case-specific claims/quotes. The native comparison/bridge outputs were
read, including automatically passing cases. Simple recovery values match the exact fictional
cases; successful conflicts preserve both reports; missing approvers abstain. This is assisted
review, not an independent human citation-accuracy estimate. Nine source/reference caveats were
recorded before final calls; frozen labels remain unchanged and George's review is still pending.

**Experimental limit / alternative:** Every required source has identical A/B chunk boundaries:
12/12 development and 60/60 final distinct passages. Entire-corpus identical spans are
47,952/50,024. Of 37 final case pairs with two successful outputs, only 21 share exact first-
query wording. The comparison therefore cannot isolate chunking quality from distractor ranks
and stochastic query/generation behavior. More boundary-sensitive examples, repeated trials
and fresh held-out cases would provide a stronger study. Adding them after seeing these final
outcomes would be a new experiment, not a repair to this reported result. No system tuning was
performed during the final run.

**Cost / latency:** Final A/B known estimates are $0.20097386/$0.20032803; development total
is $0.08628946; all evaluation adds $0.48759135. Project ledger after evaluation records
$0.69751671 known usage and $2.31480321 conservative reservations, under the unchanged $4.50
ceiling. Final attempt median latency is 5.288/5.151 s and p95 6.451/6.058 s, including failures
but excluding preflight and pauses. Caches were retained; configured rates do not claim billing
discounts, an invoice or account-wide budget enforcement.

**Verification:** All **141 backend tests** pass with warnings treated as errors; Ruff lint and
format pass. The free archive checker reproduces both complete summaries and every scored row,
checks 108 archived file fingerprints, unchanged corpus/fixture/code bytes, phase cloud identity,
configuration/limits, development selection timing and continuous ledger deltas. A disposable-
copy mutation changed a citation to nonexistent text; recomputation failed as expected. The
original archive was untouched and these checks made no provider requests. Fixed LF endings
were added for archived files to preserve byte fingerprints on Windows/Unix checkouts.
An additional read-only cloud check retrieved the four deleted indexed revisions and their
chunk IDs in both collections, confirming the physical-minus-active count difference without
model calls; see `docs/inactive-evaluation-points.json`.

**My understanding (George):** [ ] Run the free archive check; [ ] calculate one recall/MRR
example; [ ] trace a bridge's queries/context/citations; [ ] inspect the reversed-age and
population claims; [ ] explain why literal validity and name presence can both pass a false
claim; [ ] inspect the selection timestamp; [ ] review the labels independently.
**AI contribution:** Codex implemented, ran, reviewed and documented the work; no claim is made
that George independently authored or verified it. **Resume point:** Follow
`docs/comparative-evaluation.md` and `docs/evaluation-report.md`; slice 9 is public deployment
and restart verification, with final delivery/rehearsal in slice 10.

## Session 9 — checkpoint A: production image and fresh-container persistence

**What changed / why:** Built the multi-stage production image: Node compiles React, then
Python serves the API/assets from one origin. New HTTP probes and a disposable-container
command mutate only uniquely labelled sources they created, reject duplicate ownership, use
exact ETags, and clean up independently of the container. Remote origins require HTTPS with
no URL credentials, and authenticated requests never follow redirects.

**Failure and fix:** Docker `--env-file .env` preserves surrounding quotes, unlike Python
dotenv parsing. The first startup rejected a quoted Qdrant URL before provider work. The
launcher now parses Settings, creates an unquoted temporary runtime env file under ignored
artifacts, passes it to Docker and removes it. Root credentials are unchanged and not printed.

**Mechanism / observed verification:** With 512 MiB memory and 0.1 CPU quota, the production
image uploaded two fictional sources, replaced recovery 13→21 minutes, rejected a stale ETag
with 412, deleted one source, and answered 21 minutes citing the new revision. The container
was removed and a new one started without host data mounts. Its SQLite calls/cache counts
were zero, while Qdrant preserved source text/revision/ETag and the deletion's 404. A second
real answer cited the same updated revision. Both probe sources were deleted; original corpus
sources were untouched. Post-call measured memory was 108.9 MiB / 512 MiB, not a historical peak.

**Cost / alternatives:** Paid checks added estimated known usage $0.00887438. Before deletion,
container call rows were imported idempotently into the host ledger: now $0.70639109 known
usage/$2.35083284 reservations. A host ledger mount would avoid imports but invalidate the
ephemeral-filesystem test. The small importer deliberately depends on the ledger schema and
has duplicate/atomic-budget tests. No spending ceiling was raised.

**Deployment metadata:** An opaque per-process boot header distinguishes restart from browser
reload. A release header accepts only a commit SHA from Render's automatic RENDER_GIT_COMMIT
or Docker's build revision; arbitrary values are not echoed. Pure ASGI header wrapping adds
no document-body buffering or RAG changes. The Blueprint pins main/A/Free and a smaller $1
fresh-instance budget. That counter can still reset on Render spindown; it is not an account-
wide hard cap. Historical evaluation outputs stay frozen; deployment-only code changes can
legitimately differ from their original source-byte fingerprints.

**Verification / AI contribution:** All 151 backend tests pass with warnings treated as errors.
Tests cover origin/redirect safety, duplicate ownership, usage import, budget rejection, stable
boot IDs, changed IDs after recreation and release-value redaction. Codex drafted and ran the
work. Production build and the initial live persistence proof passed; rebuilt-image header and
zero-paid-call limit probes are next. Raw local evidence is saved under docs/deployment.

**My understanding (George):** [ ] Trace the two image stages; [ ] explain Qdrant versus SQLite
persistence; [ ] explain ETags/boot IDs; [ ] reproduce the env-file difference. Still pending.
**Resume point:** Rebuild with release metadata, verify limits, deploy Render Free Web Service,
then check the actual public URL/restart. Public deployment is not yet verified; George is
configuring Render access/service creation.

## Session 9 — UI refinement while deployment verification is in progress

**What changed:** George hosted the app and supplied
https://upgaming-ai-engineering-task.onrender.com/. Codex opened the public interface and
confirmed HTTP 200 liveness and dependency readiness (OpenAI/Qdrant reachable). The public
release at that point had the earlier UI and no release/boot headers. This is not cloud
restart proof. A local zero-paid Docker surface check stopped at dependency readiness;
its report is failed, not counted as a pass. Its disposable container was cleaned up.

**Why / UI approach:** The first interface gave setup details, form and empty state similar
weight. The refinement retains green/neutral colors and native controls, gives the question
clear priority, groups help in a narrower desktop column, simplifies mobile help, groups
document access/upload controls and makes citation actions more explicit. DESIGN.md records
the conventions. A component-library migration was considered unnecessary: it would add
dependencies and new abstractions without changing the API workflow.

**Mechanism:** Typing updates the existing controlled question state and its Unicode counter.
Browse documents calls a callback to App, switches view and focuses the library heading.
Both views remain mounted, preserving the draft. Choosing an example only fills/focuses;
explicit submission still invokes the same API. Results receive focus; citation dialogs
retain Escape, return focus, revision checks and safe source rendering.

**Verification:** All 21 fixture browser tests pass, including upload → question → citation →
trace → delete, replacement, conflicts, abstention, provider errors, stale data, token clearing,
axe checks and layouts at 320/768/1024/1440 px. The new test checks draft preservation,
focus and zero investigation requests from browsing/examples. One initial test failed because
its broad Search trace text selector matched new help text; it now targets the disclosure
control. Desktop/mobile renders were inspected; Impeccable's mechanical scan returned no
findings. TypeScript/production build, four client unit tests and formatting pass. Fixture
tests use in-memory providers and incur no model charges; real answer quality is not retested.

**AI contribution:** Codex designed, implemented, tested and documented the UI refinement
using Impeccable, frontend-ui-engineering and engineering-partner. React form accessibility
documentation was fetched through Context7. George performed hosting and shared the URL;
no independent code/understanding review is claimed.

**My understanding (George):** [ ] Follow docs/ui-refinement.md; [ ] preserve a question while
switching views; [ ] explain why an example does not submit; [ ] inspect a citation with the
keyboard; [ ] distinguish fixture tests from live semantic accuracy.

**Resume point:** Push the verified UI to main and verify the public build after Render
redeploys. Complete public restart/persistence checks before marking deployment verification
complete. Delivery/rehearsal remains slice 10.

**Public UI verification completed:** Pushed UI commit `8f236b2` directly to main; Render
automatically deployed it. The public release header matches its full commit SHA. Compiled JS
and CSS match the new build; the live UI shows the new question heading and library shortcut.
Public liveness/readiness, static assets, hidden private paths, absent test-reset route,
unauthorized-write rejection and pre-provider question validation all pass. Sanitized evidence:
`docs/deployment/public-ui-verification.json`. No real question or source mutation was submitted
in this public check. The browser opened the library and a canonical dataset source, returned
to Investigate, and confirmed no horizontal overflow at 1440 and 390 px. Desktop/mobile
screenshots are under ignored artifacts. Cloud restart/update/delete persistence is still
pending; the earlier local Docker readiness failure is not overwritten or counted as success.
George requested the available Impeccable update be deferred to a later session; no skill
update was performed.

## Session 9 — cloud probe exposed a proxy ETag incompatibility

**Observed failure:** The first public probe created two uniquely labelled fictional sources
but stopped before replacement. The hosted response had `ETag: W/"<revision>"`; the server's
exact If-Match revision comparison correctly rejected that value with HTTP 412. A separate
reproduction confirmed the 412 and unchanged active revision without model generation.
Evidence is in `docs/deployment/weak-etag-reproduction.json`. Test sources remain owned by
the saved probe checkpoint for cleanup after the fix deploys. No failed question was retried.

**Fix / why:** Document GET/POST/PUT now additionally expose `X-Document-ETag`, containing
the server's exact quoted revision token. React and the deployment helper prefer it, falling
back to ETag for older/local servers. This keeps transport compression validators separate
from the application revision precondition. Server comparison stays strict: stale and weak
If-Match values still receive 412. Accepting any weak tag or disabling concurrency protection
would hide stale-edit bugs. Custom response headers are available here because production
serves UI/API from the same origin. RFC 9110 section 13.1.1 specifies strong comparison for
If-Match; the fix does not strip the weak prefix and pretend the representation is identical.

**Verification:** Backend lifecycle assertions cover the dedicated header on create/read/replace
and continued rejection of weak/stale tags. Client/helper tests simulate proxy-weakened ETags.
Five client tests and all 21 fixture browser workflows pass; targeted backend checks pass.
The new two-phase cloud script checkpoints ownership before further writes, never adopts
duplicates, refuses cleanup after external edits, rejects an unchanged boot ID, and reserves
host budget before paid steps. Six offline tests cover those guards. Public verification
continues after deploying the fix. George confirmed the Render instance is Free and its
API_BUDGET_USD is 1.0; this is user-confirmed account configuration, not a public API claim.

**AI contribution / learning:** Codex diagnosed and patched this hosted-only boundary bug;
George's review is pending. Explain why a browser reload is not a server restart, why a weak
ETag cannot satisfy an exact revision precondition, and why source storage must outlive a
web process. Resume with cleanup of the failed probe, then a fresh complete restart run.
