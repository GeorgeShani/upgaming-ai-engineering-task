# Cloud deployment and persistence walkthrough

Public app: https://upgaming-ai-engineering-task.onrender.com/.

**Latest verification:** application release `5911d65` includes cited-claim review and numeric
checks. [Grounding verification](grounding-verification.json) records its real public answer;
[final requirement evidence](final-requirements-verification.json) records the subsequent
read-only public/source/build and full-corpus checks. The earlier restart and ledger totals
below are dated evidence of that probe, not current account-wide billing totals.

The actual cloud restart receipt is [cloud-persistence.json](deployment/cloud-persistence.json).
It records a successful 13→21 minute replacement, stale-tag rejection, deletion, changed
server boot ID and correct cited answers before/after the new Render instance. All owned
sources were cleaned up. The two successful question estimates total $0.00872823; upload
embedding usage retains conservative reservations because that route does not expose usage.
The failed first probe and ETag reproduction are retained rather than presented as successes.

At the restart-check checkpoint, the project ledger had $0.71511932 known estimated usage and $2.47683284
conservative reservations against its unchanged $4.50 ceiling. These totals exclude unknown
public visitor activity and are not provider invoices. The per-instance Render guard remains
$1. The [whole-corpus audit](deployment/corpus-verification.json) records current counts;
the [delivery verification](delivery-verification.json) records that delivery checkpoint.

One Docker Web Service serves FastAPI and the compiled React interface. Qdrant Cloud stores
canonical extracted text, document manifests/revisions and both vector indexes. Node builds
the frontend but does not run in the production image. Python listens on `0.0.0.0:$PORT`.
There is one web process, no worker, no Redis and no persistent Render disk.

## What survives a restart

| State | Storage | Expected after a fresh process |
| --- | --- | --- |
| Source text, document ID, active revision, metadata | Qdrant | Preserved |
| Deleted document tombstone | Qdrant | GET stays 404; retrieval rejects its chunks |
| Dense/BM25 chunks for A and B | Qdrant | Preserved; old revision points may remain physically |
| Uploaded PDF/DOCX/TXT binary | Not retained | No original-file download |
| Embedding cache and spending ledger | Local SQLite | May disappear |
| Admin token entered in the browser | React memory | Clears on page reload |
| Boot ID | Process memory | Changes on server recreation |

A browser refresh is not a restart. `X-Investigation-Instance` is an opaque per-process boot
identity. `X-Release-Revision` identifies the deployed Git commit using Render's automatic
environment value. Neither contains a credential. Readiness and unchanged text alone do not
prove that a fresh process was used.

## Reproduce the two phases

Run from the repository root with local `.env` credentials for this same public deployment.
The script reads the token locally; never pass it in a URL or command-line argument. These
checks create only uniquely labelled fictional documents, make two real investigations,
reserve local budget first, retain receipts and refuse automatic paid retries.

```powershell
uv run python scripts/verify_cloud_persistence.py prepare --url https://upgaming-ai-engineering-task.onrender.com
```

Preparation uploads two documents, changes one recovery value from 13 to 21 minutes, checks
that the old revision tag receives 412, deletes the other document, and asks a question that
must cite 21 minutes from the new active revision. It saves IDs, text, revision, tag, boot ID
and spending receipts under ignored `artifacts/cloud-persistence/`. `passed: false` in this
phase means the restart has not yet been verified.

Now recreate the service. In our run, a meaningful commit containing verification tooling
was pushed to the service's connected `main` branch, triggering a normal Render redeploy.
For a repeat, use the service's dashboard restart/redeploy action; do not create empty commits
just to manufacture history. Wait for liveness/readiness and a different boot ID.

```powershell
uv run python scripts/verify_cloud_persistence.py verify --url https://upgaming-ai-engineering-task.onrender.com
```

For a deploy test, optionally add `--expected-revision` followed by the full deployed commit
SHA. Verification refuses to proceed with an unchanged boot ID. It checks text, revision,
revision tag and deletion, then repeats the question, validates quotes/current source IDs,
rejects deleted/inactive evidence in the returned search trace, and cleans up owned sources.
The final receipt is successful only after cleanup. Any question failure remains recorded;
do not delete the checkpoint and silently resubmit it.

