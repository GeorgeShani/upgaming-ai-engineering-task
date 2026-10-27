import pytest
from app.investigations.models import AnswerDraft, InvalidEvidence, validate_evidence


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
