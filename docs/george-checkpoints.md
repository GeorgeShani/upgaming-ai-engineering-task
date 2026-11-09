# Worked resolutions for the eleven George checkpoints

Prepared 9 November 2026 using engineering-partner guidance. Every original `George:` item
in [todo](../tasks/todo.md) has a resolution here, a repeatable check and an independent
completion criterion. **Codex completed the assisted work; George's personal understanding,
manual review and no-AI performance have not been observed.** The unchecked personal items
therefore remain unchecked, alongside checked assisted-work items. Generating these answers
does not certify the interview exercises.

Fresh mechanical evidence: [checkpoint receipt](learning-checkpoints/verification.json).
The script uses real local FastAPI routes with in-memory HTTP provider/storage fakes. No real
credentials, model calls or cloud mutations are involved. Historical real-model/cloud receipts
are separately labelled. A recreated local application is not an operating-system or Render restart.

Run the free demonstration from the repository root:

```powershell
uv run python scripts/verify_learning_checkpoints.py
uv run pytest -q -W error
cd frontend
npm run test:browser
```

The first command produces local evidence under ignored `artifacts/learning-checkpoints/`.
The copies linked below preserve this run. Personal interview question banks, coding practice
and rehearsal notes are local-only ignored files; they are not required to follow this guide.

<a id="checkpoint-1"></a>

## 1. Run locally, trace health, explain liveness/readiness

**Worked answer:** React initiates a browser request using `frontend/src/api.ts`. During local
development/preview, Vite forwards `/api` to FastAPI on port 8000. In production, FastAPI also
serves compiled React assets, so UI and API share the public origin. Vite preview alone does
not start Python.

From the root, install locked dependencies if needed and start Python:

```powershell
uv sync --frozen
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run preview
```

Open `http://127.0.0.1:4173`, then inspect the Network panel for `/api/health`. For direct checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/live
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

`/api/live` checks that Python responds; it does not contact providers. `/api/health` invokes
`check_health` in `backend/app/health.py`: read-only access checks for the two configured OpenAI
models plus Qdrant collections. Ready returns HTTP 200; missing/unavailable dependencies return
503 with safe messages. This does not prove generation credit, corpus completeness or answer quality.

**Verified:** The isolated app returns 200 for liveness and ready health. Existing foundation
tests also exercise unconfigured dependencies, provider rejections and timeouts without secret leaks.

**George's remaining demonstration:** Run the two terminals yourself, identify one browser
request and explain why the process can be alive while a dependency is unavailable.

<a id="checkpoint-2"></a>

## 2. Verify reference answers/support; explain records versus chunks

**Worked answer:** A record is a distinct normalized canonical source passage. Chunks are
derived overlapping retrieval units; multiple chunks do not create additional independent
sources. The recorded corpus has 50,000 HotpotQA sources plus 24 fictional sources before chunking.
The two chunkers produce different overall counts; duplicates and overlap do not inflate source counts.

**Verified:** `load_fixtures` checks the frozen file hashes, canonical IDs/text/locations, case
structure and each labelled supporting quote. This run checked **48 cases and 72 fixture source
documents**. Those 72 support documents are a fixture subset, not the full 50,024-source corpus.
The [full reference worksheet](learning-checkpoints/gold-reference-worksheet.md) includes every
question, expected outcome, reference answer, source title, original sentence and quote.

For semantic review, read the question and support together. Preserve these known caveats:

| Case | Resolution / qualification |
| --- | --- |
| final-bridge-01 | “What government position?” can admit more roles than the single Chief of Protocol reference. |
| final-bridge-03 | A city-only New York City answer may be correct while missing the frozen neighborhood phrase. |
| final-bridge-05 | The Aladin source already states the former consultancy role; requiring a generic definition source is conservative. |
| final-bridge-06 | Distinguish 4,000 total capacity from 3,677 seated; “seat” favors the latter. |
| final-bridge-07 | The frozen category is bridge, but the wording compares birth dates; do not silently recategorize the measured set. |
| final-bridge-12 | “Country” is a typo relative to Brown County, Kansas; its 9,984 is a 2010 county figure, not a national/current population. |
| final-comparison-04 | “Used for real estate” is ambiguous; the narrow reference interpretation is not the only reading. |
| final-comparison-06 | British does not establish English origin; nationality alone does not establish birthplace. |
| final-comparison-07 | Listed roles and “multi-instrumentalist” do not establish exact instrument-count ratios. |

