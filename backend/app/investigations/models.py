from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(StrictModel):
    evidence_id: str = Field(min_length=2, max_length=10)
    quote: str = Field(min_length=8, max_length=1500)


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=500)
    citations: list[Citation] = Field(min_length=1, max_length=4)


class AnswerDraft(StrictModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim] = Field(max_length=8)
    conflicting_claims: list[Claim] = Field(max_length=8)


class Question(StrictModel):
    question: str = Field(min_length=3, max_length=1000)
    strategy: Literal["a", "b"] | None = None


class InvalidEvidence(Exception):
    pass


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
