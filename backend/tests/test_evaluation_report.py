from app.evaluation.reporting import select_strategy, summarize
from test_evaluation_scoring import case, result


def test_summary_keeps_failures_in_quality_denominators_and_costs():
    sample = case()
    sample.case_id = "test"
    sample.category = "simple"
    rows = [
        {
            "case_id": "test",
            "strategy": "a",
            "result": result(),
            "elapsed_ms": 10,
            "ledger_before": {"estimated_actual_usd": 0},
            "ledger_after": {"estimated_actual_usd": 0.1},
        },
        {
            "case_id": "test",
            "strategy": "b",
            "result": None,
            "error": "provider_failure",
            "elapsed_ms": 30,
            "ledger_before": {"estimated_actual_usd": 0.1},
            "ledger_after": {"estimated_actual_usd": 0.15},
        },
    ]
    report, scores = summarize(rows, {"test": sample}, {"one": "🚀 11 minutes"})
    assert report["a"]["supported_task_checks"] == 1
    assert report["b"]["attempts"] == 1 and report["b"]["errors"] == 1
    assert report["b"]["status_accuracy"] == 0
    assert report["b"]["citation_validity"] is None
    assert report["b"]["known_estimated_cost_usd"] == 0.05
    assert len(scores) == 2
    assert select_strategy(report) == "a"
    assert select_strategy({"a": report["a"], "b": report["a"]}) == "a"
