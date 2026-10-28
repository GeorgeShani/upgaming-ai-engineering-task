# Slice 7: run and understand the React workflows

The website now manages documents and runs investigations. Work was implemented directly on
`main`. The automated checks below exercise the application; your understanding checklist at the
end remains yours to complete. Comparative evaluation is slice 8 and has not started.

## 1. Start the two processes

From the repository root, with your existing `.env` in place:

```powershell
uv sync --frozen
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run preview
```

Open http://127.0.0.1:4173. `prepreview` type-checks and rebuilds first. Preview serves compiled
files, so restart it after frontend changes; `npm run dev` instead gives hot reload on port 5173.
Python must stay running separately. Neither command deploys the app publicly.

Open **Service connections**. `/api/live` only proves Python is running. `/api/health` checks
configured OpenAI model access and Qdrant access without generating answers or embeddings.
Connected does not prove credit, document write access, a complete index, or answer quality.

## 2. Trace a browser request

Read `frontend/src/api.ts`, then `frontend/src/components/Documents.tsx`.

1. Clicking Upload constructs browser `FormData` containing the selected file.
2. `fetch('/api/documents', ...)` sends it to the current website origin. The browser supplies the
   multipart boundary; setting `Content-Type` manually would risk breaking that boundary.
3. In preview, Vite forwards `/api` to FastAPI on port 8000. In production, FastAPI serves both
   the compiled React files and `/api`, so the browser still uses one origin.
4. FastAPI validates the bearer token, file size/type and parsing, then stores canonical text,
   stages both search configurations and activates the revision in Qdrant.
5. React receives JSON, updates its state and opens the returned document ID. The last-upload
   shortcut matters because UUID ordering may place a new source far beyond page one.

There is one typed API boundary. TypeScript checks our callers; it does not fully validate
arbitrary runtime JSON. FastAPI supplies the response contract, and integration tests protect
the current pairing. A runtime schema library would provide stronger contract checks at the
cost of another schema/dependency to maintain.

Two mounted views and local React state preserve your question/result/token during navigation.
A router and global store would help with shareable URLs or a larger workspace; they add little
to these two views. Reloading the page clears that state. Document state lives on the server.

## 3. Upload, inspect and recognize a duplicate

In **Documents → Manage access**, enter `DEMO_ADMIN_TOKEN` from your local `.env`. Do not paste
OpenAI or Qdrant keys here. The token stays in React memory, is masked, and is sent only for
document mutations; FastAPI validates it. Clearing it or reloading the page removes it from
the UI. This is shared demo administration, not individual user accounts.

Create a small TXT file with a unique case label, for example:

```text
Fictional practice case GEORGE-01. Payment-router recovered after 17 minutes.
```

Upload it and inspect **Canonical source text**, source ID, revision, locations, provenance and
search status. Text is rendered as React text, so `<img onerror=...>` remains visible text.
Large sources initially show a bounded excerpt; request full text explicitly when needed.
Repeat the same upload: the UI should say it already exists and open the same source.
Try the committed PDF/DOCX samples described in `document-management.md` as well.

Files must be nonempty PDF, DOCX or TXT and at most 5,000,000 bytes. Client checks improve
feedback; server checks remain authoritative. No OCR or original binary download is provided.
Document listing uses 20-item cursor pages instead of fetching the whole 50,024-source corpus.
There is no title search or global total in this version.

## 4. Ask, open evidence and read the trace

Close the source, choose **Investigate**, and ask about your unique practice case. This makes
paid embedding/model calls; submitting repeatedly is unnecessary. Example buttons only fill
the form. Pending requests disable resubmission, and failed requests are never retried by the UI.

An `answered` result contains cited claims. Click a citation to see its retrieved quote/chunk
and the current canonical source. The E-ID identifies evidence within that investigation;
document ID identifies the durable source; revision ID identifies the text version.
Highlight offsets come from Python, which counts Unicode code points. `sourceText.ts` uses
`Array.from(text)` so an earlier emoji does not shift the highlight through JavaScript UTF-16
indexing. It verifies the chunk still matches before highlighting.

Expand **Search trace**. Inspect the round, actual query, evidence-backed follow-up entity,
semantic/keyword candidate counts and retrieved text. When a valid entity was omitted from a
model query, the server prepends it and shows both the proposed and executed query. The entity
must still appear literally in prior evidence; unknown anchors and oversized adjusted queries
are rejected before a search. The two-round/three-search limits remain unchanged.

