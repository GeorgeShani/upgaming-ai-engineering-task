# AI Investigation Engine

An evidence-based investigation engine for the Applied AI assignment. Upload PDF, DOCX or TXT
sources, ask questions across a shared collection, and inspect cited passages and search traces.
The bounded investigation can follow an entity into another document, preserve conflicting
reports, or return insufficient evidence.

**[Live demo](https://upgaming-ai-engineering-task.onrender.com/)** ·
**[GitHub repository](https://github.com/GeorgeShani/upgaming-ai-engineering-task)**

The app uses 50,024 distinct source passages: 50,000 HotpotQA passages and 24 clearly fictional
incident sources. Both chunking configurations are indexed. Configuration A was selected on
separate development examples before the final evaluation. Read the measured
[evaluation report](docs/evaluation-report.md), including semantic citation failures and study
limitations. This is an assisted build; independent learning/rehearsal remains George's work.

## Architecture

```text
Browser: React + TypeScript
  /api requests
FastAPI: one Python web process, also serving compiled React
  ├─ PDF/DOCX/TXT → normalize/hash → canonical revision → chunks → embeddings
  │                                                    ↓
  └─ question → model search tool → dense + BM25 → custom RRF → cited claims
                                                       ↕
                                      Qdrant Cloud: sources, revisions, A/B indexes
```

Canonical source text is separate from chunks. Replacement prepares all new chunks before
activating its revision. Retrieval checks current manifests, so deleted and inactive revisions
are excluded even if their physical vectors remain. Mutations use a server-validated admin
token and an exact revision precondition; stale edits receive HTTP 412.

Search retrieves top-30 dense and top-30 BM25 candidates, combines ranks with custom reciprocal
rank fusion (`sum(1 / (60 + rank))`), and limits evidence to eight chunks/two per document.
A uses 256-token windows/40-token overlap. B uses sentence groups up to 256 tokens, one sentence
overlap, and splits oversized sentences. Rankings are relevance scores, not truth probabilities.

The real `search_documents` model tool has validated arguments, at most two retrieval rounds,
three searches and three language-model calls. Follow-up entities must come from earlier
retrieved evidence. Responses contain `answered`, `insufficient_evidence` or
`conflicting_evidence`, claims/citations and a public search trace. Quote/ID validation proves
citation integrity; it does not prove semantic entailment. Provider errors remain API errors.

Default hosted models are `text-embedding-3-small` with 384 dimensions and
`gpt-5.4-mini-2026-03-17`. All model/rate settings are server-side and configurable.

| Choice | Why here | Alternative and trade-off |
| --- | --- | --- |
| React/TypeScript + Vite | Builds on familiar web skills with explicit API integration | Gradio is faster to assemble but offers less control over document/evidence workflows |
| Explicit FastAPI modules | Keeps parsing, storage, retrieval and investigation traceable | A large agent framework adds abstractions to learn and debug |
| Qdrant Cloud | Dense/BM25 search and canonical payloads survive ephemeral hosting | PostgreSQL/pgvector is viable but adds schema/search setup; Qdrant lacks relational transactions, so staged activation and one writer matter |
| Hosted 384-dimension embeddings | Fits the small server without loading a model | Local embeddings remove per-call charges but need more memory and operational work |
| Custom RRF | Combines different ranking scales with a small testable algorithm | Raw-score addition needs calibration; reranking may improve precision but adds cost/latency |
| Bounded tool workflow | Supports follow-ups with predictable call/context limits | An unrestricted agent can explore more but makes failures, latency and cost less predictable |
| One origin/process | Simplifies deployment, credentials and browser requests | Separate services scale independently but add deployment/CORS/distributed-lock work |

## Run locally

Prerequisites: Git, Node.js 24 and uv. Python is pinned to 3.12; dependencies are locked in
`uv.lock` and `frontend/package-lock.json`. From a checkout:

```powershell
uv sync --frozen
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit the ignored root `.env`: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and
`DEMO_ADMIN_TOKEN`. Keep keys out of frontend code, Git and screenshots. With no provider
configuration the UI can start, but readiness reports setup is needed.

Start the API from the root:

```powershell
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. For a production-build preview, keep Python running and use
`npm run preview` instead. It automatically type-checks/builds, then serves port 4173.
Both Vite modes proxy `/api` to port 8000. Restart preview after source changes; use dev for
hot reload. To check the single-origin production arrangement, run `npm run build`, then
start Python and open http://127.0.0.1:8000. Interactive API contracts: `/docs`.

Reading and asking questions need no admin token. Enter it in Documents → Manage access for
writes; it stays only in page memory. This is a public, shared demo: use public/fictional
sources. Extracted source text is public; original binaries are not retained.

## Reproduce data and indexes

For a fresh corpus directory:

```powershell
uv sync --frozen --group data
uv run --group data python -m backend.app.dataset_cli prepare
uv run --group data python -m backend.app.dataset_cli verify
```

Preparation pins HotpotQA revision `1908d6afbbead072334abe2965f91bd2709910ab`, selects distinct
normalized passages deterministically and appends labelled fictional sources. The manifest
records hashes, counts and provenance. It refuses to overwrite an existing output; if data is
already prepared, run verify. The large corpus, cache and ledger live in ignored `data/`.
Evaluation questions/reference answers/support labels never enter the index.

On a fresh Qdrant cluster/namespace, estimate before the paid import:

```powershell
uv run python -m backend.app.index_cli estimate --report artifacts/index-estimate.json
uv run python -m backend.app.index_cli run --limit 1000 --report artifacts/index-pilot.json
```

Measure throughput/cost, then run without `--limit` only when the estimate fits the budget.
Stop the web writer during bulk indexing. Resume the same command/cache after interruption;
it skips ready records and preserves edits/tombstones. Do not reimport the shared demo to
undo its user changes. The [indexing walkthrough](docs/retrieval-and-first-answer.md) explains
profile changes, capacity, pilot results and full-import commands.

## Verification and evaluation

Free automated checks from the root:

```powershell
uv run pytest -q -W error
uv run ruff check backend scripts/deployment_checks.py scripts/verify_cloud_persistence.py scripts/verify_deployment_corpus.py
uv run ruff format --check backend scripts/deployment_checks.py scripts/verify_cloud_persistence.py scripts/verify_deployment_corpus.py
```

From `frontend/`:

```powershell
npm ci
npm run test:unit
npm run test:browser
npm run build
npm run format:check
```

Browser tests start their own API/UI on ports 8001/4174 with in-memory providers. They cover
upload → question → citation → trace → delete, revisions, errors, safe rendering, keyboard
focus, axe and four responsive widths. They make no paid model calls.

With the prepared corpus available, reproduce all saved evaluation scores offline:

```powershell
uv run python scripts/verify_evaluation_archive.py --report artifacts/evaluation-reproduction.json
```

The frozen study has 16 development and 80 final attempts, retaining four failed attempts.
The checker recomputes every score and summary and validates the archived fingerprints.
Current deployment/header code differs from the experiment's original bytes; that is reported
without rewriting historical results. Retrieval/prompts/model settings remain as evaluated.
For a new paid experiment use a new output directory and the
[evaluation reproduction guide](docs/comparative-evaluation.md). Do not rerun frozen final
cases to tune this result. Metrics, raw outputs and reviewed failures:

- [Methodology](docs/evaluation-methodology.md) and [measured results](docs/evaluation-report.md).
- [Raw archive manifest](docs/evaluation/manifest.json), [selection](docs/evaluation/selection.json),
  and [qualitative review](docs/evaluation/qualitative-review.md).
- [Reference caveats](docs/evaluation-reference-caveats.md): AI review is identified; George's
  independent gold/citation review remains pending.

## Public API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/live` | Python liveness; no provider work |
| `GET /api/health` | Read-only dependency readiness; 200 or structured 503 |
| `POST /api/documents` | Small PDF/DOCX/TXT upload, exact deduplication and indexing |
| `GET /api/documents` | Cursor-paginated source list |
| `GET /api/documents/{id}` | Canonical source and metadata |
| `PUT /api/documents/{id}` | Prepare and activate a replacement revision |
| `DELETE /api/documents/{id}` | Tombstone and exclude from retrieval |
| `POST /api/investigations` | Bounded question, evidence, status, search trace and usage |

Mutations require `Authorization: Bearer <demo token>`. PUT/DELETE additionally require
`If-Match` containing the exact quoted `X-Document-ETag` returned on create/read/replace.
That application revision header survives proxies weakening the standard representation ETag.
Uploads are capped at 5,000,000 bytes. Investigations are limited to six/minute and one active
request per process, with bounded context/output and a 90-second application deadline.

## Deployment, resources and cost

Use **Render Web Service → Docker → Free → main**. `render.yaml` pins the service, liveness
path `/api/live`, configuration A and a $1 per-instance guard. Supply all four secrets in Render
without surrounding quotes. Docker builds React in a Node stage and runs only Python plus the
compiled assets. No separate frontend service, Redis or worker is needed. The local image can
be built with `docker build -t investigation-engine:slice9 .`.

Render Free sleeps after inactivity and discards local files. Qdrant preserves canonical
sources/revisions/indexes; local SQLite embedding cache and spending counters may disappear.
Therefore the application budget is not a durable account-wide hard cap. The local project
ledger retains development/index/evaluation reservations; cloud verification records its paid
questions there too. Rates are configured estimates, not invoices. Unknown failures retain
reservations; uploads' unreported embedding costs retain small conservative reservations.
The API target is $5 total and is separate from free hosting. See the latest cost receipt in
[deployment verification](docs/deployment-verification.md).

Follow the [cloud restart walkthrough](docs/deployment-verification.md) for the two-phase
owned-source probe, exact corpus audit, limits, evidence and rollback. Original binary downloads,
OCR, distributed locks/rate limits, production backup recovery, streaming and multiple model
comparisons are outside this version. Near-duplicates are not detected. Conflict detection and
semantic citation support remain substantive limitations documented in the evaluation report.

## Delivery and understanding

[Submission checklist](docs/submission.md) · [Interview rehearsal](docs/interview-rehearsal.md) ·
[AI usage report](docs/ai-usage-report.md) · [Engineering journal](docs/engineering-journal.md) ·
[Accepted plan](tasks/plan.md) · [Progress and independent-review checklist](tasks/todo.md).

Hands-on walkthroughs: [documents](docs/document-management.md),
[retrieval](docs/retrieval-and-first-answer.md), [investigation](docs/multi-step-investigation.md),
[React](docs/react-workflows.md), [UI refinement](docs/ui-refinement.md),
[metrics](docs/comparative-evaluation.md).

Source data retains its recorded provenance/licences; fictional fixtures are explicitly labelled.
No repository-wide licence grant is implied. The assignment permits AI assistance and requires
its disclosure; the interview's practical part must be completed without AI.
