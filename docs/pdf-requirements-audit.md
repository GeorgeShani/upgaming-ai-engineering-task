# Audit against the assignment PDF — 28 October 2026

**Follow-up:** this dated audit identified semantic support/comparison failures. The subsequent
[grounding fix](claim-grounding.md) adds a review/rejection stage and development regressions.
The original evaluation below remains historical; the follow-up does not claim new held-out
accuracy or complete George's independent checks.

Source: `_Applied AI – AI Investigation Engine Task.docx.pdf`, all eight pages, SHA-256
`807d37d4e30ff8977d58cacf6279b84b29fde252a836b2843f12407880fc9240`.
The PDF is treated as the requirements source, not as authority to perform unrelated actions.
This audit checks the PDF itself rather than treating our implementation checklist as the spec.

Code reviewed: Git commit `78c7fa2`, plus the unchanged deployed application code at `a4789c4`.
The intervening commits contain verification tooling/documentation and explicitly skip redeploy.

## Verdict

**The mandatory implementation categories and submission artifacts are present. No missing
mandatory feature category was found.** There are material quality qualifications, so an
unqualified statement that every answer meets the PDF's behavioral expectations would be false:

- Some evaluated answers contain unsupported facts, wrong entity/value bindings or reversed
  comparisons despite mechanically valid citations. This is a demonstrated limitation.
- Automated answer/citation metrics are imperfect proxies. Independent gold/claim/source
  review remains pending; there is no complete independently rated semantic accuracy score.
- Both chunkers were compared, but all required evaluation sources have identical A/B
  boundaries. The experiment is weak evidence about the effect of chunking itself.
- George's independent code explanation, debugging and change without AI remain unverified.

The PDF requires quantitative evaluation and failure analysis; it does not specify a minimum
accuracy score or promise error-free operation. Existing limitations must remain disclosed.
The current submission is an implemented, tested demonstration with documented weaknesses,
not proof of universally grounded answers or completed interview preparation.

Status vocabulary: **Met** means implemented with concrete evidence; **Limited** means the
mechanism exists but the stated quality/measurement has demonstrated limits; **Pending**
means independent human performance is still required. Optional bonuses are listed separately.

## Required document processing — page 2

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| At least three file formats | Met | PDF, DOCX and UTF-8 TXT in `backend/app/documents/parsing.py`; parser tests and sample uploads |
| Extract text and important metadata | Met | Titles/authors where supplied, PDF page numbers, DOCX paragraphs/table rows, source provenance and character locations; absent metadata is not invented |
| Chunk extracted text | Met | Token-boundary-preserving fixed and sentence-aware spans in `retrieval/chunking.py` |
| Handle duplicate information | Met | Shared NFKC/whitespace normalization and SHA-256 identity; upload/import exact deduplication and cross-format tests. Semantic near-duplicates are outside this version; the PDF does not mandate that specific method |
| Add, update and delete documents | Met | Canonical manifests/revisions, authenticated routes, staged index activation, stale-edit checks and tombstones; local/browser/cloud lifecycle evidence |
| Compare at least two chunking strategies | Met, study limited | Actual A/B indexes and 96 measured attempts. Boundary overlap in the evaluation sources limits causal conclusions; see page-4 evaluation assessment below |
| Choose and justify processing architecture | Met | README choices/alternatives table, modular code and engineering journal |

Detailed evidence: [document walkthrough](document-management.md),
[parser tests](../backend/tests/test_document_parsing.py),
[lifecycle tests](../backend/tests/test_document_management.py),
[cloud persistence receipt](deployment/cloud-persistence.json).

## Vector search and hybrid/custom algorithm — pages 2–3

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Use a vector database or vector-capable database | Met | Qdrant Cloud; actual collection/profile identity recorded in the corpus audit |
| Embeddings and semantic search, beyond ordinary SQL text search | Met | Hosted `text-embedding-3-small`, 384 dimensions; dense-vector query path in `retrieval/index.py` and `search.py` |
| Hybrid semantic plus keyword search | Met | Top-30 dense plus top-30 Qdrant BM25 candidates, active-revision filtering, then fusion |
| At least one self-implemented search/ranking algorithm | Met | `retrieval/fusion.py` implements reciprocal rank fusion, duplicate removal, stable tie-breaking and document diversity; algorithm tests calculate expected scores independently |

