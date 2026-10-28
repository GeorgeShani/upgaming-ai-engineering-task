"""Score stored outputs offline; no gold labels are passed to investigation."""

from .metrics import answer_scores, contains_fact, document_scores, merge_document_rankings


def score_case(case, result, canonical):
    result = result or {}
    claims = result.get("claims", []) + result.get("conflicting_claims", [])
    text = " ".join(claim["text"] for claim in claims)
    status = result.get("status", "error")
    correct_status = status == case.expected_status
    required = {item.document_id for item in case.evidence}
    traces = result.get("search_trace", [])
    by_id = {hit["evidence_id"]: hit for hit in result.get("evidence", [])}
    context = {hit["document_id"] for hit in by_id.values()}
    retrieved = {hit["document_id"] for trace in traces for hit in trace.get("evidence", [])}
    cited, details = set(), []
    for index, claim in enumerate(claims):
        for citation in claim["citations"]:
            hit = by_id.get(citation["evidence_id"])
            quote = citation["quote"]
            source = canonical.get(hit["document_id"]) if hit else None
            valid = bool(
                hit
                and quote.strip()
                and quote in hit["text"]
                and source is not None
                and source[hit["start"] : hit["end"]] == hit["text"]
            )
            aligned = valid and any(
                label.document_id == hit["document_id"]
                and (label.quote in quote or quote in label.quote)
                for label in case.evidence
            )
            if hit:
                cited.add(hit["document_id"])
            details.append(
                {
                    "claim_index": index,
                    **citation,
                    "document_id": hit["document_id"] if hit else None,
                    "valid": valid,
                    "label_aligned": bool(aligned),
                }
            )
    facts = case.expected_facts or ([case.gold_answer] if case.gold_answer else [])
    fact_checks = {fact: contains_fact(text, fact) for fact in facts}
    counts = {
        "total": len(details),
        "valid": sum(item["valid"] for item in details),
        "label_aligned": sum(item["label_aligned"] for item in details),
    }
    supported = correct_status and (
        not required
        or all(fact_checks.values())
        and required <= cited
        and counts["total"] > 0
        and counts["valid"] == counts["total"]
        and counts["label_aligned"] > 0
    )
    answerable = case.gold_answer is not None
    full, last = text, claims[-1]["text"] if claims else ""
    if not correct_status:
        full = last = ""
    return {
        "status": status,
        "status_correct": correct_status,
        "supported_task_check": bool(supported),
        "retrieval_initial": document_scores(
            traces[0].get("document_ranking", []) if traces else [], required
        ),
        "retrieval_aggregate": document_scores(merge_document_rankings(traces), required),
        "required_sources": len(required),
        "multi_source": len(required) > 1,
        "all_sources_retrieved": required <= retrieved if required else None,
        "all_sources_in_context": required <= context if required else None,
        "all_sources_cited": required <= cited if required else None,
        "answer_full": answer_scores(full, case.gold_answer) if answerable else None,
        "answer_last_claim": answer_scores(last, case.gold_answer) if answerable else None,
        "expected_fact_checks": fact_checks,
        "all_expected_facts": all(fact_checks.values()) if facts else None,
        "citations": counts,
        "citation_details": details,
    }
