from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..retrieval.chunking import sentence_spans


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(StrictModel):
    evidence_id: str = Field(min_length=2, max_length=10)
    quote: str = Field(
        min_length=1,
        max_length=1500,
        description="A contiguous verbatim substring from this chunk; no inserted ellipses.",
    )


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=500)
    citations: list[Citation] = Field(min_length=1, max_length=4)


class AnswerDraft(StrictModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim] = Field(max_length=8)
    conflicting_claims: list[Claim] = Field(max_length=8)


class QuoteReference(StrictModel):
    evidence_id: str = Field(min_length=2, max_length=10)
    quote_id: str = Field(min_length=2, max_length=10)


class SelectedClaim(StrictModel):
    text: str = Field(min_length=1, max_length=500)
    citations: list[QuoteReference] = Field(min_length=1, max_length=4)


class SelectedAnswer(StrictModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    claims: list[SelectedClaim] = Field(max_length=8)
    conflicting_claims: list[SelectedClaim] = Field(max_length=8)


class Question(StrictModel):
    question: str = Field(min_length=3, max_length=1000)
    strategy: Literal["a", "b"] | None = None


class InvalidEvidence(Exception):
    pass


def quote_catalog(evidence):
    """Keep source text in context, never in a schema enum of arbitrary string literals."""
    quotes = {}
    for item in evidence:
        text = item["text"]
        # Whole chunks/fragments cover all text. Sentence options allow shorter
        # quotations; cap extra choices to keep the schema small and predictable.
        fragments = [text[start : start + 1000] for start in range(0, len(text), 1000)]
        sentences = [text[start:end] for start, end in sentence_spans(text)]
        choices = list(dict.fromkeys(fragments + sentences))
        for quote in choices[: max(16, len(fragments))]:
            if quote.strip() and len(quote) <= 1500:
                quotes[f"Q{len(quotes) + 1}"] = {"evidence_id": item["evidence_id"], "quote": quote}
    return quotes


def answer_schema(evidence, catalog):
    schema = SelectedAnswer.model_json_schema()
    properties = schema["$defs"]["QuoteReference"]["properties"]
    properties["evidence_id"]["enum"] = [item["evidence_id"] for item in evidence]
    properties["quote_id"]["enum"] = list(catalog)
    return schema


def resolve_quotes(raw, catalog):
    selected = SelectedAnswer.model_validate(raw)
    result = {"status": selected.status}
    for field in ("claims", "conflicting_claims"):
        claims = []
        for claim in getattr(selected, field):
            citations = []
            for reference in claim.citations:
                quote = catalog.get(reference.quote_id)
                if quote is None or quote["evidence_id"] != reference.evidence_id:
                    raise InvalidEvidence
                citations.append({"evidence_id": reference.evidence_id, "quote": quote["quote"]})
            claims.append({"text": claim.text, "citations": citations})
        result[field] = claims
    return AnswerDraft.model_validate(result)


def validate_evidence(draft, evidence):
    sources = {item["evidence_id"]: item for item in evidence}
    for claim in draft.claims + draft.conflicting_claims:
        if not claim.text.strip() or not claim.citations:
            raise InvalidEvidence
        for citation in claim.citations:
            source = sources.get(citation.evidence_id)
            if source is None or not citation.quote.strip() or citation.quote not in source["text"]:
                raise InvalidEvidence
    if draft.status == "answered" and (not draft.claims or draft.conflicting_claims):
        raise InvalidEvidence
    if draft.status == "insufficient_evidence" and (draft.claims or draft.conflicting_claims):
        raise InvalidEvidence
    if draft.status == "conflicting_evidence":
        documents = {
            sources[c.evidence_id]["document_id"]
            for claim in draft.conflicting_claims
            for c in claim.citations
        }
        if len(draft.conflicting_claims) < 2 or len(documents) < 2:
            raise InvalidEvidence
    # Exact quotes/known IDs prove citation integrity. Whether each quote entails its
    # claim and whether claims contradict each other still need semantic evaluation.
    return draft
