# AI Investigation Engine: 48-hour implementation and learning plan

Status: accepted plan; implementation proceeds one reviewed slice at a time.

## Outcome and working agreement

Build a demonstrable investigation engine that meets the assignment's core requirements and
that George can explain, debug, and modify independently. The assignment permits AI assistance,
requires an AI usage report, and includes an interview without AI assistance.

AI drafts one small slice. George reviews it, runs it, traces its behaviour, and explains it
before the next slice. A working implementation alone does not complete the learning checkpoint.
Do not implement all ten sessions in one autonomous pass.

Budget: 18 focused hours, 2 contingency hours, 28 hours for sleep, breaks, meals, and unattended
processing. This is an ambitious assisted build, not a promise of mastery in two days.

- Keep the checklist in `tasks/todo.md` and explanations in `docs/engineering-journal.md`.
- Commit each verified slice with a meaningful message. Record actual history, not invented effort.
- Defer visual polish, streaming, multiple models, and other bonuses until mandatory work is done.

## Architecture and trade-offs

React + TypeScript + Vite -> FastAPI -> document processing / investigation -> Qdrant + OpenAI.

| Decision | Reason | Alternative and drawback |
| --- | --- | --- |
| React and TypeScript | Familiar frontend tools | Gradio saves time but offers less frontend/API integration practice |
| FastAPI and explicit Python modules | Clear responsibilities | Large orchestration frameworks add abstractions to learn and defend |
| Qdrant Cloud | Persistent text, metadata, dense and sparse indexes | PostgreSQL + pgvector adds setup and capacity decisions |
| Hosted embeddings | Avoid local model memory on a free server | Local models save API fees but add operational work |
| Bounded investigation | Follow evidence with predictable limits | Unrestricted agents make cost and failure harder to control |
| Custom reciprocal rank fusion | Small, explainable, testable algorithm | Raw score addition mixes scales; built-in fusion alone is insufficient |

Models: `text-embedding-3-small`, 384 dimensions; `gpt-5.4-mini-2026-03-17` for generation and tools.
Make models configurable and record actual settings in evaluation runs.

Deploy one FastAPI process serving the React build on Render Free. Keep canonical extracted text,
metadata, and indexes in Qdrant Cloud Free. App restart must not erase data. No Redis, separate
worker service, local LLM, or separate frontend deployment. Document sleep, inactivity, memory,
and quota restrictions. The API spending target is $5, not a provider-enforced hard cap.

## Required implementation behaviour

### Corpus and lifecycle

- Use HotpotQA with a reproducible selection of at least 50,000 distinct source passages before
  chunking. Record revision, selection procedure, hashes, and counts. Duplicates and chunks do
  not inflate document counts.
- Add clearly labelled fictional incident documents covering changes, affected services,
  contradictory reports, and missing information.
- Upload PDF, DOCX, and TXT; import dataset records through a separate local command.
- Preserve titles, provenance, page/paragraph locations, and original sentence IDs where possible.
- Normalize and hash text for exact duplicate handling. Report duplicates; semantic near-duplicate
  detection is outside this version.
- Create, list, inspect, replace, and delete documents. Keep canonical text separate from chunks.
- Prepare replacement chunks before activating a revision. Exclude deleted/inactive revisions
  from retrieval, even after interrupted operations. No OCR or original binary download feature.
- Bulk indexing is resumable and local, never a public HTTP bulk job.

### Chunking and retrieval

- A: fixed 256-token windows, 40-token overlap.
- B: sentence-aware groups targeting 256 tokens, one sentence overlap; split oversized sentences.
- Compare over the same corpus with the same embedding model and retrieval settings.
- Retrieve 30 dense semantic and 30 BM25 sparse keyword candidates.
- Implement RRF: score(chunk) = sum(1 / (60 + rank_in_each_list)); use one-based ranks,
  stable tie-breaking, and deduplication.
- Select up to eight evidence chunks, at most two per document. Scores express rank, not truth.

### Investigation and API

- Expose `search_documents` as a real LLM tool with validated arguments.
- Maximum two retrieval rounds and three searches total; a later search may follow an entity.
- Return answer, evidence references, conflicting claims, and status `answered`,
  `insufficient_evidence`, or `conflicting_evidence`.