These are AI-assisted source-relative findings, not George's independent approval. Original
labels remain frozen. See [pre-final reference caveats](evaluation-reference-caveats.md).

**George's remaining demonstration:** Review the worksheet, explain at least these disputed
labels in your own words and record genuine disagreements. A corrected benchmark would need
a versioned change and a fresh evaluation; do not silently improve historical scores.

<a id="checkpoint-3"></a>

## 3. Trace a document through its lifecycle

**Worked trace, freshly executed using isolated API routes:**

1. Upload `A fictional source fact.` as TXT. Parsing retains a paragraph location; normalized
   text receives a stable source identity; a revision and A/B chunks are indexed. HTTP 201.
2. Upload the same text again. The existing source is returned with `duplicate=true`, HTTP 200.
3. Read its exact revision tag and replace the text with `A changed source fact.`. The source
   ID stays stable for the managed document; the active revision changes. New chunks become
   eligible only when the revision is activated.
4. Attempt another replacement with the old tag. HTTP 412 rejects the stale write.
5. Ask a question. The answer cites the changed text/current revision, not superseded chunks.
6. Delete the source. Reads return 404; the source is excluded from retrieval even if old
   vectors physically remain. With no active source, the isolated question abstains.

The concrete document/revision IDs and returned answer are in `local_api.document_trace` in
the [receipt](learning-checkpoints/verification.json). Starting code: `documents/parsing.py`,
`documents/service.py`, `documents/routes.py`, `retrieval/search.py`.

**Why staged revisions?** Preparing replacement chunks first avoids making an incomplete
index visible. The trade-off is retained inactive data and lifecycle bookkeeping rather than
a single database transaction spanning every operation.

**George's remaining demonstration:** Point to normalization, revision activation and active
filtering, then explain what a failed preparation or concurrent edit would expose to readers.

<a id="checkpoint-4"></a>

## 4. Calculate fusion and explain ranking versus confidence

**Worked calculation:** For A at dense rank 1 / keyword rank 3,
`1/61 + 1/63 = 0.0322664585`. For B at ranks 2 / 1,
`1/62 + 1/61 = 0.0325224749`. B ranks ahead of A.

Ranks start at one. A missing list contributes zero. Repeated IDs within one list count once,
and the next unique item receives the next rank. Total ties break by string chunk ID.
Production then selects up to eight chunks with at most two from one document.

**Why:** Dense and BM25 scores use different scales. Rank fusion combines relative positions
without treating raw scores as comparable. The constant 60 dampens rank differences. Neither
the constant nor the fused result describes the probability that the answer is true.

**Verified:** The hand calculation and actual fusion behavior pass the free script and retrieval
algorithm tests. Code: `backend/app/retrieval/fusion.py`.

**George's remaining demonstration:** Calculate the example without notes and explain what
the two-per-document cap gains and sacrifices.

<a id="checkpoint-5"></a>

## 5. Inspect every citation in an answer and identify writer input

Use the historical real-model [development bridge](grounding-checks/development-bridge-01.json),
which asks for the former conference name. Its answer contains two claims and two citations:

| Claim | Citation | Source evidence and resolution |
| --- | --- | --- |
| Vermont men's soccer competes in America East Conference | E1 | “Vermont Catamounts men's soccer” says the team competes in that conference. Document `c3bbe7be-f3e6-5752-ba9b-73d3043faf06`. |
| America East was known as North Atlantic Conference, 1988–1996 | E3 | “America East Conference” explicitly supplies that name and date range. Document `2e15a777-e170-53b1-b34a-e4ddd0a95606`. |

**Verified:** Both full quoted excerpts occur in their identified retrieved texts. Their claim
relationships are supported in this source-relative worked example; this is assistant review,
not an independent human accuracy rating. The receipt's `saved_receipts.bridge_citations`
includes the complete actual quotations, not only the shortened explanations above.

The writer input contains the question, selected evidence IDs/titles/text, and the server's
quote catalogue. Instructions define evidence-only claims, statuses, comparison premises and
abstention. The selected-output schema restricts quote IDs and structure. Reference answers
and support labels are not writer inputs. The separate reviewer later receives proposed
claims and cited sources, not the evaluator's expected answer.

