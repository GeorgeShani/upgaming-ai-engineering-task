from collections import Counter


def fuse(rankings, limit=8, per_document=2):
    """Reciprocal rank fusion: relevance ordering, never confidence or probability."""
    scores, hits = {}, {}
    for ranking in rankings:
        seen = set()
        rank = 0
        for hit in ranking:
            key = str(hit["id"])
            if key in seen:
                continue
            seen.add(key)
            rank += 1
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
            hits[key] = hit
    result, counts = [], Counter()
    for key in sorted(scores, key=lambda key: (-scores[key], key)):
        doc = hits[key]["payload"]["document_id"]
        if counts[doc] >= per_document:
            continue
        result.append({**hits[key], "fusion_score": scores[key]})
        counts[doc] += 1
        if len(result) == limit:
            break
    return result
