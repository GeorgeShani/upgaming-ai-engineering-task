# Implementation checklist

Keep implementation verification separate from George's learning review. A checked code item
does not claim that George has completed his review. Estimates are focused working time.

## Session 1: Skeleton and early deployment (1 hour)

- [x] Save the accepted plan and committed learning workflow.
- [x] Implement React -> FastAPI -> read-only dependency checks.
- [x] Verify backend tests, frontend build, and actual browser behaviour.
- [x] Commit the verified local foundation.
- [x] Set up real OpenAI and Qdrant credentials; verify provider access.
- [x] Publish the first Render deployment and verify its public page and dependency readiness.
- [ ] George: run locally, trace a health request, explain liveness vs dependency readiness.

## Session 2: Corpus and evaluation fixtures (2 hours; explicitly started by George)

- [x] Deterministic HotpotQA selection with revision, hashes, and >=50,000 distinct source records.
- [x] Clearly labelled synthetic incident corpus.
- [x] Freeze 40 final questions (8 simple / 12 bridge / 8 comparison / 6 absent / 6 conflict).
- [x] Separate development examples; prevent questions/answers/labels entering the corpus.
- [ ] George: verify gold answers/support and explain records versus chunks.

## Session 3: Document lifecycle (2 hours; depends on 2)

- [x] PDF/DOCX/TXT extraction, provenance, locations, exact deduplication, 5 MB limit.
- [x] Persistent canonical documents, listing, inspection, replacement, and deletion.
- [x] Revision eligibility gate rejects inactive/deleted candidates after failures; mutation admin token.
- [x] Tests protect parsing, duplicates, replacement, and deletion.
- [ ] George: trace a document through the lifecycle.

## Session 4: Chunking and retrieval (2 hours; depends on 3)

- [x] Two specified token/sentence chunkers with boundary and location tests.
- [x] Dense and BM25 sparse retrieval plus tested custom RRF and document diversity cap.
- [x] Benchmark 1,000 records, estimate resources/cost, start resumable bulk indexing.
- [ ] George: calculate RRF and explain rank versus confidence.

## Session 5: First cited answer (2 hours; depends on 4)

- [x] End-to-end real retrieval and generation with structured evidence references.
- [x] Validate citation IDs and quote text; test invalid evidence rejection.
- [ ] George: inspect every citation in one answer and identify the model's context.

## Session 6: Multi-step investigation (2 hours; depends on 5)

- [x] Real validated search tool; <=2 rounds and <=3 searches.
- [x] Follow-up entity search, conflicts, abstention, provider errors, bounded retries/context.
- [x] Investigations are rate-limited; usage and cost recorded.
- [ ] George: demonstrate and explain multi-step, conflicting, absent, and failing cases.

## Session 7: Complete React workflows (2 hours; depends on 6)

- [x] Upload/list/inspect/replace/delete UI, question form, status, citations, search trace.
- [x] Loading/error/empty states and safe document rendering.
- [x] Browser smoke test: upload -> ask -> open citation -> delete.
- [ ] George: run the entire workflow and distinguish errors from evidence limitations.

## Session 8: Comparative evaluation (2 hours; depends on 7 and completed indexes)

- [x] Choose deployment config from development examples before final results.
- [x] Run both chunking configurations with otherwise identical settings.
- [x] Save raw results and required metrics, cost/latency, failure analysis, reproduction commands.
- [ ] George: explain metrics and manually review disputed citations.

## Session 9: Deployment verification (1 hour; depends on 8)

- [x] Confirm 50,024 unique records and all 52,246 A / 52,307 B active chunks, including content/revision identity.
- [x] Recreate the actual Render process and confirm uploaded/updated/deleted data and cited retrieval persist correctly.
- [x] Verify public workflows, known-secret redaction, upload limits, user-confirmed Free/$1 configuration and recorded budget; document reset/public-traffic limitations.
- [ ] George: reproduce restart checks.

## Session 10: Delivery and rehearsal (2 hours; depends on 9)

- [x] Final README, architecture/trade-offs, demo URL, evaluation report, AI usage, journal and submission/rehearsal guides.
- [x] Meaningful GitHub history and reproduction instructions, with final checks and frozen evaluation scores reproduced.
- [ ] George: explain pipeline, calculate fusion, diagnose retrieval, change a setting/test without AI.

## Contingency (2 hours)

- [x] Follow-up: support review, numeric comparison checks, development regressions and an honest account of remaining semantic limits (`docs/claim-grounding.md`).
- [ ] George: inspect a rejected and an accepted draft, and explain why arithmetic cannot establish the meaning of a claim.

- [ ] Use for unmet requirements or misunderstandings before optional features.
