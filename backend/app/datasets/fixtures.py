import json
from collections import Counter
from pathlib import Path

from .files import read_jsonl, sha256_file, write_json, write_jsonl
from .hotpot import labelled_case
from .models import Document, EvaluationCase, Evidence, Source, make_document, normalize_text

FINAL_COUNTS = {"simple": 8, "bridge": 12, "comparison": 8, "unanswerable": 6, "conflict": 6}
DEV_COUNTS = {"simple": 2, "bridge": 2, "comparison": 2, "unanswerable": 1, "conflict": 1}


def synthetic_cases() -> tuple[list[EvaluationCase], list[Document]]:
    cases, documents = [], []

    def document(name: str, facts: list[str]) -> Document:
        doc = make_document(
            f"Fictional investigation: {name}",
            [
                "This document is a fictional test fixture; it describes no real organization.",
                *facts,
            ],
            Source(
                kind="synthetic",
                revision="fictional-incidents-v1",
                split="fixture",
                record_id=name,
                url=f"fixture://fictional-incidents-v1/{name}",
                license="CC0-1.0",
            ),
        )
        documents.append(doc)
        return doc

    def evidence(doc: Document) -> Evidence:
        sentence = doc.segments[1]
        return Evidence(document_id=doc.document_id, sentence_id=1, quote=sentence.text)

    for split, simple_count, conflict_count, absent_count in [
        ("final", 8, 6, 6),
        ("development", 2, 1, 1),
    ]:
        for index in range(1, simple_count + 1):
            case = f"NOVA-{split.upper()}-{index:02}"
            minutes = 10 + index
            doc = document(
                case,
                [
                    f"For fictional incident {case}, the documented recovery time was "
                    f"{minutes} minutes.",
                    f"Incident {case} affected the fictional payment-router service on 2026-03-12.",
                ],
            )
            cases.append(
                EvaluationCase(
                    case_id=f"{split}-simple-{index:02}",
                    category="simple",
                    split=split,
                    question=f"What recovery time was documented for fictional incident {case}?",
                    expected_status="answered",
                    gold_answer=f"{minutes} minutes",
                    expected_facts=[f"{minutes} minutes"],
                    evidence=[evidence(doc)],
                )
            )
        for index in range(1, absent_count + 1):
            case = f"NOVA-{split.upper()}-{index:02}"
            cases.append(
                EvaluationCase(
                    case_id=f"{split}-unanswerable-{index:02}",
                    category="unanswerable",
                    split=split,
                    question=f"Who approved the rollback for fictional incident {case}?",
                    expected_status="insufficient_evidence",
                    gold_answer=None,
                )
            )
        for index in range(1, conflict_count + 1):
            case = f"NOVA-CONFLICT-{split.upper()}-{index:02}"
            low, high = index + 2, index + 4
            docs = [
                document(
                    f"{case}-report-{number}",
                    [
                        f"For fictional case {case}, the retry limit of payment-router at "
                        f"12:00 UTC on 2026-03-12 was {value} attempts.",
                        "This report provides no resolution or precedence over other reports.",
                    ],
                )
                for number, value in enumerate((low, high), 1)
            ]
            cases.append(
                EvaluationCase(
                    case_id=f"{split}-conflict-{index:02}",
                    category="conflict",
                    split=split,
                    question=f"What was payment-router's retry limit for fictional case {case} "
                    "at 12:00 UTC on 2026-03-12?",
                    expected_status="conflicting_evidence",
                    gold_answer=None,
                    expected_facts=[f"{low} attempts", f"{high} attempts"],
                    evidence=[evidence(doc) for doc in docs],
                )
            )
    return cases, documents


def validate_cases(cases: list[EvaluationCase], documents: dict[str, Document]) -> None:
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique")
    if len({normalize_text(c.question).casefold() for c in cases}) != len(cases):
        raise ValueError("Development and final questions must not overlap")
    source_ids = [c.source_question_id for c in cases if c.source_question_id]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("A HotpotQA question was reused across evaluation cases")
    for split, expected in (("final", FINAL_COUNTS), ("development", DEV_COUNTS)):
        actual = Counter(c.category for c in cases if c.split == split)
        if actual != Counter(expected):
            raise ValueError(f"Wrong {split} category counts: {dict(actual)}")
    for case in cases:
        for item in case.evidence:
            doc = documents.get(item.document_id)
            if doc is None:
                raise ValueError(f"Missing support document for {case.case_id}")
            sentences = {s.sentence_id: s.text for s in doc.segments}
            if sentences.get(item.sentence_id) != item.quote:
                raise ValueError(f"Gold evidence location/quote mismatch for {case.case_id}")