- Require evidence for factual claims. Validate reference IDs and quote substrings. Measure
  semantic support separately: a real quote does not necessarily support a claim.
- Show conflicts together. Do not infer causation solely from timing.
- Bound context, output, model calls, retries; distinguish provider failures from absent evidence.

| Endpoint | Purpose |
| --- | --- |
| GET /api/live | App process liveness for hosting, without provider calls |
| GET /api/health | Dependency access checks; final readiness expands as indexing is built |
| POST /api/documents | Upload and index a small document |
| GET /api/documents | Paginated listing |
| GET /api/documents/{id} | Metadata and canonical text |
| PUT /api/documents/{id} | Replace |
| DELETE /api/documents/{id} | Delete |
| POST /api/investigations | Structured question and evidence result |

React: document management, question form, answer status, clickable citations, expandable search
trace. Trace exposes searches/evidence, not hidden reasoning. Protect mutations with a server-side
demo admin token. Limit uploads to 5 MB; rate-limit investigations; render document text safely.
Keep credentials server-side.

## Sessions and checkpoints

Work in 60-90 minute stretches, with breaks within longer blocks. Run unattended indexing and
evaluation during pauses. Measure 1,000-record throughput and cost before the full indexing run.

| Session | Deliverable | Hours | Understanding checkpoint |
| --- | --- | --- | --- |
| Day 1, 1 | Skeleton and early deployment | 1 | Trace browser -> Python -> external services |
| 2 | Corpus and evaluation fixtures | 2 | Records vs chunks, provenance, evaluation leakage |
| 3 | Parsing and document management | 2 | Trace one document's lifecycle |
| 4 | Two chunkers and hybrid retrieval | 2 | Calculate fusion by hand; start bulk indexing |
| 5 | First cited answer | 2 | Inspect every citation and the model's actual context |
| Day 2, 6 | Multi-step investigation and reliability | 2 | Second search, conflict, abstention, bounded errors |
| 7 | Complete React workflows | 2 | Upload, inspect, replace, delete, ask, view evidence |
| 8 | Comparative evaluation | 2 | Explain metrics and inspect failures |
| 9 | Deployment verification | 1 | Restart persistence, secrets, limits, public access |
| 10 | Documentation and interview rehearsal | 2 | Explain pipeline and change code without AI |
| Reserve | Resolve failures before bonuses | 2 | Prioritize incomplete mandatory requirements |

Journal entries contain: what changed; why; alternative and drawback; concrete mechanism;
verification and failures; George's own understanding/questions; AI contribution; resume point.
Never fill George's understanding section on his behalf.

## Evaluation and delivery

Freeze 40 final questions: 8 simple, 12 bridge, 8 comparison, 6 unanswerable, 6 conflicting.
Keep development examples separate. George verifies reference answers and support passages.
Include supporting documents in the corpus; never index questions, answers, or support labels.

Select the deployed chunking configuration using development examples before final evaluation.
Compare A/B with corpus, prompts, retrieval settings, and models held constant.

Report document Recall@5/10, MRR, complete multi-source retrieval; normalized exact match/token
F1 for short answers and expected-fact checks for composed answers; citation validity/accuracy
against labelled support with manual dispute review; abstention/conflict results; latency,
tokens, API cost, document/chunk counts; representative failures and improvements.

Test parsing/locations, chunk boundaries, duplicates, fusion, replacement/deletion, citations,
tool limits, and provider errors. Browser smoke: upload -> question -> citation -> delete.

Estimate both indexes before bulk work. Keep resumable embedding caches, record usage, and stop
batch work before exhausting the remaining $5 target. Provider alerts are not a hard cap.

Deliver GitHub code/history, public demo, README, evaluation methodology/raw results/report,
reproduction instructions, honest AI usage report, and committed journal.

Rehearse without AI: explain the pipeline, calculate RRF, diagnose failed retrieval, and change
a retrieval setting with its test. Document weaknesses in conflict detection and citation support.

## References

- Assignment: `_Applied AI – AI Investigation Engine Task.docx.pdf`, supplied by George.
- https://huggingface.co/datasets/hotpotqa/hotpot_qa
- https://developers.openai.com/api/docs/guides/embeddings
- https://developers.openai.com/api/docs/models/gpt-5.4-mini
- https://render.com/docs/free
- https://qdrant.tech/documentation/cloud/create-cluster/
