# Comparative evaluation — 28 October 2026

**A remains the default selected on development data before final testing.** All 96 planned
attempts are archived: eight development questions and forty final questions, each under A/B.
The results show useful retrieval alongside substantive semantic failures. They do **not**
establish that fixed-window chunking is inherently better than sentence-aware chunking.

Read the [predeclared methodology](evaluation-methodology.md),
[hands-on reproduction guide](comparative-evaluation.md),
[frozen selection](evaluation/selection.json), and
[qualitative claim/citation review](evaluation/qualitative-review.md).
George's independent source/claim review and understanding checkpoint remain pending.

## Study identity and controls

The corpus contains **50,024 distinct canonical source passages**: 50,000 HotpotQA and 24
clearly fictional sources, before chunking. Dataset revision is
`1908d6afbbead072334abe2965f91bd2709910ab`; corpus SHA-256 is
`7fb92aae4a89727ca1d274d23ee25ba1dfafa052808fce75086f17c7c088c5eb`.
All cloud source IDs/content hashes/index profiles matched the prepared corpus before/after
each phase. Expected active chunks: **52,246 A / 52,307 B**. Physical point counts are
52,250 / 52,311, including four retained inactive test chunks per configuration.
The [read-only inactive-point check](inactive-evaluation-points.json) retrieved those four
deleted indexed revisions and confirmed their points in both collections.

A uses 256-token windows/40-token overlap. B uses sentence groups up to 256 tokens with one
sentence overlap and oversized-sentence splitting. Both use `text-embedding-3-small`, 384
dimensions, `gpt-5.4-mini-2026-03-17`, prompt `bounded_tools_quote_ids_v1`, top-30 dense and
BM25 candidates, custom RRF k=60, at most two chunks per document and eight chunks in final
context. The bounded workflow retains two retrieval rounds/three searches. Code/package/input
hashes and settings are in the [manifest](evaluation/manifest.json).
Reasoning effort is `none`, temperature/seed are unset, planning output is capped at 600 tokens
per call and final output at 1,200. Snapshot pinning does not make the workflow deterministic.

Run serially with alternating A/B order by question. No final question was retried; errors
stay in denominators. The model saw questions and retrieved source text, never reference answers
or support labels. No prompts, schema, retrieval limits, labels or corpus were tuned after
observing final outputs. The selected A default was not changed in response to final results.

Selection was frozen at **10:57:38 Asia/Tbilisi**, before the first final attempt at **10:59:55**
on 28 October 2026; UTC timestamps are preserved in the archive. Development A passed 6/8
supported-task checks versus B's 5/8, selecting A on the first predeclared criterion. The
selection and development receipts were committed in `d1ce1db` before final execution.

## Final retrieval results

These are macro averages across the **34 cases with labelled sources**; six unanswerable
cases have no retrieval denominator. Failed attempts receive zero in these averages, although
their partial retrieved evidence remains in raw receipts. MRR is explicitly truncated at ten.
All-search ranking is a diagnostic document-level RRF across executed search lists; it is
separate from production context selection.

| Metric | A | B |
| --- | ---: | ---: |
| Initial Document Recall@5 | 85.3% | 86.8% |
| Initial Document Recall@10 | 86.8% | 89.7% |
| Initial MRR@10 | 0.892 | 0.912 |
| All-search diagnostic Recall@5 | 83.8% | 88.2% |
| All-search diagnostic Recall@10 | 92.6% | 94.1% |
| All-search diagnostic MRR@10 | 0.882 | 0.912 |
| All gold sources in retrieved evidence, multi-source cases | 23/26 | 24/26 |
| All gold sources in final context, multi-source cases | 22/26 | 23/26 |
| All gold sources cited, multi-source cases | 21/26 | 20/26 |

MRR can be high while a bridge is incomplete: finding the first source at rank one says
nothing about the missing second source. More searches can improve Recall@10 without improving
Recall@5, because diagnostic fusion can move a gold document lower. The context/citation rows
also expose losses after retrieval. These are distinct failure locations.

