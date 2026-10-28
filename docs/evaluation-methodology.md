# Slice 8: predeclared comparative evaluation

Recorded before running the slice-8 development comparison. The final fixture files remain
frozen. Reference review by George is still pending; generated scores are provisional against
those labels. AI-assisted source/claim review is recorded separately and is not called human review.

## Controlled comparison

Run the eight development questions under A and B, then select the deployed default before
running the forty final questions under both. A uses 256-token windows/40-token overlap; B
uses sentence groups up to 256 tokens/one-sentence overlap with oversized sentence splitting.
Hold model snapshots, dimensions, corpus, prompts, top-30 semantic/keyword candidates, custom
RRF k=60, two-per-document cap and eight-chunk model context constant. Run serially, alternating
A/B order by case to reduce systematic order bias. One attempt per case/configuration; errors
stay in the denominator. No final-set tuning or selective retries.

Selection rule, applied only to development results, in order:

1. Higher count of supported-task checks passing (defined below).
2. Higher fraction of multi-source questions with all labelled documents in final context.
3. Higher mean initial-search Document Recall@10 across labelled cases.
4. A on an exact tie, preserving the provisional simpler fixed-window default.

Latency and cost are reported, not used to break tiny stochastic quality ties. The selected
default does not change after inspecting final results. A single stochastic run per condition
cannot establish that chunking caused a small difference. Many short source passages may
produce identical chunks under both strategies; measure this overlap before interpreting scores.

## Metric definitions and denominators

- **Document Recall@k:** distinct required gold document IDs found in the first k distinct
  ranked documents, divided by the number required. Average per case; unanswerable questions
  have no required documents and are excluded rather than counted as perfect.
- **MRR@10:** reciprocal rank of the first required source, or zero if none appears in ten.
  This rewards finding *one* source early; it cannot prove a complete multi-document chain.
- **Initial retrieval:** the first actual model-requested query. Diagnostic ranking is formed
  by the same chunk RRF over active candidates, then keeping each document's first appearance.
  It reaches ten documents independently of the eight-chunk context cap.
- **All-search diagnostic retrieval:** document-level RRF k=60 over the top-ten document lists
  of executed queries, with stable document-ID ties. Reused queries count once. This is a
  diagnostic aggregation, not the exact context selection algorithm.
- **All required sources:** report separately for the union of actual retrieved evidence,
  the final eight-chunk context, and cited sources. Bridge/comparison/conflict cases require
  multiple gold sources; a high first-hit MRR can coexist with a failed chain.
- **Normalized exact match / token F1:** HotpotQA lowercasing, ASCII punctuation/article removal,
  whitespace normalization, multiset token F1, and yes/no special handling. Compare against the
  single frozen short reference. Score both the complete concatenated claim text and its last
  atomic claim (the prompt asks for links first, requested fact last). These are unextracted
  generated prose, so exact match penalizes explanatory wording. Never select a gold-dependent
  substring or best matching claim. Report only the 28 answerable final cases (six development).
  API failures and wrong statuses receive zero. No EM/F1 is invented for conflicts/absence.
- **Expected-fact coverage:** whole normalized token sequence checks for every frozen
  `expected_facts` item; for answerable cases without those, use the frozen short answer.
  Check returned claim text only. This accepts explanatory prose but cannot detect negation,
  entity binding or an otherwise incorrect claim; inspect disputed cases separately.
- **Citation validity:** nonempty quote, known evidence ID, literal substring of that evidence,
  and evidence offsets matching canonical prepared source text. Report numerator/denominator;
  a zero-citation run is undefined, not 100% valid. A missing answer is still a failed task.
- **Labelled citation precision:** fraction of citations that also reference a gold document
  and contain a labelled supporting quote or are contained within one. This is a strict label
  alignment proxy. Other valid passages or duplicates with different source IDs can be false
  negatives. Correct IDs/literal quotes/label alignment do not prove semantic entailment.
- **Status results:** expected versus predicted status confusion table, abstention precision/
  recall, conflict precision/recall and conflict facts/both-source coverage. API errors are a
  separate predicted class, never treated as an abstention or dropped.
- **Supported-task check:** correct status; for answered/conflict cases, all expected facts,
  all required documents cited, at least one labelled-aligned citation, and all citations
  mechanically valid. This is a reproducible conservative proxy, not a human correctness grade.
- **Operations:** success/error counts, all-attempt wall latency median/p95, returned token
  usage, ledger token/cost deltas including failures, cache hits, physical index points,
  canonical document count, active-corpus expected chunk counts and chunk-strategy overlap.

## Integrity, cost and reproducibility

Use a local resumable command, not a public HTTP batch endpoint. Reuse the production bounded
investigation/search/provider services serially; the public demo rate limiter remains intact.
The local command bypasses only HTTP admission limits. It passes the question and configuration
to investigation; no reference answer, support label or evaluation explanation enters model
context or the corpus. Record fixture/corpus/code/prompt/schema hashes, dependency locks,
model settings, prices and per-attempt ledger deltas. Capture searches/evidence/outputs, not
hidden reasoning, credentials or provider headers.

Check cloud manifests against all prepared source IDs/hashes and index profile before calls.
Do not repair/reindex during evaluation. Stop on identity drift, storage/provider failure or
insufficient remaining budget. A completed provider failure remains recorded; do not silently
rerun it on resume. An interrupted in-flight attempt is marked uncertain instead of charged
twice. Resume only absent attempts with the same identity and unchanged corpus snapshot.

Keep the existing $4.50 conservative local ceiling within the $5 target. Show a preflight cost
projection using earlier development usage and a per-case conservative upper reservation.
Check that reservation allowance before each attempt. Actual usage estimates use configured
standard rates, without claiming cached-input discounts or account-wide spending enforcement.
The final report should retain representative failures and offer improvements without changing
the measured final system.

Primary sources: [HotpotQA official evaluator](https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py),
[GPT-5.4 mini model/pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
and [Qdrant count API](https://api.qdrant.tech/api-reference/points/count-points).
