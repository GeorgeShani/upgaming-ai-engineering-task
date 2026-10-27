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
- Real OpenAI/Qdrant access and Render deployment remain pending. No project provider credentials
  were configured in this environment, and no live demo URL has been verified.

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
checklist. Configure provider accounts and deploy the foundation. Session 2 follows this review.

## Template for later sessions

### What changed
### Why
### Alternatives and drawbacks
### Trace a concrete input
### Verification, including failures
### My understanding (George writes this)
### AI contribution and independent changes
### Resume point