## Answer and citation results

The supported-task check combines status, literal expected-fact presence, required cited
documents and mechanical/labelled citation checks. **It is not a semantic accuracy percentage.**
It has both false negatives from wording and false positives from wrong relationships.

| Metric / denominator | A | B |
| --- | ---: | ---: |
| Successful responses / 40 attempts | 38/40 | 39/40 |
| Status matches frozen label / 40 | 38/40 | 38/40 |
| Supported-task checks / 40 | 32/40 | 31/40 |
| All literal expected facts / 34 labelled cases | 27/34 | 26/34 |
| Full generated prose normalized EM / 28 short-reference cases | 0/28 | 0/28 |
| Full generated prose token F1, mean | 0.221 | 0.195 |
| Last generated claim normalized EM / 28 | 0/28 | 0/28 |
| Last generated claim token F1, mean | 0.224 | 0.208 |
| Mechanically valid citations / returned citations | 59/59 | 58/58 |
| Gold document/quote aligned citations / returned citations | 57/59 (96.61%) | 56/58 (96.55%) |

There is no dedicated short-answer field in this system. EM/F1 compare unextracted generated
prose to the short reference; the last-claim variant follows the prompt convention without
using gold to choose a substring. Explanations such as “The documented recovery time … was
11 minutes” correctly answer the question but cannot exactly match “11 minutes.” Yes/no F1
uses HotpotQA's special rule, which also gives zero for an explanatory negative without a
literal normalized “no.” These lexical results must not be interpreted as zero correct answers.
Some outputs put the requested fact first, making the last-claim convention imperfect as well.

Conversely, B says Annie Morton is older than Terry Richardson despite citing 1970 and 1965
birth dates. It contains the expected name and the labelled passages, so the supported-task
proxy passes the wrong comparison. This is why a high proxy score is not a semantic guarantee.

Mechanical citation validity is conditional on **returned** citations. Validation can reject an
output, and those failed attempts remain failed tasks rather than receiving a free perfect
citation score. Gold alignment is a stricter automatic citation-accuracy proxy, not entailment.
B's Local H claim cites a gold For Against passage: alignment succeeds while entity support
fails. B's extra Hork-Bajir narration quote is valid source context outside the specific labelled
sentences and receives a strict alignment penalty. Both types need qualitative review.

Supported-task checks by frozen category:

| Category | Questions | A | B |
| --- | ---: | ---: | ---: |
| Simple | 8 | 8 | 8 |
| Bridge | 12 | 10 | 9 |
| Comparison | 8 | 4 | 2 |
| Conflict | 6 | 4 | 6 |
| Unanswerable | 6 | 6 | 6 |

## Abstention, conflict and errors

| Measure | A | B |
| --- | ---: | ---: |
| Abstention precision | 6/6 | 6/7 |
| Abstention recall | 6/6 | 6/6 |
| Conflict precision | 4/4 | 6/6 |
| Conflict recall | 4/6 | 6/6 |
| HTTP errors | 2 | 1 |

A's final errors are `final-conflict-01` and `final-conflict-06`; B's is
`final-comparison-06`. All are HTTP 502 after retrieval/model work. The runner records status,
partial searches and usage, but not the exact provider/schema/evidence failure subtype; do
not invent a precise root cause. B also abstains on the instrument/person-ratio comparison.
That differs from the frozen label but is defensible because the passages do not establish
exact counts. The full status confusion tables are in the [raw summary](evaluation/final/summary.json).
The development B conflict failure is retained separately, for four errors across all 96 attempts.

Every successful final conflict output preserves both same-case/same-time retry values and
their separate reports. None chooses a winner. The absent-approver cases return no claims;
the original fictional source text records no approver. These cases demonstrate bounded
behavior on this fixture collection, not general abstention/conflict reliability.

## Latency, tokens and cost