[Reconstructed writer context](learning-checkpoints/writer-context-reconstructed.json) is
explicitly reconstructed from the saved selected evidence and matching current code; it is
not a captured original network request or hidden model reasoning. See `service.py`, `models.py`
and `tools.py` under `backend/app/investigations/`.

**George's remaining demonstration:** Open each full quotation, identify the two-step relation
and distinguish the prompt, evidence, schema, returned output and public trace.

<a id="checkpoint-6"></a>

## 6. Demonstrate multi-step, conflict, abstention and failure

| Case | Worked outcome | Evidence |
| --- | --- | --- |
| Multi-step | Team → America East Conference → historical North Atlantic name; the second-round query follows a grounded entity | Saved real-model development bridge; current isolated tool-loop tests |
| Conflict | Two fictional reports give payment-router 3 and 5 retries for the same incident/time; retain both, choose no winner | `grounding-checks/development-conflict-01.json` |
| Absent answer | No approver is documented for the labelled fictional case; return `insufficient_evidence` with empty claims | `grounding-checks/development-unanswerable-01.json` |
| Provider failure | A simulated provider error returns HTTP 502, without an answer or private provider body | Fresh local API demonstration and existing API tests |

Two retrieval rounds and at most three searches are enforced by Python. Current v2 can use
up to four LLM requests: two planners, one draft and one support review. An early abstention
may skip later requests. A second search alone is not proof of multi-hop success; inspect
its bridge relation and whether both sources support the answer.

**George's remaining demonstration:** Explain these four outcomes and why HTTP 502 cannot be
interpreted as evidence that an answer is absent from the corpus.

<a id="checkpoint-7"></a>

## 7. Run the complete browser workflow and distinguish errors

**Worked sequence:** Upload → list/inspect source → close dialog → submit question → open
citation and exact source text → expand search trace → replace with the current revision tag
→ inspect an old citation as a snapshot → delete and confirm source absence.

The freshly run browser suite exercises actual UI events and real local API routes with
in-memory providers; its result is recorded in [browser evidence](learning-checkpoints/browser.json).
It also checks stale writes, duplicate notice, safe text rendering, error states, keyboard
accessibility and several widths. It does not test the factual ability of a real LLM.

`insufficient_evidence` and `conflicting_evidence` are successful evidence-status responses.
HTTP 429/502/503 are operational errors; they should offer an appropriate recovery action
without being relabelled as an evidence limitation or silently submitting another paid request.

**George's remaining demonstration:** Perform the workflow yourself and show one evidence
limitation and one error. Existing browser tests provide a demonstration, not proof you operated it.

<a id="checkpoint-8"></a>

## 8. Explain metrics and review disputed citations

**Worked metrics:** With two required sources and one in the first five, Recall@5 = 1/2.
If that one source ranks first, reciprocal rank = 1. A bridge is still incomplete. MRR
averages reciprocal ranks across the defined cases. Token F1 measures reference-token overlap,
not logical correctness. Mechanical citation validity tests IDs/excerpts; alignment to a gold
source remains weaker than semantic support for the exact claim.

**Worked source-relative reviews:**

- Annie Morton 1970 versus Terry Richardson 1965: Terry is older. The opposite claim reverses
  the relation even while citing correct birth years and mentioning the reference name.
- Germany's 82-million excerpt cannot establish the United States' population. Literal quote
  existence is true; entity/value binding is wrong.
- A For Against origin quotation cannot establish Local H's origin. Both being relevant gold
  documents does not make the particular claim/citation pairing sound.
- Publisher/apartment use versus a property company's headquarters exposes the ambiguity in
  “used for real estate”; a single yes/no reference can oversimplify the task.

These findings and full raw case pointers are in the existing
[AI-assisted qualitative review](evaluation/qualitative-review.md). Frozen labels/scores stay
unchanged. The offline archive checker freshly reproduces all 96 historical attempts and scores.
The full A/B study measures v1; v2 has development regressions. Required sources have identical
A/B chunk boundaries, so no causal superiority of one chunker is established.

**George's remaining demonstration:** Explain the denominators and personally read the cited
passages in disputed cases. Record your own judgments rather than copying the assistant label.

<a id="checkpoint-9"></a>

## 9. Reproduce restart checks

