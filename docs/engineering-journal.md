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

## Template for later sessions

### What changed
### Why
### Alternatives and drawbacks
### Trace a concrete input
### Verification, including failures
### My understanding (George writes this)
### AI contribution and independent changes
### Resume point
