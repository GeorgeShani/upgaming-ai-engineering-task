from types import SimpleNamespace

from app.evaluation.scoring import score_case


def case(category="bridge"):
    return SimpleNamespace(
        expected_status="answered",
        category=category,
        expected_facts=[],
        gold_answer="11 minutes",
        evidence=[SimpleNamespace(document_id="one", quote="11 minutes")],
    )


def result(quote="11 minutes", document="one"):
    return {
        "status": "answered",
        "claims": [
            {
                "text": "Recovery took 11 minutes.",
                "citations": [{"evidence_id": "E1", "quote": quote}],
            }
        ],
        "conflicting_claims": [],
        "evidence": [
            {
                "evidence_id": "E1",
                "document_id": document,
                "text": "11 minutes",
                "start": 2,
                "end": 12,
            }
        ],
        "search_trace": [
            {
                "executed": True,
                "document_ranking": ["noise", "one"],
                "evidence": [{"document_id": "one"}],
            }
        ],
    }


def test_citation_text_identity_is_separate_from_label_alignment_and_answer_wording():
    scored = score_case(case(), result(), {"one": "🚀 11 minutes"})
    assert scored["supported_task_check"]
    assert scored["answer_last_claim"]["exact_match"] == 0
    assert scored["citations"] == {"total": 1, "valid": 1, "label_aligned": 1}
    other = score_case(case(), result(document="other"), {"other": "🚀 11 minutes"})
    assert other["citations"]["valid"] == 1
    assert other["citations"]["label_aligned"] == 0
    assert not other["supported_task_check"]


def test_invalid_quote_and_provider_failure_cannot_receive_free_success():
    assert (
        score_case(case(), result(quote="99 minutes"), {"one": "🚀 11 minutes"})["citations"][
            "valid"
        ]
        == 0
    )
    failed = score_case(case(), None, {})
    assert failed["status"] == "error"
    assert failed["answer_last_claim"]["token_f1"] == 0
    assert failed["retrieval_aggregate"]["recall_at_10"] == 0
    assert not failed["supported_task_check"]


def test_empty_unanswerable_result_is_a_valid_abstention_but_has_no_citation_score():
    absent = case("unanswerable")
    absent.evidence, absent.gold_answer, absent.expected_status = [], None, "insufficient_evidence"
    scored = score_case(absent, {"status": "insufficient_evidence"}, {})
    assert scored["supported_task_check"]
    assert scored["retrieval_initial"] is None
    assert scored["answer_full"] is None
    assert scored["citations"] == {"total": 0, "valid": 0, "label_aligned": 0}
