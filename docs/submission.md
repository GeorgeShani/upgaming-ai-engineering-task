# Submission and handoff

Repository: https://github.com/GeorgeShani/upgaming-ai-engineering-task

Live demo: https://upgaming-ai-engineering-task.onrender.com/

The repository contains the implementation, genuine incremental commit history and technical
reports. Review the independent rehearsal before presenting it as work you can defend.

The subsequent [grounding fix](claim-grounding.md) adds a separate claim review and numeric
comparison checks. Its development and deployed-release receipts are in
[grounding verification](grounding-verification.json). The archived comparative study still
measures the earlier workflow; these regressions do not replace a new held-out evaluation.

## Deliverables

| Required artifact | Location |
| --- | --- |
| Code, setup, architecture and trade-offs | [README](../README.md), source modules, [journal](engineering-journal.md) |
| Actual public application | Live URL above; [deployment walkthrough](deployment-verification.md) |
| Corpus provenance/counts | [Preparation report](dataset-preparation-report.json), [fixture conventions](../fixtures/README.md) |
| Two chunking configurations, hybrid retrieval and custom algorithm | [Retrieval walkthrough](retrieval-and-first-answer.md) and `backend/app/retrieval/` |
| Comparative methodology, metrics, raw outputs and limitations | [Evaluation report](evaluation-report.md), [methodology](evaluation-methodology.md), [archive](evaluation/manifest.json) |
| Honest AI assistance record | [AI usage report](ai-usage-report.md), [engineering journal](engineering-journal.md) |
| Independent code defence/practice | [Rehearsal guide](interview-rehearsal.md); George's completion remains pending |

## Requirement map

| Requirement | Implementation / evidence |
| --- | --- |
| PDF/DOCX/TXT, locations, provenance and exact duplicates | `documents/parsing.py`, parsing/lifecycle tests, [document walkthrough](document-management.md) |
| Create/list/inspect/replace/delete and canonical text separate from chunks | Document routes/service/store; activation and stale-edit tests |
| At least 50,000 distinct passages before chunking | 50,000 HotpotQA + 24 labelled fictional sources; `verify_deployment_corpus.py` audits cloud content |
| Two chunkers and semantic/keyword search | `retrieval/chunking.py`, `index.py`, `search.py`; A/B reports |
| Custom ranking algorithm | `retrieval/fusion.py`, tested RRF k=60 and per-document cap |
| Multi-step tool use, references, missing/conflicting information | `investigations/` modules; real development checks, frozen final attempts and limitations |
| Frontend and API | React workflows and FastAPI `/docs`; browser smoke tests |
| Cloud persistence and protected secrets | Two-phase cloud restart probe; public surface and corpus audits; ignored root `.env` |
| Bounded model usage and free infrastructure | One Docker web process, external Qdrant; conservative local ledger and documented reset limitation |
| Reproducible evaluation and honest failures | 96 archived attempts, four retained errors; offline score/integrity checker |

The final cloud/check evidence is stored under `docs/deployment/`; follow the actual receipt's
scope and timestamps. Historical local/image/evaluation reports are preserved, including
failures and later deployment-only changes. A historical report does not claim its original
source-byte identity matches today's entire backend.

## Before sharing

1. Open the public URL early enough for Render Free to wake. Confirm Service connections,
   browse a source and return to Investigate. Never include the admin token or provider keys
   in the submission, screenshots or the browser URL.
2. Use the development example for a live demonstration, and submit once. Open the citation,
   read its quote and canonical source, then inspect the executed search trace. This costs
   API credit; it is separate from the free fixture tests and offline archive checker.
3. Explain one successful multi-source example and one documented failure. Do not present a
   mechanical citation-validity percentage as semantic accuracy.
4. Run the independent rehearsal. Record your own explanations/change/test; leave unresolved
   learning items unchecked. Confirm the working tree is clean before sharing the commit.
5. Review provider usage and the public demo's availability near the interview. The $5 target
   and $1 instance guard are not a durable shared billing cap. Do not publish credentials to
   give reviewers mutation access; coordinate any separate access directly yourself.

## Known limitations to disclose

Conflict detection can miss distinctions or preserve claims that are not truly contradictory.
Literal quotes can support the wrong relationship. Some automatic expected-fact checks can
pass an incorrect answer, while prose EM/F1 can fail a correct paraphrase. Required sources
have identical A/B boundaries in this study, limiting its ability to isolate chunker quality.

The corpus and canonical extracted text are public. There is no private workspace, OCR,
original binary download, semantic near-duplicate detector or production backup/restore drill.
Locks/rate limits assume one process. Render's temporary ledger can reset; the service may
sleep. Inactive vectors are retained but excluded by manifests. Future work should prioritize
semantic claim/support evaluation, boundary-sensitive fresh cases and durable shared budgets
before optional streaming or extra models.

No claim is made that George independently authored or reviewed every line. The AI report
identifies the assistance, while the checklist distinguishes verified software from learning.
