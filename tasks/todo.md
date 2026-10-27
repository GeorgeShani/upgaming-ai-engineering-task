# Implementation checklist

Keep implementation verification separate from George's learning review. A checked code item
does not claim that George has completed his review. Estimates are focused working time.

## Session 1: Skeleton and early deployment (1 hour)

- [x] Save the accepted plan and committed learning workflow.
- [x] Implement React -> FastAPI -> read-only dependency checks.
- [x] Verify backend tests, frontend build, and actual browser behaviour.
- [x] Commit the verified local foundation.
- [x] Set up real OpenAI and Qdrant credentials; verify provider access.
- [ ] Publish the first Render deployment and verify its public URL.
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

- [ ] Real validated search tool; <=2 rounds and <=3 searches.
- [ ] Follow-up entity search, conflicts, abstention, provider errors, bounded retries/context.
- [ ] Investigations are rate-limited; usage and cost recorded.
- [ ] George: demonstrate and explain multi-step, conflicting, absent, and failing cases.

## Session 7: Complete React workflows (2 hours; depends on 6)

- [ ] Upload/list/inspect/replace/delete UI, question form, status, citations, search trace.
- [ ] Loading/error/empty states and safe document rendering.
- [ ] Browser smoke test: upload -> ask -> open citation -> delete.
- [ ] George: run the entire workflow and distinguish errors from evidence limitations.

## Session 8: Comparative evaluation (2 hours; depends on 7 and completed indexes)

- [ ] Choose deployment config from development examples before final results.
- [ ] Run both chunking configurations with otherwise identical settings.
- [ ] Save raw results and required metrics, cost/latency, failure analysis, reproduction commands.
- [ ] George: explain metrics and manually review disputed citations.

## Session 9: Deployment verification (1 hour; depends on 8)

- [ ] Confirm >=50,000 actual unique records and expected chunk counts.
- [ ] Restart app and confirm uploaded/updated/deleted data persists correctly.
- [ ] Verify public workflows, secrets, free-tier restrictions, and spending target.
- [ ] George: reproduce restart checks.

## Session 10: Delivery and rehearsal (2 hours; depends on 9)

- [ ] Final README, architecture/trade-offs, demo URL, evaluation report, AI usage, journal.
- [ ] Meaningful GitHub history and complete reproduction instructions.
- [ ] George: explain pipeline, calculate fusion, diagnose retrieval, change a setting/test without AI.

## Contingency (2 hours)

- [ ] Use for unmet requirements or misunderstandings before optional features.
