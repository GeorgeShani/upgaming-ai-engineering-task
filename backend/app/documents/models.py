from typing import Literal

from pydantic import BaseModel, ConfigDict


class Location(BaseModel):
    kind: Literal["page", "paragraph", "table_row"]
    number: int
    start: int
    end: int
    text: str


class ParsedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    format: Literal["pdf", "docx", "txt"]
    title: str
    text: str
    content_sha256: str
    locations: list[Location]
    metadata: dict[str, str]


class Revision(ParsedDocument):
    document_id: str
    revision_id: str
    created_at: str


class DocumentSummary(BaseModel):
    document_id: str
    revision_id: str
    filename: str
    title: str
    format: Literal["pdf", "docx", "txt"]
    content_sha256: str
    created_at: str
    updated_at: str
    # Parsed content is durable, but has not been embedded/indexed in this slice.
    index_status: Literal["pending"] = "pending"


class DocumentView(DocumentSummary):
    text: str
    locations: list[Location]
    metadata: dict[str, str]


class MutationResult(BaseModel):
    document: DocumentSummary
    duplicate: bool


class DocumentPage(BaseModel):
    items: list[DocumentSummary]
    next_cursor: str | None
