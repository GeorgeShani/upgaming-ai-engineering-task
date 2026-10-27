"""Canonical content identity shared by dataset preparation and file ingestion."""

import hashlib
import re
import unicodedata
from uuid import NAMESPACE_URL, uuid5


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def document_id(digest: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"investigation-engine:text:v1:{digest}"))