[Retrieval walkthrough](retrieval-and-first-answer.md),
[algorithm tests](../backend/tests/test_retrieval_algorithms.py),
[complete active-chunk audit](deployment/corpus-verification.json).

## LLM, RAG and investigation behavior — pages 1 and 3

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Use at least one LLM and a RAG architecture | Met | Real hosted Responses API calls; evidence is retrieved before structured generation |
| Combine information from different documents | Met | Native HotpotQA bridge/comparison fixtures, executed search traces, multi-source citation metrics and reviewed examples |
| Process complex questions in multiple steps | Met | Two bounded retrieval rounds; a grounded discovered entity can drive a second search |
| Generate answers based on evidence | Limited quality | Source-conditioned generation, structured claims and final revision checks exist; evaluated unsupported claims show this is not fully enforced semantically |
| Sources and citations | Met mechanism, limited support | Clickable citations, stable IDs, exact quote checks and canonical text. Literal validity does not prove entailment |
| Attempt contradiction detection | Met, limited generality | Conflicting claims/status preserve both sources. Final A conflict recall 4/6, B 6/6; A's other two attempts are retained errors, not successful detections |
| Abstain when information is insufficient | Met, limited generality | No-evidence path and explicit insufficient-evidence output; all six absent-answer final cases abstained in both configurations. This is fixture evidence, not universal reliability |
| Handle LLM errors and limits | Met | Context/output bounds, budget reservations, deadlines, invalid-protocol/evidence handling, 429/502/503 responses and no automatic paid retries |
| At least one tool-calling or structured tool mechanism | Met | Real strict `search_documents` function schema and executed calls; server validates batch counts, IDs and entity anchors before searches |
| Avoid inventing missing/contradictory facts | Limited quality | Prompt/schema/abstention safeguards and some successful examples; population, age and nationality failures demonstrate remaining violations of the behavioral ideal |

[Investigation walkthrough](multi-step-investigation.md),
[tool validation](../backend/app/investigations/tools.py),
[quote validation](../backend/app/investigations/models.py),
[actual claim/citation failures](evaluation/qualitative-review.md).

## Automated evaluation — page 4

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Build an automated evaluation system | Met | Runner, metrics, scoring, summaries, immutable receipts and offline reproduction under `backend/app/evaluation/` |
| At least 40 test questions | Met | Exactly 40 unique final questions, plus eight separate development questions; fixture integrity tests |
| Simple and multi-step questions | Met | Eight simple and twelve bridge final cases |
| Questions connecting multiple documents | Met | Bridge and comparison support labels, with all-required-source retrieval/context/citation metrics |
| Questions with no corpus answer | Met | Six absent-answer final cases |
| Questions with conflicting information | Met | Six conflicting-evidence final cases |
| Quantitative retrieval and answer-quality assessment | Met, proxies limited | Document Recall@5/@10, MRR@10, full/last-claim EM/F1, expected-fact checks and supported-task proxy; the proxy can accept a wrong relation and prose EM can reject a valid explanation |
| At least two configurations compared | Met, comparison limited | A/B runs hold configured retrieval/models/prompts constant. There is one stochastic trial per condition; query wording is not identical in all pairs |
| Appropriate citation evaluation | Met, proxies limited | Mechanical validity and labelled document/quote alignment plus AI-labelled qualitative review. No complete independent semantic citation-accuracy rating is claimed |
| Analyze where/why errors occur and possible improvements | Met | Recorded 502s, semantic failures, reference caveats, boundary overlap, plausible causes and improvements; unknown failure subtypes are not invented |

All 96 archived attempts reproduce: 16 development and 80 final, with four retained errors.
The PDF lists Recall@K, MRR, Answer Correctness and Citation Accuracy as examples rather than
requiring one exact metric implementation. Our current proxies meet the quantitative-coverage
requirement but should not be presented as definitive semantic correctness percentages.