| Final-set operation / 40 attempts | A | B |
| --- | ---: | ---: |
| Attempt latency median | 5.288 s | 5.151 s |
| Attempt latency p95 | 6.451 s | 6.058 s |
| Provider calls recorded | 188 | 185 |
| Known input tokens | 228,413 | 227,992 |
| Known output tokens | 6,745 | 6,671 |
| Query embedding cache hits | 12 | 16 |
| Known estimated API cost | $0.20097386 | $0.20032803 |
| Conservative reservation delta | $0.75862061 | $0.75852603 |

Latency includes successful/failed service attempts, excluding corpus preflight and pauses.
The local embedding cache was retained; this is not a cold-cache benchmark. Model input is
estimated at standard configured rates without cached-input discounts: $0.75/M input and
$4.50/M output, plus $0.02/M embedding tokens. These are application estimates, not invoices.

Development cost was $0.08628946; final cost was $0.40130189; **all evaluation attempts added
$0.48759135**. The project ledger moved from $0.20992536 known usage/$0.48744711 reservations
to **$0.69751671 known usage/$2.31480321 reservations**, below the unchanged $4.50 local
ceiling and $5 target. Failed calls retain usage/reservations. The offline checker confirms
ledger continuity between attempts; no other paid app work was run during these batches.

## Failures, interpretation and plausible improvements

The [claim review](evaluation/qualitative-review.md) records concrete examples and supporting
excerpts. The most serious failures are semantic: A assigns Germany's 82-million figure to
the US; B gives an unsupported 331-million US figure while citing world population; B reverses
an age comparison; A equates British with English origin. These are not excused by literal
quote validity or the benchmark's wording problems. Retrieval alone cannot enforce correct
entity/value binding, comparison direction or geographic scope.

Nine reference caveats were recorded [before final calls](evaluation-reference-caveats.md).
They include a country/county typo, ambiguous building “real estate” usage and underspecified
instrument ratios. Labels were preserved; scores are provisional against those labels, and
George's independent review remains pending.

The strongest experimental limitation: **all 12 development and all 60 final distinct required
source passages have identical A/B chunk spans**. Across the entire corpus, 47,952/50,024 sources
have identical spans. Only distractor boundaries/index statistics and model behavior can
differentiate many cases here. Among 37 case pairs with two successful responses, only 21
have identical first-query wording. Together with a small order-biased public benchmark and
one stochastic trial per condition, this prevents a causal “A chunking is better” conclusion.
B has slightly stronger measured retrieval, while A retains the development-selected default.

A future study should add boundary-sensitive development documents, clarify/version labels,
use fresh held-out questions, repeat paired trials and record uncertainty. Product improvements
could require evidence for each bridge link, check entity/value bindings and comparison direction,
clarify ambiguous question scope, and add a dedicated cited short-answer field. Record sanitized
failure subtypes to diagnose 502s. These changes were not applied to tune this final set.

## Verify it yourself without more model calls

Raw [development](evaluation/development/summary.json) and [final](evaluation/final/summary.json)
summaries link to per-attempt JSON and scored rows in their folders. Archive fingerprints and
the [offline verification report](evaluation/verification.json) check inputs, metrics, selection
timing, code bytes and budgets. The original corpus stays under ignored `data/`; reproduction
instructions and hashes recreate it. Passage provenance/licenses remain in source metadata
and [fixture conventions](../fixtures/README.md).

```powershell
uv run python scripts/verify_evaluation_archive.py
uv run --group data pytest -W error
```

The first command recomputes both summaries/scores from saved results and local corpus text.
It does not read credentials, contact providers or retry questions. Use the
[walkthrough](comparative-evaluation.md) to calculate a ranking, trace a bridge and review
the reversed-age example. All 141 backend tests and Ruff lint/format checks pass. Public
deployment/restart checks and final rehearsal remain the next slices.

An [offline mutation check](evaluation-mutation-check.json) replaced one citation in a
disposable archive copy. Recomputed scores rejected the modified copy; the original archive
was untouched. Archive files have fixed LF checkout endings so their fingerprints remain
portable between Windows and Unix. Raw historical code-byte hashes can still reflect the
original checkout endings; the checker reports that separately from metric reproduction.
