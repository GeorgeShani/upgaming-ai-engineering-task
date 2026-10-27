import pytest
from app.investigations.models import (
    AnswerDraft,
    InvalidEvidence,
    answer_schema,
    quote_catalog,
    resolve_quotes,
    validate_evidence,
)


def evidence():
    return [
        {
            "evidence_id": "E1",
            "document_id": "doc-one",
            "text": "The payment router recovered after 12 minutes.",
        }
    ]


def draft(**changes):
    data = {
        "status": "answered",
        "claims": [
            {
                "text": "Recovery took 12 minutes.",
                "citations": [{"evidence_id": "E1", "quote": "recovered after 12 minutes"}],
            }
        ],
        "conflicting_claims": [],
    }
    data.update(changes)
    return AnswerDraft.model_validate(data)


def test_valid_quotes_and_claim_references():
    result = validate_evidence(draft(), evidence())
    assert result.claims[0].citations[0].evidence_id == "E1"


def test_editorially_abridged_quote_is_rejected_even_if_its_words_appear_in_order():
    result = draft()
    result.claims[0].citations[0].quote = "The payment router ... after 12 minutes."
    with pytest.raises(InvalidEvidence):
        validate_evidence(result, evidence())


def test_generation_schema_constrains_quote_choices_to_actual_source_substrings():
    sources = evidence()
    catalog = quote_catalog(sources)
    schema = answer_schema(sources, catalog)
    properties = schema["$defs"]["QuoteReference"]["properties"]
    assert properties["evidence_id"]["enum"] == ["E1"]
    assert properties["quote_id"]["enum"] == ["Q1"]
    assert catalog["Q1"]["quote"] == sources[0]["text"]


def test_short_source_still_has_a_valid_quote_choice():
    sources = [{"evidence_id": "E1", "document_id": "one", "text": "Paris"}]
    assert quote_catalog(sources)["Q1"]["quote"] == "Paris"


@pytest.mark.parametrize("reference", ["Q999", "Q2"])
def test_quote_resolution_rejects_unknown_or_mismatched_source(reference):
    sources = evidence() + [
        {"evidence_id": "E2", "document_id": "two", "text": "A separate fictional source."}
    ]
    raw = {
        "status": "answered",
        "claims": [
            {
                "text": "Claim",
                "citations": [
                    {"evidence_id": "E1", "quote_id": reference},
                ],
            }
        ],
        "conflicting_claims": [],
    }
    with pytest.raises(InvalidEvidence):
        resolve_quotes(raw, quote_catalog(sources))


def test_quotes_with_double_quotation_marks_stay_in_context_not_schema_enums():
    sources = [{"evidence_id": "E1", "document_id": "one", "text": 'He wrote "the book".'}]
    catalog = quote_catalog(sources)
    raw = {
        "status": "answered",
        "claims": [
            {
                "text": "He wrote the book.",
                "citations": [
                    {"evidence_id": "E1", "quote_id": "Q1"},
                ],
            }
        ],
        "conflicting_claims": [],
    }
    result = validate_evidence(resolve_quotes(raw, catalog), sources)
    assert result.claims[0].citations[0].quote == sources[0]["text"]
    assert answer_schema(sources, catalog)["$defs"]["QuoteReference"]["properties"]["quote_id"][
        "enum"
    ] == ["Q1"]


def test_conflict_needs_distinct_documents_even_when_two_chunks_are_cited():
    sources = [
        {"evidence_id": "E1", "document_id": "same", "text": "Retry limit was 3 attempts."},
        {"evidence_id": "E2", "document_id": "same", "text": "Retry limit was 5 attempts."},
    ]
    result = draft(
        status="conflicting_evidence",
        claims=[],
        conflicting_claims=[
            {
                "text": item["text"],
                "citations": [{"evidence_id": item["evidence_id"], "quote": item["text"]}],
            }
            for item in sources
        ],
    )
    with pytest.raises(InvalidEvidence):
        validate_evidence(result, sources)


@pytest.mark.parametrize(
    "mode",
    ["unknown_id", "invented_quote", "uncited_claim", "false_abstention", "unsupported_conflict"],
)
def test_invalid_citations_or_status_contracts_are_rejected(mode):
    result = draft()
    if mode == "unknown_id":
        result.claims[0].citations[0].evidence_id = "E999"
    elif mode == "invented_quote":
        result.claims[0].citations[0].quote = "recovered after 8 minutes"
    elif mode == "uncited_claim":
        result.claims[0].citations = []
    elif mode == "false_abstention":
        result.status = "insufficient_evidence"
    else:
        result.status = "conflicting_evidence"
        result.conflicting_claims = [result.claims.pop()]
    with pytest.raises(InvalidEvidence):
        validate_evidence(result, evidence())
