# Walkthrough: unsupported claims and comparisons

28 October 2026. Current workflow: `bounded_tools_verified_v2`; review policy:
`cited_claim_review_v1`. Raw development receipts: [grounding checks](grounding-checks/).

## What changed and why

The previous pipeline established that a quote existed in retrieved text. It could still attach
that quote to the wrong entity, infer a missing attribute, or reverse a comparison. Increasing
retrieval recall cannot by itself prevent those generation errors.

The current request proceeds through these boundaries:

1. Two bounded planners call the real search tool, with at most three searches in total.
2. The writer selects quote IDs and drafts cited claims. Python resolves IDs and validates
   literal excerpts and answer structure, as before.
3. A separate model request receives the question, proposed claims and **only cited sources**.
   It checks each claim's own excerpts for support, entity/value binding, comparison premises,
   scope and completeness. The expected test answers are never sent to this reviewer.
4. Python requires exactly one judgment per claim. For numeric comparisons supplied by the
   reviewer it validates operands against the actual cited quotes, normalizes explicit scales,
   and evaluates the relation with `Decimal` arithmetic.
5. Any unsupported/uncertain claim, missing question premise, false numeric relation or
   unverified conflict withholds the **entire** draft. The result is `insufficient_evidence`
   with empty claim arrays. Keeping only a valid fragment could misleadingly answer a question
   requiring two premises. A malformed review/provider failure is HTTP 502, not an abstention.
6. The final revision check still runs after review: a concurrent replacement/deletion returns
   HTTP 409. Rejected draft text is not sent to the browser. Review outcome/counts are visible
   in Search trace → Run details; this is not hidden reasoning.

Code: `backend/app/investigations/verification.py`, `service.py`, and `backend/app/providers.py`.

## Trace a comparison yourself

Quotes say Arden was born in 1986 and Bryn in 1972. The proposed claim says Arden is older.
The intended numeric relation is `1986 < 1972`, which is false. The unit test deliberately
marks that claim supported but supplies this relation; Python withholds it anyway. The correct
claim, Bryn is older, uses `1972 < 1986` and can pass. For quantities, `1.2 billion > 900 million`
becomes `1200000000 > 900000000`; comparing the bare values 1.2 and 900 would be wrong.

Read the live `reversed-age.json` receipt carefully: the model marked the claim unsupported,
but supplied `1986 > 1972`. Withholding succeeded because of its unsupported verdict, **not**
because arithmetic detected that reversed operator. Python does not independently understand
which operator the English claim requires. This illustrates the boundary between semantic
interpretation and deterministic arithmetic rather than hiding a reviewer weakness.

## Choices and alternatives

| Choice | Why | Alternative and drawback |
| --- | --- | --- |
| Separate cited-claim review | Checks the claim/evidence relationship after writing, with no uncited source to rescue a bad citation | Prompt-only reminders are cheaper but gave no post-generation rejection boundary |
| Same configured small model | Fits existing deployment and cost target | A different model can reduce correlated errors but adds configuration/cost; a local entailment model needs memory and its own calibration |
| Decimal relations over cited operands | Makes supplied arithmetic reproducible, including explicit million/billion scales | Free-form model arithmetic is harder to audit; fully parsing every natural-language comparison is a much larger problem |
| Withhold whole draft | Avoids passing an incomplete comparison or bridge as a complete answer | A repair/rewrite loop may recover answers but adds calls and new claims needing review |
| Typed reason codes, no explanations from reviewer | Small bounded output and useful diagnostics | Unbounded review prose adds latency and can disclose generated reasoning without proving support |

There are now at most **four** model calls and three embedding requests (seven provider calls),
with the existing two retrieval rounds, three searches and 90-second deadline unchanged. Review
allows 1,200 output tokens. Usage includes `verification` separately and in the total. With the
configured rate estimates, the conservative full-attempt reservation bound is **$0.062592**;
cloud persistence probes reserve $0.08. These are application guards, not a provider hard cap.

## What was actually verified

- **185 backend tests** passed with warnings treated as errors. Coverage includes quote validity
  versus unsupported support, wrong entity/value, missing premise, scope, reversed arithmetic,
  scale normalization, malformed/incomplete reviews, provider errors and deletion during review.
  The central unsupported-claim regression was first observed failing against the old pipeline.
- Eight synthetic development reviews with the real configured model passed their expected
  pass/withhold checks: reversed/correct age, wrong population entity, wrong band, missing
  nationality premise, British-to-English inference, scaled population ordering and supported
  origin. Estimated usage: **$0.0071775**.
- Four real retrieval → drafting → review development cases passed: two bridges cite both
  required documents, conflicting reports retain 3/5 attempts for the same service/time, and the
  unavailable answer abstains without a needless review. Estimated usage: **$0.02470914**.
  Observed latency: **6.2–14.4 seconds**. Both bridges used a grounded second-round entity search.
- The frozen evaluation archive still reproduces all 96 earlier attempts, scores and summaries
  offline. Its source fingerprints differ because this changes the application. Its model outputs,
  labels and scores were not rewritten or rerun as held-out evidence for the new workflow.
- After the tested change was committed/pushed, Render served application commit `5911d65`.
  Health was ready and the served frontend contained the review details. One public development
  question returned the fictional incident's **11 minutes**, with `verification.outcome=passed`
  and a citation matching the active canonical source. Estimated usage: **$0.00502692**, mirrored
  conservatively into the local ledger before/after the request. Its separate public receipt is
  `grounding-checks/public-development-simple-01.json`; it is not an additional held-out case.

The raw receipts retain the inputs, verdicts, usage and unsuccessful drafts for **developer
inspection only**. These synthetic facts are explicitly fictional and were not added to Qdrant.
No corpus mutation or reindexing was needed. Full automated and deployment check receipts are
recorded in `docs/grounding-verification.json`.

## Verify it yourself

Free checks from the repository root:

```powershell
uv run pytest backend/tests/test_claim_verification.py backend/tests/test_investigations_api.py -q -W error
uv run python scripts/verify_evaluation_archive.py
cd frontend
npm run test:browser
```

For a deliberate **paid** development rerun, return to the root with credentials configured:

```powershell
uv run python scripts/verify_claim_grounding.py review --output artifacts/my-grounding-check
uv run python scripts/verify_claim_grounding.py pipeline --output artifacts/my-grounding-check
```

The script records a pending receipt before each attempt and refuses to overwrite an existing
one, including an interrupted/failed attempt. It never reads final fixtures or retries a paid
failure automatically. Review the saved claim, citations and judgment yourself; a passing
expected-status check is not a substitute for semantic review.

Then use the website's development example, open its citations, and expand Search trace → Run
details. Explain why “quote exists”, “review passed” and “claim is true” are different statements.
Run the reversed-age unit test, inspect its `lt`, and change the relation locally to understand
what the arithmetic gate can and cannot establish. Restore practice edits before submission.

## Remaining limits

The reviewer can misinterpret a claim, choose the wrong operand/operator, omit a comparison or
approve an unsupported fact. Using the same model for writer and reviewer creates correlated
errors; it can also reject correct answers. Decimal checks only verify the relations actually
submitted, not every possible comparison. Missing evidence and withheld generation remain
distinct in metadata but share the three-status API's `insufficient_evidence` status.

Twelve selected development checks do not establish accuracy on a fresh distribution. The old
frozen study remains a historical baseline; a new independently reviewed held-out set is needed
to quantify benefit and false abstentions. George's own source review and unaided explanation
remain pending. No universal correctness claim is made.
