"""Aggregate transparent denominators; a failed paid attempt remains a failed case."""

from collections import Counter

from .metrics import mean, percentile
from .scoring import score_case


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def ledger_delta(row, name):
    return row.get("ledger_after", {}).get(name, 0) - row.get("ledger_before", {}).get(name, 0)


def summarize(records, cases, canonical):
    scores = [
        {
            "case_id": row["case_id"],
            "strategy": row["strategy"],
            "category": cases[row["case_id"]].category,
            **score_case(cases[row["case_id"]], row.get("result"), canonical),
        }
        for row in records
    ]
    summaries = {}
    for strategy in ("a", "b"):
        rows = [row for row in records if row["strategy"] == strategy]
        values = [row for row in scores if row["strategy"] == strategy]
        citations = {
            key: sum(row["citations"][key] for row in values)
            for key in ("total", "valid", "label_aligned")
        }
        confusion = Counter(
            (cases[row["case_id"]].expected_status, row["status"]) for row in values
        )
        detection = {}
        for status in ("insufficient_evidence", "conflicting_evidence"):
            tp = confusion[status, status]
            expected = sum(n for (gold, _), n in confusion.items() if gold == status)
            predicted = sum(n for (_, pred), n in confusion.items() if pred == status)
            detection[status] = {
                "true_positive": tp,
                "expected": expected,
                "predicted": predicted,
                "precision": ratio(tp, predicted),
                "recall": ratio(tp, expected),
            }
        latency = [row["elapsed_ms"] for row in rows if row.get("elapsed_ms") is not None]
        summaries[strategy] = {
            "attempts": len(rows),
            "successes": sum(row.get("result") is not None for row in rows),
            "errors": sum(row.get("result") is None for row in rows),
            "status_accuracy": mean(row["status_correct"] for row in values),
            "supported_task_checks": sum(row["supported_task_check"] for row in values),
            "supported_task_rate": mean(row["supported_task_check"] for row in values),
            "retrieval_labelled_cases": sum(row["required_sources"] > 0 for row in values),
            **{
                field: {
                    metric: mean(row[field][metric] for row in values if row[field] is not None)
                    for metric in ("recall_at_5", "recall_at_10", "mrr_at_10")
                }
                for field in ("retrieval_initial", "retrieval_aggregate")
            },
            "multi_source_cases": sum(row["multi_source"] for row in values),
            **{
                field: mean(row[field] for row in values if row["multi_source"])
                for field in (
                    "all_sources_retrieved",
                    "all_sources_in_context",
                    "all_sources_cited",
                )
            },
            "short_reference_cases": sum(row["answer_full"] is not None for row in values),
            **{
                field: {
                    metric: mean(row[field][metric] for row in values if row[field] is not None)
                    for metric in ("exact_match", "token_f1")
                }
                for field in ("answer_full", "answer_last_claim")
            },
            "all_expected_facts": mean(row["all_expected_facts"] for row in values),
            "citation_counts": citations,
            "citation_validity": ratio(citations["valid"], citations["total"]),
            "labelled_citation_precision": ratio(citations["label_aligned"], citations["total"]),
            "status_confusion": [
                {"expected": gold, "predicted": pred, "count": n}
                for (gold, pred), n in sorted(confusion.items())
            ],
            "detection": detection,
            "latency": {
                "measured_attempts": len(latency),
                "median_ms": percentile(latency, 0.5),
                "p95_ms": percentile(latency, 0.95),
            },
            "known_estimated_cost_usd": round(
                sum(ledger_delta(row, "estimated_actual_usd") for row in rows), 8
            ),
            "reserved_cost_usd": round(sum(ledger_delta(row, "reserved_usd") for row in rows), 8),
            "input_tokens": sum(ledger_delta(row, "input_tokens") for row in rows),
            "output_tokens": sum(ledger_delta(row, "output_tokens") for row in rows),
            "provider_calls": sum(ledger_delta(row, "calls") for row in rows),
            "embedding_cache_hits": sum(
                usage["cache_hits"]
                for row in rows
                for usage in (row.get("result") or {}).get("usage", {}).get("embeddings", [])
            ),
        }
    return summaries, scores


def select_strategy(summaries):
    def key(strategy):
        value = summaries[strategy]
        return (
            value["supported_task_checks"],
            value["all_sources_in_context"] or 0,
            value["retrieval_initial"]["recall_at_10"] or 0,
            strategy == "a",
        )

    return max(("a", "b"), key=key)
