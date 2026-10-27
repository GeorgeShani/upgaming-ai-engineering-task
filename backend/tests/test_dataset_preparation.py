import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from app.datasets.fixtures import FINAL_COUNTS, freeze_fixtures, load_fixtures, validate_cases
from app.datasets.models import EvaluationCase
from app.datasets.preparation import prepare_bundle, verify_bundle
from pydantic import ValidationError

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def selection():
    return json.loads((FIXTURES / "dataset-selection.json").read_text(encoding="utf-8"))


def training_example():
    _, docs, _ = load_fixtures(FIXTURES)
    seed = next(doc for doc in docs.values() if doc.source.kind == "hotpotqa")
    return {
        "id": "unit-test-row",
        "question": "DO_NOT_INDEX_QUESTION",
        "answer": "DO_NOT_INDEX_ANSWER",
        "context": {
            "title": ["Duplicate seed", "Training A", "Training B", "Training C"],
            "sentences": [
                [s.text for s in seed.segments],
                ["Unique training fact A."],
                ["Unique training fact B."],
                ["Unique training fact C."],
            ],
        },
    }


def target_count():
    _, docs, _ = load_fixtures(FIXTURES)
    return sum(doc.source.kind == "hotpotqa" for doc in docs.values()) + 3


def prepare(output):
    return prepare_bundle([training_example()], selection(), FIXTURES, output, target_count())


def test_frozen_cases_have_exact_categories_and_valid_gold_evidence():
    cases, docs, _ = load_fixtures(FIXTURES)
    assert len(cases) == 48
    assert Counter(c.category for c in cases if c.split == "final") == Counter(FINAL_COUNTS)
    assert all(doc.source.kind in {"hotpotqa", "synthetic"} for doc in docs.values())
    assert all(c.gold_answer is None for c in cases if c.category in {"unanswerable", "conflict"})


def test_repeated_preparation_is_byte_reproducible_and_deduplicates_source_records(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    one, two = prepare(first), prepare(second)
    assert one == two
    assert (first / "corpus.jsonl").read_bytes() == (second / "corpus.jsonl").read_bytes()
    assert one["duplicate_occurrences_skipped"] == 1
    assert one["hotpot_passages"] == target_count()
    assert not one["meets_assignment_minimum"]
    text = (first / "corpus.jsonl").read_text(encoding="utf-8")
    assert "DO_NOT_INDEX_ANSWER" not in text
    assert "DO_NOT_INDEX_QUESTION" not in text
    report = verify_bundle(first, FIXTURES)
    assert report["verified"] and report["evaluation_cases"] == 48


def test_preparation_refuses_overwriting_a_previous_run(tmp_path):
    output = tmp_path / "prepared"
    prepare(output)
    with pytest.raises(FileExistsError, match="already exists"):
        prepare(output)


def test_insufficient_source_does_not_publish_a_partial_bundle(tmp_path):
    output = tmp_path / "prepared"
    with pytest.raises(ValueError, match="Source exhausted"):
        prepare_bundle([], selection(), FIXTURES, output, target_count())
    assert not output.exists()


def test_verify_rejects_tampered_corpus(tmp_path):
    output = tmp_path / "prepared"
    prepare(output)
    with (output / "corpus.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="Corpus hash mismatch"):
        verify_bundle(output, FIXTURES)


def test_frozen_labels_cannot_silently_change(tmp_path):
    directory = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, directory)
    with (directory / "evaluation/final.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="fixture hash mismatch"):
        load_fixtures(directory)
    with pytest.raises(FileExistsError, match="already exist"):
        freeze_fixtures([], directory, selection())


def test_gold_support_must_actually_be_in_the_corpus():
    cases, docs, _ = load_fixtures(FIXTURES)
    evidence = next(c.evidence[0] for c in cases if c.evidence)
    docs.pop(evidence.document_id)
    with pytest.raises(ValueError, match="Missing support"):
        validate_cases(cases, docs)


def test_development_and_final_questions_cannot_overlap():
    cases, docs, _ = load_fixtures(FIXTURES)
    final = next(c for c in cases if c.split == "final")
    dev = next(c for c in cases if c.split == "development")
    duplicated = dev.model_copy(update={"question": final.question})
    with pytest.raises(ValueError, match="must not overlap"):
        validate_cases([duplicated if c.case_id == dev.case_id else c for c in cases], docs)


def test_conflicts_cannot_have_a_single_gold_answer():
    cases, _, _ = load_fixtures(FIXTURES)
    conflict = next(c for c in cases if c.category == "conflict").model_dump()
    with pytest.raises(ValidationError, match="single gold answer"):
        EvaluationCase.model_validate({**conflict, "gold_answer": "Pick one source"})


def test_preparation_rejects_mixing_dataset_revisions(tmp_path):
    with pytest.raises(ValueError, match="different revisions"):
        prepare_bundle(
            [],
            {**selection(), "revision": "wrong"},
            FIXTURES,
            tmp_path / "prepared",
            target_count(),
        )
