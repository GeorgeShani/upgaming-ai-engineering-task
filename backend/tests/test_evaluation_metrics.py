import pytest
from app.evaluation.metrics import answer_scores, document_scores, merge_document_rankings


def test_document_metrics_count_distinct_required_sources_and_rank_first_hit():
    scores = document_scores(["noise", "one", "one", "other", "two"], {"one", "two"})
    assert scores == {"recall_at_5": 1.0, "recall_at_10": 1.0, "mrr_at_10": 0.5}
    assert document_scores(["noise"], {"one"})["mrr_at_10"] == 0
    assert document_scores(["one"], set()) is None
    assert document_scores([str(i) for i in range(9)] + ["one"], {"one", "two"}) == {
        "recall_at_5": 0.0,
        "recall_at_10": 0.5,
        "mrr_at_10": 0.1,
    }


def test_merge_ranks_is_stable_rrf_and_ignores_reused_searches():
    traces = [
        {"executed": True, "document_ranking": ["b", "a", "a"]},
        {"executed": True, "document_ranking": ["a", "c"]},
        {"executed": False, "document_ranking": ["z"]},
    ]
    assert merge_document_rankings(traces) == ["a", "b", "c"]


def test_short_answer_scoring_does_not_extract_gold_from_long_claims():
    assert answer_scores("The North Atlantic Conference.", "North Atlantic Conference") == {
        "exact_match": 1.0,
        "token_f1": 1.0,
    }
    scores = answer_scores("It was 11 minutes of recovery", "11 minutes")
    assert scores["exact_match"] == 0
    assert scores["token_f1"] == pytest.approx(0.5)
    assert answer_scores("yes", "no")["token_f1"] == 0
    assert answer_scores("No, it is Australian", "no")["token_f1"] == 0