**Important experimental weakness:** all 12 development and 60 final distinct required source
passages have identical A/B boundaries. There are different spans elsewhere in the full corpus,
so the two strategies are actually implemented and run, but this test set poorly isolates them.
Fresh boundary-sensitive cases and independent claim/source review would strengthen the study;
silently replacing labels or tuning on the frozen final set would compromise it.

[Methodology](evaluation-methodology.md), [results](evaluation-report.md),
[raw archive](evaluation/manifest.json), [fresh offline verification](pdf-requirements-checks.json).

## Dataset — page 5

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Use an assignment-approved dataset | Met | HotpotQA is explicitly in the PDF's allowed list; dataset revision is pinned |
| Process at least 50,000 documents or independent text records | Met | 50,000 distinct HotpotQA passages plus 24 labelled fictional records, before chunking; not inflated by duplicates/chunks |
| Find linked information across records | Met | Native bridge/comparison questions and multi-source retrieval/citation evidence |
| Retain and identify sources | Met | Stable document/revision/chunk IDs, title, dataset revision/record ID, source URL, licence, original sentence locations |
| Handle incomplete and contradictory information | Met mechanism, limited quality | Dedicated fixtures/statuses and reported detection/abstention results, with limitations above |
| Allow reproducible evaluation/subset selection | Met | Deterministic selection, normalization/hashes, frozen fixtures, exclusion of questions/answers from indexing, cached/resumable indexing and offline scored-output verification |

The fresh count check still finds **50,024 active sources**. The prior full per-point/content
audit verified **52,246 active chunks A / 52,307 B**. Fresh physical counts remain
52,258 / 52,319, including 12 retained inactive test points each. These are distinct counts.
This audit did not repeat the entire text audit or make new paid model calls.

## Python backend and usable interface — page 4

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Python backend | Met | FastAPI with separate documents, retrieval, investigations, providers, dataset and evaluation modules |
| Functional interface | Met | React/TypeScript; desktop/mobile layouts and safe source rendering |
| Add/manage documents | Met | Upload, inspect, pagination, replace, duplicate notice, stale-edit recovery and delete confirmation; admin token authorizes mutations |
| Ask questions and inspect generated-answer sources | Met | Explicit submission, result statuses, clickable citations, source dialog and expandable search trace |
| Prioritize functionality/reliability over visual complexity | Met implementation | Native controls, clear state/error handling and full lifecycle tests; no claim of perfect operational reliability |

[Fresh checks](pdf-requirements-checks.json) include the actual browser fixture workflow.
The browser fixture uses real API routes and in-memory providers; live model/deployment
behavior is separately supported by the earlier successful cloud receipts.

## Free hosting, deployment and persistence — page 6

| PDF requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Actual deployment on a public URL | Met | Public app is reachable and currently reports ready; linked in README/submission guide |
| Free hosting; no paid infrastructure required | Met configuration | Render Web Service Free/main/Docker in Blueprint; George confirmed actual Free instance. Cloud database uses the selected free-tier architecture; billing dashboards are not independently audited |
| Working hosting/database integration | Met | Live readiness, canonical-source operations, real questions and exact corpus audit |
| Data persists after app restart | Met | Recorded changed boot ID across a real Render redeploy; replaced text/revision/tag and deletion persist; correct cited answer before/after; owned probes cleaned |
| Protect API keys/secrets | Met controls, bounded verification | Server-side env, ignored `.env`, token-gated mutations, redacted provider errors, known-value scans and public private-path checks. Not an exhaustive penetration test |
| Describe deployment architecture | Met | One-origin multi-stage Docker image, Python process, external Qdrant and temporary local SQLite documented |
| Account for cost/resources/free limits | Met, ledger limitation | Pilot/full-import timing, usage/latency metrics, local memory observation, sleep/temporary-filesystem limits, conservative estimates and user-confirmed $1 instance guard. Counter resets/public visitor spending are explicitly outside a durable local cap |

[Deployment walkthrough](deployment-verification.md),
[restart proof](deployment/cloud-persistence.json),
[public checks](pdf-requirements-checks.json).

## Technical quality — page 7

