"""Explicit metrics with denominators kept separate from missing/undefined labels."""

import re
import string
from collections import Counter


def normalize_answer(text):
    # HotpotQA's official normalization, including its yes/no F1 special case below.
    text = "".join(ch for ch in text.lower() if ch not in string.punctuation)
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", text).split())


def answer_scores(prediction, gold):
    prediction, gold = normalize_answer(prediction), normalize_answer(gold)
    exact = float(prediction == gold)
    if (prediction in {"yes", "no", "noanswer"} or gold in {"yes", "no", "noanswer"}) and not exact:
        return {"exact_match": exact, "token_f1": 0.0}
    predicted, expected = prediction.split(), gold.split()
    common = sum((Counter(predicted) & Counter(expected)).values())
    f1 = 2 * common / (len(predicted) + len(expected)) if common else 0.0
    return {"exact_match": exact, "token_f1": f1}


def document_scores(ranking, required):
    if not required:
        return None
    ranking = list(dict.fromkeys(ranking))[:10]
    first = next((rank for rank, key in enumerate(ranking, 1) if key in required), None)
    return {
        "recall_at_5": len(set(ranking[:5]) & required) / len(required),
        "recall_at_10": len(set(ranking) & required) / len(required),
        "mrr_at_10": 1 / first if first else 0.0,
    }


def merge_document_rankings(traces):
    """Diagnostic document-level RRF across executed queries; not the model's context."""
    scores = Counter()
    for trace in traces:
        if trace.get("executed", True):
            for rank, key in enumerate(dict.fromkeys(trace.get("document_ranking", [])), 1):
                scores[key] += 1 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))[:10]


def contains_fact(text, fact):
    # Whole normalized tokens avoid accepting '3 attempts' inside '13 attempts'.
    return f" {normalize_answer(fact)} " in f" {normalize_answer(text)} "


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lo = int(position)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (position - lo)
