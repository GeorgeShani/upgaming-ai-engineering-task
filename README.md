# AI Investigation Engine

An evidence-based investigation engine built in small, reviewed sessions for the Applied AI
assignment. **Current stage: Session 1 foundation.** Document ingestion, search, investigations,
and evaluation are planned, not yet implemented. No public demo URL has been verified yet.

Start with [the plan](tasks/plan.md), [the checklist](tasks/todo.md), and
[the engineering journal](docs/engineering-journal.md). The [AI usage report](docs/ai-usage-report.md)
records actual assistance and independent work.

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