**Worked interpretation:** A browser reload is not a process restart. The historical
[real Render receipt](deployment/cloud-persistence.json) has different before/after boot IDs
and verifies replacement text, revision, exact tag and deletion, plus cited answers and cleanup.
The free learning script rechecks this receipt and separately recreates a local application
against a persistent external fake store. It also shows a fresh local ledger can be empty.
That isolated exercise is not a new Render restart or production durability experiment.

To perform a **new paid/cloud** rehearsal yourself, use a new state path consistently:

```powershell
uv run python scripts/verify_cloud_persistence.py prepare --url https://upgaming-ai-engineering-task.onrender.com --state artifacts/my-restart-rehearsal/state.json
```

Review the saved preparation result, then use the Render dashboard's restart/redeploy action.
After it is ready and its boot ID has changed:

```powershell
uv run python scripts/verify_cloud_persistence.py verify --url https://upgaming-ai-engineering-task.onrender.com --state artifacts/my-restart-rehearsal/state.json
```

The verifier refuses an unchanged boot ID, verifies current text/revision/tag and deletion,
checks returned evidence and cleans up only owned sources. It reserves budget, records
attempts and does not automatically retry uncertain paid calls. For interruption recovery,
inspect the saved state and use the documented `cleanup` phase with the same path.

**George's remaining demonstration:** Perform and explain the actual restart, if you wish to
check off “reproduce restart checks.” The commands/proof analysis are prepared; no new real
cloud restart or paid investigation was performed in this learning pass.

<a id="checkpoint-10"></a>

## 10. Explain the pipeline, diagnose a failure, change a setting without AI

**Worked pipeline:** browser question → request validation/limits → planner/tool call → query
embedding → dense/BM25 candidates → active-revision filtering → RRF/diversity selection →
grounded follow-up search → quoted draft → citation validation → support review/numeric checks
→ final revision check → structured result and trace.

**Worked diagnosis:** A high-ranking first bridge source with a missing second source is a
retrieval/selection problem before it is a generation problem. Inspect the discovered entity,
follow-up query, candidate lists, active filtering, document cap and final context. Do not
assume a prompt rewrite can supply an absent source fact.

**Executed practice change:** The script changes the per-document cap from two to one in an
isolated in-memory copy of `fusion.py`, then checks results against explicit expectations:

| Input ranking | Default cap 2 | Practice cap 1 |
| --- | --- | --- |
| a/D1, b/D1, c/D2 | a, b, c | a, c |

[Practice patch](learning-checkpoints/practice-change.patch) shows the exact one-line change.
Production source remains unchanged. This AI-assisted experiment passes independent expected-ID
assertions; the existing retrieval algorithm tests protect fusion behavior as well.

**George's remaining demonstration:** With AI closed, implement the change and its test in
your own practice copy, explain the diversity/detail trade-off and diagnose a deliberately
incorrect expectation. The assisted patch cannot satisfy the “without AI” condition for you.

<a id="checkpoint-11"></a>

## 11. Inspect accepted/rejected drafts and explain arithmetic versus meaning

**Accepted:** The synthetic quotes give Arden's birth as 1986 and Bryn's as 1972. “Bryn is
older than Arden” is supported; the supplied year relation can be recomputed and passes.
See [correct age](grounding-checks/correct-age.json).

**Rejected:** “Arden is older than Bryn” has the same literal source quotes. The real reviewer
marked it unsupported, so the system withheld it. However, that reviewer supplied `1986 > 1972`,
which is mathematically true but does not express the claim's required older-than direction.
See [reversed age](grounding-checks/reversed-age.json).

This is the distinction: Python proves a submitted numerical relation from quote-bound
operands. It does not independently establish the semantic mapping from the claim to that
relation. The rejection succeeded through the unsupported verdict, not through a false
numeric calculation. The unit test separately supplies `1986 < 1972` while marking support;
there Python can directly reject the false arithmetic relation.

**George's remaining demonstration:** Explain both rejection paths and why a same-model
reviewer's agreement or a true calculation is not a general factual guarantee.

## Completion record

All eleven **assisted resolutions** are prepared and linked in the checklist. Fresh tests and
isolated demonstrations are actual executed checks. Historical model/restart evidence is
labelled historical. All personal review, manual rating and unaided-performance criteria remain
available for George to complete and record honestly; no personal competency was fabricated.