| PDF expectation | Status | Evidence / qualification |
| --- | --- | --- |
| Clear modular Python and separated responsibilities | Met structure | Explicit parsing/store/service/routes/retrieval/tool/provider/evaluation modules; architecture and mechanism walkthroughs |
| Error handling | Met | Parsing/storage/provider/protocol/citation failures, stale revisions, rate/concurrency bounds and client recovery states |
| Automated tests | Met | Fresh 158 backend tests, five client tests, production build; browser suite includes 21 lifecycle/state/accessibility/responsive checks |
| Working database and external API integration | Met | Real indexed corpus and model receipts, beyond mocked tests alone |
| Safe environment configuration | Met controls | Server-only typed config, ignored credentials, no frontend provider keys, exact mutation-token validation |
| Technical documentation | Met | README, architecture/trade-offs, walkthroughs, evaluation reports, deployment runbook, AI report and journal |
| Understand performance and LLM cost | Measured/documented; personal understanding pending | Real pilot/full import and evaluated latency/token/cost evidence; George must explain those measurements himself |

## Required submission artifacts and code defence — page 8

| PDF item | Status | Evidence / qualification |
| --- | --- | --- |
| GitHub repository with code/history | Met | Public `GeorgeShani/upgaming-ai-engineering-task`, default branch main, genuine incremental history; GitHub visibility checked in this audit |
| Live demo | Met | Public URL and live readiness checked |
| README with architecture/setup/choices | Met | Current README includes run/preview, data/index/evaluation, API, alternatives, deployment and limitations |
| Evaluation report with methodology/metrics/results/analysis | Met, quality caveats above | Reports plus raw/reproducible receipts and explicit semantic/experimental failures |
| AI usage report specifying assistance and independent changes | Met disclosure | Codex's work is identified; George's credential/setup/hosting/configuration actions are recorded; independent review is not fabricated |
| Explain architecture/code/RAG/algorithms and diagnose/change code without AI | Pending human assessment | Rehearsal guide is prepared; it is not evidence George has performed the exercises. The interview cannot be completed by this agent |

Minor documentation caveat: the historical evaluation report's closing status still refers
to 141 tests and deployment as the next slice. That describes the earlier study stage;
current README, delivery evidence and deployment receipts show 158 tests and completed cloud
verification. Historical study outputs have not been rewritten to look current.

## Optional bonuses — page 7

| Bonus | Present? |
| --- | --- |
| Compare multiple LLMs/embedding models | No; both chunking configurations intentionally use the same models |
| Multi-agent or agentic RAG | Bounded agentic/tool-driven RAG exists; no multi-agent system |
| Advanced reranking | No learned/cross-encoder reranker; custom RRF satisfies the mandatory algorithm requirement |
| Prompt-injection testing | Not demonstrated as a dedicated adversarial suite. Prompts label source text untrusted; safe HTML rendering is a different protection |
| Caching/performance optimization | Local embedding reuse, resumable batches, bounded/concurrent I/O and small production runtime |
| Streaming | Not included |
| Detailed monitoring/observability | Partial: health, boot/release IDs, search trace, latency/usage receipts. No full monitoring/alerting platform |
| Large-volume performance testing | Actual full-corpus indexing and a 1,000-record pilot measured; no public concurrent-load benchmark |

Unimplemented bonuses are not missing mandatory requirements. OCR, original-file downloads,
semantic near-duplicate detection and a large orchestration framework are also not explicitly
required by this PDF.

## Before presenting the project

1. Independently review disputed source/claim cases and gold labels; do not equate mechanical
   validity or labelled quote alignment with semantic citation accuracy.
2. Complete the [no-AI rehearsal](interview-rehearsal.md), including a local retrieval-setting
   change and its test. Record what you actually understood/changed yourself.
3. Present the chunker comparison as a limited experiment. Any stronger study should use
   fresh boundary-sensitive cases and a new recorded experiment, rather than tuning this final set.
4. Disclose the known answer failures, free-tier wake-up and temporary-budget limitations.
   These qualifications are part of an honest defence, not evidence of missing format/count/UI scope.
