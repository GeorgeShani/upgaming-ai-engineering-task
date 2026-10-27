# Dataset and evaluation fixture conventions

## What is committed

- `dataset-selection.json`: exact HotpotQA dataset revision and deterministic selection rule.
- `source-documents.jsonl`: 48 native HotpotQA support passages and 24 fictional documents.
- `evaluation/final.jsonl`: 40 questions, reference answers/statuses, and labelled evidence.
- `evaluation/development.jsonl`: 8 separate questions for development decisions.
- `evaluation/manifest.json`: hashes of frozen source and label files, counts, and review status.

Full corpus output is ignored under `data/`. No question or answer fields are accepted by the
source-record schema. Only `corpus.jsonl` is intended as input to the future dataset indexer.
Never recursively index this repository: README files, review notes, and evaluation files contain
answers and are not corpus sources.

## Reproducible selection

Dataset: `hotpotqa/hotpot_qa`, configuration `distractor`, pinned revision
`1908d6afbbead072334abe2965f91bd2709910ab`.

First select valid validation questions in source order: 12 bridge and 8 comparison questions for
final evaluation, followed by 2 of each for development. Retain their supporting passages, with
original zero-based sentence IDs. Questions requiring fewer than two distinct source passages
are skipped for these categories, and skipped IDs are recorded in the fixture manifest.

Seed the corpus with the native support passages, then read training contexts in source order
until 50,000 unique normalized HotpotQA passages exist. Append 24 distinct fictional passages.
Sort the emitted JSONL by stable document ID. NFKC plus whitespace collapse is normalization v1;
SHA-256 hashes normalized text. Repeated content counts once regardless of title; altered text
under the same title remains distinct. Provenance records the first selected occurrence rather
than every repeated occurrence. Source paragraphs are independent records, not complete articles
or retrieval chunks. No padding, paraphrasing, or chunk multiplication inflates the minimum.
Streaming avoids loading the entire upstream dataset first. Preparation still retains the selected
50,000 records in memory before writing; it is bounded local work, not constant-memory processing
or a task intended for the free web server.

The corpus is intentionally constructed to contain the labelled evidence. This tests retrieval
and answering when evidence exists, not unbiased corpus coverage or random-population accuracy.
The first-source-order subset is reproducible but order-biased. The 40 final questions are a small
demonstration benchmark, not a representative estimate of production investigation quality.
Public benchmark facts may already be familiar to an LLM, so later answer scores must be assessed
alongside actual retrieved evidence and the previously unseen fictional cases.

## Evaluation categories and review

| Category | Final | Development | Reference source |
| --- | ---: | ---: | --- |
| Simple | 8 | 2 | Fictional recovery-time records |
| Bridge | 12 | 2 | Native HotpotQA question/answer/support labels |
| Comparison | 8 | 2 | Native HotpotQA question/answer/support labels |
| Unanswerable | 6 | 1 | Unrecorded approvers for unique fictional cases |
| Conflict | 6 | 1 | Two same-time reports with incompatible retry limits |

The fictional documents describe no real organization. Conflicts give both values and have no
precedence rule, so the reference does not choose a winner. Unanswerable questions have no gold
answer or fabricated supporting evidence. Native answers are benchmark labels, not an assertion
that all facts are current. Dataset revision and quoted text anchor evidence to a snapshot;
the linked live Wikipedia page may have changed.

Reference review is **pending George's independent verification**. Read the generated review
sheet in `docs/evaluation-fixtures.md`, trace quotes to source sentences, and question ambiguous
labels. If a label is wrong, make an explicit versioned correction before reporting evaluation;
do not silently edit labels in response to poor scores. Freeze configuration choices on development
examples before measuring the final set. Development/final case IDs, questions, and native QA IDs
must not overlap, though they may share general background source documents.

Regenerate the readable sheet from the frozen labels without downloading anything:

```powershell
uv run python -m backend.app.dataset_cli review
```

Questions, answers, and support labels are never copied to the corpus. Gold labels are used
offline to establish corpus membership and verify fixtures; future retrieval/answering sees only
canonical source text and provenance.

## Files, hashes, and failures

Each source record has `document_id`, `title`, `text`, `content_sha256`, `source`, and `segments`.
Segments carry original sentence IDs, canonical character offsets, and normalized sentence text.
Evidence labels reference document ID, original sentence ID, and exact canonical quote. Validators
check all three, counts, unique content, split separation, and source/fixture hashes.

JSONL uses UTF-8 and LF line endings. `.gitattributes` preserves these bytes across Windows and
Unix checkouts, otherwise checkout line-ending conversion could invalidate frozen hashes.
Preparation publishes a whole output directory only after all files are written successfully.
It refuses existing outputs. The preparation step is not resumable indexing; restart with the
same pinned inputs after a network failure. Dataset-library downloads may be cached separately.

The one-time fixture generator refuses existing frozen files. For reproducing fixtures separately,
copy only `dataset-selection.json` into a fresh directory first, then run:

```powershell
uv run --group data python -m backend.app.dataset_cli --fixtures artifacts/rebuilt-fixtures freeze-fixtures
```

Compare the generated JSONL hashes with the committed fixture manifest. This is a verification
operation, not a reason to repeatedly select new final questions while tuning.

## Attribution and data terms

HotpotQA dataset card: https://huggingface.co/datasets/hotpotqa/hotpot_qa (CC-BY-SA-4.0 as listed).
Native passage records retain their Wikipedia title/URL, dataset revision, originating QA record
ID, and split. HotpotQA: Yang et al., 2018, https://arxiv.org/abs/1809.09600.
The source repository's Apache-2.0 code license is separate from the dataset/content terms.
The clearly marked original fictional fixture text is provided under CC0-1.0.