def freeze_fixtures(rows, directory: Path, selection: dict) -> dict:
    paths = [
        directory / "source-documents.jsonl",
        directory / "evaluation" / "final.jsonl",
        directory / "evaluation" / "development.jsonl",
        directory / "evaluation" / "manifest.json",
    ]
    if any(path.exists() for path in paths):
        raise FileExistsError("Frozen fixtures already exist; choose a new directory/version")
    cases, documents = synthetic_cases()
    counters = Counter()
    skipped = []
    for row in rows:
        category = row["type"]
        if category not in ("bridge", "comparison"):
            continue
        final_limit, dev_limit = FINAL_COUNTS[category], DEV_COUNTS[category]
        if counters[category] >= final_limit + dev_limit:
            continue
        index = counters[category] + 1
        split = "final" if index <= final_limit else "development"
        number = index if split == "final" else index - final_limit
        try:
            case, support = labelled_case(
                row, selection["revision"], split, f"{split}-{category}-{number:02}"
            )
        except (ValueError, KeyError, StopIteration) as error:
            skipped.append({"source_id": row["id"], "reason": type(error).__name__})
            continue
        counters[category] += 1
        cases.append(case)
        documents.extend(support)
        if all(counters[k] == FINAL_COUNTS[k] + DEV_COUNTS[k] for k in ("bridge", "comparison")):
            break
    by_id = {doc.document_id: doc for doc in documents}
    validate_cases(cases, by_id)
    cases.sort(key=lambda case: case.case_id)
    write_jsonl(paths[0], sorted(by_id.values(), key=lambda doc: doc.document_id))
    write_jsonl(paths[1], (c for c in cases if c.split == "final"))
    write_jsonl(paths[2], (c for c in cases if c.split == "development"))
    manifest = {
        "schema_version": 1,
        "dataset_revision": selection["revision"],
        "selection": "First valid multi-document validation questions in source order, by category",
        "final_counts": FINAL_COUNTS,
        "development_counts": DEV_COUNTS,
        "reference_review": "pending George's independent review",
        "skipped_candidates": skipped,
        "files": {
            str(path.relative_to(directory)).replace("\\", "/"): sha256_file(path)
            for path in paths[:3]
        },
    }
    write_json(paths[3], manifest)
    return manifest


def load_fixtures(directory: Path) -> tuple[list[EvaluationCase], dict[str, Document], dict]:
    manifest = json.loads((directory / "evaluation" / "manifest.json").read_text(encoding="utf-8"))
    expected_files = {
        "source-documents.jsonl",
        "evaluation/final.jsonl",
        "evaluation/development.jsonl",
    }
    if set(manifest["files"]) != expected_files:
        raise ValueError("Fixture manifest has an unexpected file list")
    for name, digest in manifest["files"].items():
        if sha256_file(directory / name) != digest:
            raise ValueError(f"Frozen fixture hash mismatch: {name}")
    cases = []
    for split in ("final", "development"):
        records = list(read_jsonl(directory / "evaluation" / f"{split}.jsonl", EvaluationCase))
        if any(case.split != split for case in records):
            raise ValueError(f"The {split} file contains a case assigned to another split")
        cases.extend(records)
    docs = list(read_jsonl(directory / "source-documents.jsonl", Document))
    by_id = {doc.document_id: doc for doc in docs}
    if len(by_id) != len(docs):
        raise ValueError("Source fixtures contain duplicate document IDs")
    validate_cases(cases, by_id)
    return cases, by_id, manifest


def render_review(cases: list[EvaluationCase], documents: dict[str, Document]) -> str:
    lines = [
        "# Evaluation fixture review sheet",
        "",
        "Generated from the frozen JSONL fixtures. Reference answers are candidates pending "
        "George's independent review.",
        "",
        "HotpotQA excerpts retain their source titles, revision, and sentence labels in "
        "source-documents.jsonl. Fictional sources are explicitly labelled.",
        "",
    ]
    for split in ("development", "final"):
        lines += [f"## {split.title()} cases", ""]
        for case in cases:
            if case.split != split:
                continue
            lines += [
                f"### {case.case_id} ({case.category})",
                "",
                case.question.strip(),
                "",
                f"Expected status: `{case.expected_status}`. Reference answer: "
                f"**{case.gold_answer or 'No single answer'}**.",
                "",
            ]
            if case.expected_facts:
                lines += ["Expected facts: " + "; ".join(case.expected_facts) + ".", ""]
            if not case.evidence:
                lines += [
                    "No labelled supporting evidence. The corpus must not supply an "
                    "approver for this fictional case.",
                    "",
                ]
            for item in case.evidence:
                doc = documents[item.document_id]
                lines += [
                    f"- **{doc.title}**, original sentence {item.sentence_id}, "
                    f"document `{item.document_id}`:",
                    f"  > {item.quote}",
                    "",
                ]
    return "\n".join(lines)
