# AI Investigation Engine

An evidence-based investigation engine built in small, reviewed sessions for the Applied AI
assignment. **Current stage: Session 2, dataset preparation and evaluation fixtures.** The web
interface still shows the verified connection page. Source preparation is available through the
offline CLI; document ingestion, search, answer generation, and evaluation scoring remain planned.
No public demo URL has been verified yet.

Start with [the plan](tasks/plan.md), [the checklist](tasks/todo.md), and
[the engineering journal](docs/engineering-journal.md). The [AI usage report](docs/ai-usage-report.md)
records actual assistance and independent work.

## Prepare and verify the dataset

The committed fixtures contain 40 final questions, 8 development questions, and their 72 supporting
source records. The large corpus is generated locally under ignored `data/`, not stored in Git.
Read the [fixture review sheet](docs/evaluation-fixtures.md) before accepting reference answers.

From the repository root:

```powershell
uv sync --frozen --group data
uv run --group data python -m backend.app.dataset_cli prepare
uv run --group data python -m backend.app.dataset_cli verify
```

Preparation streams a pinned HotpotQA revision, includes required evaluation support, deduplicates
normalized source text, and selects 50,000 distinct HotpotQA passages. It appends 24 explicitly
fictional source records. It creates `data/prepared/corpus.jsonl` and `manifest.json`, and refuses
to overwrite an existing output. If these files already exist, run `verify`; to reproduce separately:

```powershell
uv run --group data python -m backend.app.dataset_cli prepare --output data/reproduced
uv run --group data python -m backend.app.dataset_cli verify --output data/reproduced
```

The corpus hashes should match for the same inputs and settings. An explicitly smaller `--count`
is permitted for experiments, but its manifest truthfully reports whether it reaches 50,000
HotpotQA passages. Counts below the required support set are rejected. Preparation makes no
embedding or generation calls and does not write to Qdrant. This is not the later indexing job;
failed preparation restarts deterministically, while interrupted output is not published.

The [verification report](docs/dataset-preparation-report.json) records the actual count and byte
hash of this run. It is not a retrieval-quality report. See [fixture conventions](fixtures/README.md)
for schema, provenance, licensing, leakage prevention, and deliberate benchmark limitations.

```powershell
uv run --group data pytest -W error
```

The offline tests use tiny synthetic training inputs plus committed fixtures; they do not download
the full dataset, contact model providers, or spend API credit. The optional `data` group contains
Datasets/PyArrow/Pandas tooling and is not installed by the production Docker build.

## Run locally (PowerShell)

Prerequisites: Node.js 24 and `uv`. `uv sync` installs the pinned Python 3.12 interpreter if needed.
Run these commands from the repository root:

```powershell
uv sync --frozen
Copy-Item .env.example .env
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/docs.
An unconfigured setup is expected to show "Needs setup". It does not require paid API calls.
Only copy the template once: do not overwrite an existing `.env` containing your credentials.

### Preview the built website

Keep the Python server running on port 8000. In the frontend terminal:

```powershell
npm run preview
```

Open http://127.0.0.1:4173. The `prepreview` script runs `npm run build` automatically before
starting Vite's preview server. This avoids previewing an old build. Preview forwards `/api`
to the Python server, just like development. The port is strict: if 4173 is occupied, stop the
existing preview rather than accidentally opening another instance on a different port.

Preview serves built files and does not hot-reload source changes. Restart `npm run preview`
after editing frontend code, or use `npm run dev` for hot reload. Preview does not start Python
and is for local verification; production serves the compiled files directly through FastAPI.
The full [Session 1 walkthrough](docs/engineering-journal.md#session-1-hands-on-walkthrough)
explains the request path and verification exercises.

## Configure providers

Edit the root `.env` locally; never paste API keys into frontend code, Git, or the journal.

- `OPENAI_API_KEY`: an OpenAI API project key. ChatGPT access does not configure an API key here.
- `QDRANT_URL`: the HTTPS URL of your Qdrant Cloud Free cluster.
- `QDRANT_API_KEY`: the cluster's API key.
- Models and embedding dimensions have the accepted plan's defaults in `.env.example`.

Restart Python after changing configuration and click **Check connections**. The backend reads
model metadata for both OpenAI models and lists Qdrant collections. It does not generate answers
or embeddings. Passing checks does not prove sufficient credit, write access, or indexing.
The public report exposes status, never keys, provider bodies, or cluster URLs.

## Verify the foundation

```powershell
uv run pytest
uv run ruff check backend
uv run ruff format --check backend
cd frontend
npm run build
```

The backend tests use mocked provider transports, make no paid calls, and check successful,
unconfigured, rejected, and timed-out connections, secret redaction, and static/API routing.
Actual provider access remains a separate check.

To exercise the production arrangement, build the frontend, then start Python from the root:

```powershell
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The built frontend must exist before starting the server.

## API in this slice

| Endpoint | Meaning |
| --- | --- |
| `GET /api/live` | 200 while Python is running; no dependency calls |
| `GET /api/health` | 200 when all configured provider access checks pass; otherwise 503 plus a structured report |
| `/docs` | Interactive FastAPI API documentation |

Other planned API endpoints return 404 until their implementation sessions.

## Deploy on Render Free

1. Push the verified branch to the GitHub repository.
2. In Render create a Blueprint from the repository, selecting that branch. `render.yaml` specifies
   a **Free** Docker web service; do not select a paid instance or database.
3. Supply the three provider secrets in Render's environment settings. They remain server-side.
4. Render builds React in a Node stage and copies only its output into the Python runtime. Python
   serves that output and the API on Render's `PORT`.
5. Open the assigned public URL and check `/api/live`, `/api/health`, and the connection page.
6. Record the real URL and results here and in the journal only after verification.

The host health check uses liveness so a provider outage does not cause a deployment restart loop.
No paid infrastructure is required. Render Free has limited memory, sleeps after idle periods,
and discards local files on restart. Future persistent documents and indexes therefore belong in
Qdrant, not a local SQLite database or uploads directory. The free database also has inactivity
restrictions. The $5 API target is separate from infrastructure hosting.

Docker is optional for local development. To check the actual image locally:

```powershell
docker build -t investigation-engine .
docker run --rm -p 8000:8000 --env-file .env investigation-engine
```

## Technical choices

FastAPI supplies typed API contracts and Python processing; React uses familiar frontend tools.
Serving both from one production origin avoids a separate deployment and CORS configuration.
One HTTP client is shared through FastAPI's lifespan and closed at shutdown. Liveness is separate
from external access checks. See the journal for concrete request traces, alternatives, limits,
and your own learning checkpoint.

Official references: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[Vite](https://vite.dev/guide/), [Render free limits](https://render.com/docs/free), and
[Qdrant free clusters](https://qdrant.tech/documentation/cloud/create-cluster/).