If interrupted, inspect the saved phase/receipt. This cleanup command verifies marker,
filename and expected revision before deleting; externally edited sources are left alone:

```powershell
uv run python scripts/verify_cloud_persistence.py cleanup --url https://upgaming-ai-engineering-task.onrender.com
```

Use `--state` consistently to choose another checkpoint file for an explicitly new run. The
saved receipt contains public fictional text and opaque IDs, but no credentials. HTTPS is
required remotely and authenticated requests never follow redirects.

## Why the separate document revision header exists

The first public probe exposed an actual deployment bug: the hosting proxy returned a weak
representation ETag, `W/"<revision>"`. Passing it unchanged as If-Match produced HTTP 412.
Local tests had no compression proxy, so the issue appeared only in the cloud.

The API now exposes `X-Document-ETag` on create/read/replace. Clients prefer that exact quoted
revision token for If-Match. Standard ETag remains available for HTTP representation semantics.
The server still rejects stale or weak preconditions; it does not weaken concurrency checks.
See the [failure reproduction](deployment/weak-etag-reproduction.json) and the regression
tests. This follows the strong-comparison requirement in
[RFC 9110 §13.1.1](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match).

## Verify the whole corpus without model calls

After removing probe documents and while nobody is changing the corpus:

```powershell
uv run python scripts/verify_deployment_corpus.py
```

This verifies the prepared dataset hashes, all active cloud source IDs/content hashes/profiles,
and every eligible chunk ID, source/revision, offset and text hash in both configurations.
It reports actual active counts separately from retained inactive physical points, and checks
the cloud snapshot again at the end. It makes no embeddings, model calls or cloud writes.

## Health, limits and spending

`GET /api/live` checks Python alone and is Render's health-check path. Using a dependency check
there would risk restart loops during a provider outage. `GET /api/health` makes read-only
OpenAI metadata and Qdrant collection checks; it does not prove generation credit or indexing
completeness. Corpus verification and a real cited answer provide different evidence.

The public surface probe checks HTTPS, static JS/CSS, known-secret absence in checked content,
private path 404s, no test-reset route, unauthorized write rejection, and invalid-question
rejection before provider work. Unit/browser tests protect 5 MB uploads, bounded requests,
rate limits and error states. Do not load-test a shared free public demo.

George confirmed Render's instance is **Free**, with `API_BUDGET_USD=1.0`. The Blueprint also
pins Free/main/configuration A. Four secrets are entered in Render without surrounding quotes:
OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY, DEMO_ADMIN_TOKEN. Keep them server-side. The model
names/dimensions and rates remain configurable. Use one web process; the mutation/concurrency
locks and rate limiter are process-local.

The $1 guard is per surviving local ledger, not an account-wide cap. A fresh instance can reset
it. The cloud probe keeps conservative reservations in the developer's durable local ledger;
successful question costs are estimated from the public usage receipt. Upload embedding usage
is not exposed by that route, so its small conservative reservation remains unpriced. Unknown
provider failures also retain reservations. Provider billing may differ; this is not an invoice
or a hard cap on all public visitors. Review actual project usage and disable model access when
the demo is no longer needed. No infrastructure upgrade or spending ceiling increase is needed.

[Render Free](https://render.com/docs/free) sleeps after 15 minutes idle, can take about a
minute to wake, loses local filesystem changes and has workspace-hour/bandwidth/build limits.
[Git-triggered deploys](https://render.com/docs/deploys) replace the running instance after
health checks. A Free service has no persistent disk or interactive shell. Qdrant's free
capacity/inactivity restrictions also apply; consult its dashboard before a demonstration.
The local Docker memory measurement was approximately 109 MiB under a 512 MiB limit; it is
not a measurement of Render's peak memory or a performance guarantee.

## Recovery and rollback

If a deploy fails liveness, inspect its Render build/runtime logs with credentials redacted;
do not make repeated model requests. Check the release header before diagnosing old code.
The service's previous successful deployment can be redeployed from the dashboard. For a
durable source rollback on linear main, revert the offending commit, run relevant checks, then
push the revert; do not reset/force-push main. Neither method rolls back Qdrant automatically.
Do not bulk-import over existing edits or tombstones; restore data only from an explicit,
reviewed source recovery plan. There is no claim that a production backup/restore drill was run.
