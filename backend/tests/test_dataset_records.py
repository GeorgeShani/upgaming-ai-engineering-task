import pytest
from app.datasets.hotpot import context_documents, labelled_case
from app.datasets.models import Document, Source, make_document
from pydantic import ValidationError


def source():
    return Source(
        kind="synthetic",
        revision="v1",
        split="fixture",
        record_id="example",
        url="fixture://example",
        license="CC0-1.0",
    )


def example_row():
    return {
        "id": "example",
        "type": "bridge",
        "question": "Where is the employer based?",
        "answer": "Tbilisi",
        "context": {
            "title": ["Employee", "Company"],
            "sentences": [["Mira works at Example Co."], ["Example Co. is based in Tbilisi."]],
        },
        "supporting_facts": {"title": ["Employee", "Company"], "sent_id": [0, 0]},
    }


def test_whitespace_duplicates_have_stable_content_ids_and_original_sentence_ids():
    first = make_document("First title", [" Hello\n world. ", "", "Another fact."], source())
    second = make_document("Other title", ["Hello world.", "Another fact."], source())
    assert first.document_id == second.document_id
    assert first.content_sha256 == second.content_sha256
    assert [s.sentence_id for s in first.segments] == [0, 2]
    assert all(first.text[s.start : s.end] == s.text for s in first.segments)


def test_changed_text_is_a_distinct_source_record():
    assert (
        make_document("A", ["Value 3."], source()).document_id
        != make_document("A", ["Value 5."], source()).document_id
    )


def test_corpus_records_reject_evaluation_labels():
    record = make_document("A", ["A fact."], source()).model_dump()
    for forbidden in ("question", "answer", "supporting_facts"):
        with pytest.raises(ValidationError):
            Document.model_validate({**record, forbidden: "label must not enter corpus"})


def test_hotpot_preserves_native_support_and_keeps_labels_out_of_documents():
    case, docs = labelled_case(example_row(), "pinned-revision", "final", "final-bridge-01")
    assert case.gold_answer == "Tbilisi"
    assert len({e.document_id for e in case.evidence}) == 2
    assert case.evidence[0].sentence_id == 0
    assert docs[0].source.revision == "pinned-revision"
    assert "question" not in docs[0].model_dump()


def test_mismatched_context_arrays_fail_instead_of_silently_dropping_sources():
    row = example_row()
    row["context"]["title"].append("Missing paragraph")
    with pytest.raises(ValueError, match="different lengths"):
        context_documents(row, "revision", "train")


def test_tampered_text_or_locations_fail_validation():
    record = make_document("A", ["Original fact."], source()).model_dump()
    record["text"] = "Changed fact."
    with pytest.raises(ValidationError, match="content hash"):
        Document.model_validate(record)
    record = make_document("A", ["Original fact."], source()).model_dump()
    record["segments"][0]["start"] = 2
    with pytest.raises(ValidationError, match="locations"):
        Document.model_validate(record)
