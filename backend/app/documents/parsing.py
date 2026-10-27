import re
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

from docx import Document as WordDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader, apply_configuration

from ..text import content_hash, normalize_text
from .models import Location, ParsedDocument

MAX_UPLOAD_BYTES = 5_000_000
MAX_TEXT_CHARS = 1_000_000
MAX_UNITS = 2000


class ParseError(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def parse_pdf(data: bytes):
    if not data.startswith(b"%PDF-"):
        raise ParseError("The file does not have a PDF signature.")
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        raise ParseError("Encrypted PDFs are unsupported. Upload an unencrypted copy.")
    if len(reader.pages) > 200:
        raise ParseError("PDFs are limited to 200 pages.")
    units = []
    total = 0
    decoded_bytes = 0
    for number, page in enumerate(reader.pages, 1):
        contents = page.get_contents()
        if contents is not None:
            size = len(contents.get_data())
            decoded_bytes += size
            if size > 5_000_000 or decoded_bytes > 10_000_000:
                raise ParseError("PDF decoded content exceeds the processing limit.")
        text = page.extract_text() or ""
        total += len(text)
        if total > MAX_TEXT_CHARS:
            raise ParseError("Extracted document text exceeds the character limit.")
        units.append(("page", number, text))
    metadata = reader.metadata
    details = {
        key: str(value)[:500]
        for key, value in {
            "title": getattr(metadata, "title", None),
            "author": getattr(metadata, "author", None),
        }.items()
        if value
    }
    details["page_count"] = str(len(reader.pages))
    empty_pages = [str(number) for _, number, text in units if not normalize_text(text)]
    if empty_pages:
        details["pages_without_text"] = ", ".join(empty_pages)
    return units, details


def parse_docx(data: bytes):
    if not data.startswith(b"PK"):
        raise ParseError("The file does not have a DOCX ZIP signature.")
    with ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(item.file_size for item in entries) > 20_000_000:
            raise ParseError("DOCX expanded content exceeds the archive limit.")
        if any(item.flag_bits & 1 for item in entries):
            raise ParseError("Encrypted DOCX files are unsupported.")
        if "word/document.xml" not in archive.namelist():
            raise ParseError("The ZIP archive is not a Word document.")
    doc = WordDocument(BytesIO(data))
    units = []
    paragraph, table_row = 0, 0

    def cell_text(container, depth=0):
        if depth > 10:
            raise ParseError("DOCX table nesting exceeds the limit.")
        parts = []
        for block in container.iter_inner_content():
            if len(parts) >= MAX_UNITS:
                raise ParseError("DOCX contains too many text blocks.")
            if isinstance(block, Paragraph):
                parts.append(block.text)
            elif isinstance(block, Table):
                for row in block.rows:
                    if len(parts) >= MAX_UNITS:
                        raise ParseError("DOCX contains too many text blocks.")
                    parts.append(" | ".join(cell_text(cell, depth + 1) for cell in row.cells))
        return " ".join(parts)

    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            paragraph += 1
            units.append(("paragraph", paragraph, block.text))
        elif isinstance(block, Table):
            for row in block.rows:
                if len(units) >= MAX_UNITS:
                    raise ParseError("DOCX contains too many text blocks.")
                table_row += 1
                units.append(("table_row", table_row, " | ".join(cell_text(c) for c in row.cells)))
        if len(units) > MAX_UNITS:
            raise ParseError("DOCX contains too many text blocks.")
    return units, {
        key: str(value)[:500]
        for key, value in {
            "title": doc.core_properties.title,
            "author": doc.core_properties.author,
        }.items()
        if value
    }


def parse_upload(filename: str, data: bytes) -> ParsedDocument:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ParseError("Files must be at most 5 MB.", 413)
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    name = "".join(c for c in name if c.isprintable())[:200]
    extension = PurePosixPath(name).suffix.lower().lstrip(".")
    if extension not in {"pdf", "docx", "txt"}:
        raise ParseError("Supported file extensions are PDF, DOCX, and TXT.", 415)
    if not data:
        raise ParseError("The file is empty.")
    try:
        if extension == "pdf":
            with apply_configuration(
                maximum_declared_stream_length=5_000_000,
                zlib_maximum_output_length=5_000_000,
                array_based_stream_maximum_output_length=5_000_000,
                lzw_maximum_output_length=5_000_000,
                run_length_maximum_output_length=5_000_000,
                brotli_maximum_output_length=5_000_000,
                stream_filters_maximum_length=8,
                stream_decoding_work_maximum_length=20_000_000,
                stream_parsing_work_maximum_count=200_000,
                xform_maximum_invocations_per_extraction=500,
            ):
                units, metadata = parse_pdf(data)
        elif extension == "docx":
            units, metadata = parse_docx(data)
        else:
            raw = data.decode("utf-8-sig")
            if any(ord(c) < 32 and c not in "\n\r\t\f" for c in raw):
                raise ParseError("TXT must contain UTF-8 text, not binary data.")
            units = [
                ("paragraph", n, text)
                for n, text in enumerate(
                    re.split(r"\n\s*\n", raw.replace("\r\n", "\n"), maxsplit=MAX_UNITS), 1
                )
            ]
            metadata = {}
    except ParseError:
        raise
    except UnicodeDecodeError as error:
        raise ParseError("TXT must use UTF-8 encoding.") from error
    except Exception as error:
        # Parser exceptions may include uploaded content; never expose their messages.
        raise ParseError(
            "Cannot parse this document. Check that the file is valid and unencrypted."
        ) from error
    locations, position = [], 0
    for kind, number, raw in units:
        text = normalize_text(raw)
        if not text:
            continue
        if position + len(text) > MAX_TEXT_CHARS or len(locations) >= MAX_UNITS:
            raise ParseError("Extracted document text exceeds the processing limit.")
        locations.append(
            Location(kind=kind, number=number, start=position, end=position + len(text), text=text)
        )
        position += len(text) + 1
    text = " ".join(unit.text for unit in locations)
    if not text:
        raise ParseError(
            "No extractable text found. Scanned PDFs require OCR, which is not supported."
        )
    return ParsedDocument(
        filename=name,
        format=extension,
        title=normalize_text(metadata.get("title", "")) or name,
        text=text,
        content_sha256=content_hash(text),
        locations=locations,
        metadata=metadata,
    )
