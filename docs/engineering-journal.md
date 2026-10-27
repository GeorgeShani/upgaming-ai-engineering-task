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
