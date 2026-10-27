from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..text import content_hash, document_id, normalize_text


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    kind: Literal["hotpotqa", "synthetic"]
    revision: str
    split: str
    record_id: str
    url: str
    license: str


class Segment(StrictModel):
    sentence_id: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class Document(StrictModel):
    document_id: str
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    content_sha256: str
    source: Source
    segments: list[Segment] = Field(min_length=1)

    @model_validator(mode="after")
    def verify_content_and_locations(self):
        if self.text != normalize_text(self.text):
            raise ValueError("Canonical text must be normalized")
        digest = content_hash(self.text)
        if digest != self.content_sha256 or document_id(digest) != self.document_id:
            raise ValueError("Document content hash or identifier does not match its text")
        if len({s.sentence_id for s in self.segments}) != len(self.segments):
            raise ValueError("Sentence identifiers must be unique within a document")
        if any(self.text[s.start : s.end] != s.text for s in self.segments):
            raise ValueError("Sentence locations must match canonical text")
        if " ".join(s.text for s in self.segments) != self.text:
            raise ValueError("Sentence segments must cover all canonical text")
        return self


def make_document(title: str, sentences: list[str], source: Source) -> Document:
    segments = []
    position = 0
    for sentence_id, sentence in enumerate(sentences):
        text = normalize_text(sentence)
        if not text:
            continue
        segments.append(
            Segment(sentence_id=sentence_id, start=position, end=position + len(text), text=text)
        )
        position += len(text) + 1
    text = " ".join(s.text for s in segments)
    digest = content_hash(text)
    return Document(
        document_id=document_id(digest),
        title=normalize_text(title),
        text=text,
        content_sha256=digest,
        source=source,
        segments=segments,
    )


class Evidence(StrictModel):
    document_id: str
    sentence_id: int = Field(ge=0)
    quote: str = Field(min_length=1)


class EvaluationCase(StrictModel):
    case_id: str
    category: Literal["simple", "bridge", "comparison", "unanswerable", "conflict"]
    split: Literal["development", "final"]
    question: str = Field(min_length=1)
    expected_status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    gold_answer: str | None
    expected_facts: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    source_question_id: str | None = None

    @model_validator(mode="after")
    def verify_expected_behaviour(self):
        if self.category == "unanswerable":
            if (
                self.expected_status != "insufficient_evidence"
                or self.gold_answer is not None
                or self.evidence
            ):
                raise ValueError("Unanswerable cases must abstain without fabricated gold evidence")
        elif self.category == "conflict":
            if self.expected_status != "conflicting_evidence" or self.gold_answer is not None:
                raise ValueError("Conflicting cases must not select a single gold answer")
            if len({item.document_id for item in self.evidence}) < 2:
                raise ValueError("Conflicts require at least two source documents")
        elif self.expected_status != "answered" or not self.gold_answer or not self.evidence:
            raise ValueError("Answerable cases need a reference answer and source evidence")
        if self.category in {"bridge", "comparison"}:
            if len({item.document_id for item in self.evidence}) < 2:
                raise ValueError("Multi-source cases require at least two source documents")
        return self
