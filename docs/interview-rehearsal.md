# Independent interview rehearsal

The implementation and AI-run checks are documented. This rehearsal is still yours to do.
The assignment permits disclosed AI assistance while building and forbids it in the practical
interview. Close AI/chat tools for the exercises, use the code/docs as indicated, and record
what you actually explained or changed. Do not turn an AI-written explanation into a claim
of independent implementation.

## Explain the system without notes — 10 minutes

Explain to another developer:

1. How a React action reaches a FastAPI route. What changes between Vite preview's proxy and
   the deployed single-origin service? Why does preview still need Python running?
2. How a PDF page, DOCX paragraph or TXT paragraph becomes canonical text, a normalized hash,
   a revision and overlapping chunks. Why isn't a chunk a distinct source passage?
3. How embeddings find similar meaning and BM25 finds matching terms. Why combine rankings
   rather than adding their raw scores? What does the two-per-document cap sacrifice?
4. How an actual model tool call is validated/executed, and how an entity discovered in one
   result grounds a follow-up search. Where do the two-round/three-search limits apply?
5. What citation validation proves. Give a case where a valid quote does not support the
   generated relationship. Use the reversed-age example in the evaluation report.
6. What survives a cloud restart. Why is the local spending counter not an account-wide cap?
   Why did a weak representation ETag break replacement, and what did the dedicated header fix?
7. What the study measured, why A was selected before final testing, and why the experiment
   cannot establish that A's chunking is inherently superior.

If you cannot explain a step, trace that step before reading more generated code.

## Trace one recorded request — 15 minutes, notes allowed

Use the successful cloud persistence receipt under `docs/deployment/`. Read
`question_before.result`: question → executed queries → retrieved source/revision → claim
→ citation ID → verbatim quote. Find its implementation using this map:

| Responsibility | Starting point |
| --- | --- |
| React question state/request | `frontend/src/components/InvestigationPanel.tsx`, `frontend/src/api.ts` |
| Route, request limits and errors | `backend/app/investigations/routes.py` |
| Bounded planning/generation | `backend/app/investigations/service.py` |
| Tool arguments/entity grounding | `backend/app/investigations/tools.py` |
| Dense/BM25 retrieval and active-revision gate | `backend/app/retrieval/search.py` |
| Rank fusion/diversity | `backend/app/retrieval/fusion.py` |
| Quote IDs, quote resolution and validation | `backend/app/investigations/models.py` |
| Revision activation, ETag and deletion | `backend/app/documents/service.py`, `routes.py` |
| Provider limits/cache/usage | `backend/app/providers.py` |
| Evaluation denominators/scoring | `backend/app/evaluation/metrics.py`, `scoring.py` |

Locate the data actually sent to the model. Separate source text, tool results, JSON schema,
prompts and hidden model internals. The public trace contains searches/evidence, not hidden
reasoning. Identify the unsupported assumptions the model was explicitly told to avoid.

## Calculate rank fusion — 5 minutes, no notes

Chunk A is semantic rank 1, keyword rank 3. Chunk B is semantic rank 2, keyword rank 1.
Compute their scores with k=60 and decide which ranks first. Then explain what happens if a
chunk is absent from one list, repeated in one list, or tied in total score.

<details>
<summary>Self-check after calculating</summary>

A = 1/61 + 1/63 ≈ 0.03226646. B = 1/62 + 1/61 ≈ 0.03252247, so B ranks first.
Absence contributes zero; duplicates in one ranking are removed before assigning the next
unique rank; ties use the chunk ID for stable ordering. Neither score is a truth probability.

</details>

## Diagnose a failure — 10 minutes, no AI

For each scenario, name the first observation/test you would make, and distinguish data,
retrieval, generation and infrastructure failures:

- `/api/live` is 200 but `/api/health` is 503.
- A bridge's first source ranks first but the second required source is missing.
- Both required documents are in retrieved evidence but only one reaches the answer context.
- A quote appears verbatim, but the model reverses the relationship it describes.
- A replacement gets 412 after you loaded the source; should the client overwrite anyway?
- A request times out after provider submission. Why shouldn't it be retried automatically?
- A deleted chunk remains a physical Qdrant point. How is it kept out of answers?

For evaluation, calculate Recall@5 for a question requiring two documents when only one is
found. Contrast it with reciprocal rank when the first relevant source is rank one. Explain
why averaging only successful attempts would conceal provider failures.

## Make a small retrieval change — 20–30 minutes, no AI

Start with a clean working tree and inspect the existing retrieval-algorithm tests. As a local
practice exercise, reduce `fuse`'s per-document default from two chunks to one. Write/adjust a
test with several candidates from one document and another from a second document. Show that
the chosen evidence respects the new cap and preserves stable ranking for eligible hits.
Do not change the RRF formula or weaken an assertion just to get green.

Run the focused tests, inspect the diff, and explain the recall/diversity trade-off aloud.
Restore the original setting/tests manually after practice, or keep the change only if you
deliberately choose it and document why. The submitted default remains two; this guide has
not made the exercise change for you. Do not push an unreviewed practice edit to the live demo.

## Record actual understanding

For the follow-up grounding fix, read `docs/claim-grounding.md` and
`backend/app/investigations/verification.py`. Explain why a literal quote can support the wrong
entity, why withholding the whole draft avoids an incomplete comparison, and why a correct
numeric calculation does not prove that the reviewer chose the right operator for the English
claim. Trace the fourth model call and its separate usage row. Compare `reversed-age.json`
with the unit test that supplies a false `lt` relation; they reject through different checks.

Append your own dated journal entry with:

- Your explanation of one request and one failure, in your own words.
- Commands you ran and results you observed yourself.
- The practice change/test you wrote, including any failed attempt and how you fixed it.
- What remains confusing and which code you will inspect next.

Only then tick the corresponding George review items in `tasks/todo.md`. AI-generated tests,
documentation and a working demo do not complete this independent rehearsal.