RRF scores rank relevance; they are not truth probabilities. The trace exposes observable
search actions and evidence, not hidden model reasoning. A valid quote proves text identity,
not that the quote logically supports the answer. That remains an evaluation/review question.

`insufficient_evidence` and `conflicting_evidence` are successful evidence results. HTTP 429,
502 or 503 means the request failed or was limited; it must not be interpreted as no answer
in the corpus. Client validation says nothing was submitted. A timeout may still have incurred
usage: the UI does not resubmit it. The browser question deadline is 105 seconds, beyond the
server's 90-second investigation deadline.

## 5. Replace, detect a stale edit and delete

Return to **Documents** and use **Open last uploaded source**. Select a replacement file and
save it. A GET returned an exact quoted `ETag`; React sends it unchanged as `If-Match` for
PUT/DELETE. If another client updated the source first, FastAPI returns 412. The UI blocks the
stale write, asks you to reload, and clears the old selected file so you review the new revision
before choosing it again. Some network/server failures are ambiguous; reload before retrying.
This is preferable here to optimistic UI updates that could display a write that failed.

Reopen the old answer's citation. It should label the old evidence as a snapshot and show the
new canonical text separately. Delete your practice document through its confirmation step.
The old citation can retain its retrieved snapshot; the source GET returns 404 and retrieval
excludes it. The UI does not silently rewrite previous answers when the corpus changes.
The native dialog supports Escape/focus containment and restores focus after closing; while
a write is pending, wait for its result before closing.

## 6. Reproduce automated checks

These use isolated in-memory provider fakes and make no paid calls:

```powershell
# Repository root
uv run --group data pytest -W error
uv run ruff check backend scripts/verify_browser_workflow.py
uv run ruff format --check backend scripts/verify_browser_workflow.py
cd frontend
npm run test:unit
npm run format:check
npm run build
npx playwright install chromium --no-shell
npm run test:browser
```

Playwright starts separate fixture FastAPI/compiled preview processes on 8001/4174 and refuses
to reuse existing servers. Its reset endpoint exists only in `backend/tests/browser_app.py`;
tests verify the fixture marker before resetting. Some status/error tests stub the final API
response to make rare states deterministic. The lifecycle smoke runs real FastAPI routes with
fake external providers. Neither proves real model quality. See `browser-verification.json`.
The runner invokes project-local build tools directly to avoid an unrelated broken ancestor
npm installation observed on this Windows machine. No home/global installation was modified.

An optional paid check, with the real API/preview already running, is:

```powershell
# Repository root
uv run python scripts/verify_browser_workflow.py
```

It reads the admin token server-side and passes it only through a child environment, creates
one uniquely labelled fictional source, asks one question and deletes only the source it
created. It records no browser trace/video/request headers. Cleanup also runs after failure
when its new source ID is known. Deletion leaves the normal server tombstone/revision history.
Reports/screenshots go to ignored `artifacts/`; the committed successful sanitized report is
`browser-live-verification.json`. Failed development attempts also consumed ledger reservations.

The successful real run returned 17 minutes in 6,494 ms, opened its actual source citation and
second-round trace, and confirmed deletion with GET 404. Investigation estimated cost was
$0.00448099; upload plus question increased known ledger usage by $0.00448239. These are
application estimates, not an invoice, hard account cap, or final evaluation results.
Automated axe checks found no violations in the tested answered/dialog states and at widths
320, 768, 1024 and 1440; this does not replace manual screen-reader/accessibility review.

## Your checkpoint before slice 8

- [ ] Run preview yourself and explain why Python must also be running.
- [ ] Upload TXT/PDF/DOCX; inspect text/locations, and recognize an exact duplicate.
- [ ] Trace FormData → proxy → auth/parser/storage → JSON → React state in the code.
- [ ] Ask one question, open every citation and decide whether each quote supports its claim.
- [ ] Find the first and second search queries; explain the follow-up entity and RRF score.
- [ ] Replace a source, inspect an old citation, then delete your practice source.
- [ ] Explain why 412, insufficient evidence, conflicting evidence and 502 are different.
- [ ] Reload and confirm the admin token is cleared; use keyboard navigation and Escape.

The remaining slices cover comparative evaluation, public deployment verification and final
delivery/rehearsal. The current successful browser smoke does not complete those requirements.

Primary references used for the implementation: [React state](https://react.dev/learn/managing-state),
[Vite preview](https://vite.dev/guide/static-deploy.html),
[Playwright web servers](https://playwright.dev/docs/test-webserver),
[native dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog), and
[FormData](https://developer.mozilla.org/en-US/docs/Web/API/FormData).
