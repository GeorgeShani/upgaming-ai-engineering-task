import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from .models import (
    DocumentPage,
    DocumentSummary,
    DocumentView,
    MutationResult,
    ParsedDocument,
    Revision,
)
from .store import QdrantDocumentStore, StoreUnavailable


class DocumentService:
    def __init__(self, store: QdrantDocumentStore, indexer=None):
        self.store = store
        self.indexer = indexer
        # One process is part of the deployment contract. This is not a distributed lock.
        self.mutation_lock = asyncio.Lock()

    async def current(self, document_id):
        manifest = await self.store.get(self.store.documents, document_id)
        if manifest is None or manifest.get("deleted") is not False:
            raise HTTPException(404, "Document not found.")
        return manifest

    async def read(self, document_id):
        manifest = await self.current(document_id)
        revision = await self.store.get(self.store.revisions, manifest["revision_id"])
        if revision is None or revision["document_id"] != document_id:
            raise StoreUnavailable
        return DocumentView(
            **DocumentSummary.model_validate(manifest).model_dump(),
            text=revision["text"],
            locations=revision["locations"],
            metadata=revision["metadata"],
        )

    async def list_documents(self, limit, cursor):
        items, next_cursor = await self.store.scroll(limit=limit, cursor=cursor)
        return DocumentPage(
            items=[DocumentSummary.model_validate(item) for item in items], next_cursor=next_cursor
        )

    @staticmethod
    def check_version(manifest, if_match):
        if if_match is None:
            raise HTTPException(428, "Supply the document's ETag in the If-Match header.")
        if if_match != f'"{manifest["revision_id"]}"':
            raise HTTPException(412, "Document changed. Reload it before editing or deleting.")

    async def save(self, parsed: ParsedDocument, document_id=None, if_match=None):
        async with self.mutation_lock:
            old = await self.current(document_id) if document_id else None
            if old:
                self.check_version(old, if_match)
            await self.store.initialize()
            duplicates, _ = await self.store.scroll(limit=1, digest=parsed.content_sha256)
            if duplicates:
                duplicate = duplicates[0]
                if old and duplicate["document_id"] != document_id:
                    raise HTTPException(
                        409,
                        {
                            "message": "Content belongs to another active document.",
                            "document_id": duplicate["document_id"],
                        },
                    )
                return MutationResult(
                    document=DocumentSummary.model_validate(duplicate), duplicate=True
                )
            now = datetime.now(UTC).isoformat()
            document_id = document_id or str(uuid4())
            revision = Revision(
                **parsed.model_dump(),
                document_id=document_id,
                revision_id=str(uuid4()),
                created_at=now,
            )
            # Persist all prepared content before committing the active revision pointer.
            await self.store.put(self.store.revisions, revision.revision_id, revision.model_dump())
            if self.indexer:
                await self.indexer.prepare([revision])
            manifest = DocumentSummary(
                document_id=document_id,
                revision_id=revision.revision_id,
                filename=parsed.filename,
                title=parsed.title,
                format=parsed.format,
                content_sha256=parsed.content_sha256,
                created_at=old["created_at"] if old else now,
                updated_at=now,
                index_status="ready" if self.indexer else "pending",
                index_profile=self.indexer.profile if self.indexer else None,
            )
            await self.store.put(
                self.store.documents, document_id, {**manifest.model_dump(), "deleted": False}
            )
            return MutationResult(document=manifest, duplicate=False)

    async def delete(self, document_id, if_match):
        async with self.mutation_lock:
            manifest = await self.current(document_id)
            self.check_version(manifest, if_match)
            await self.store.put(
                self.store.documents,
                document_id,
                {**manifest, "deleted": True, "updated_at": datetime.now(UTC).isoformat()},
            )

    async def filter_active_revisions(
        self, candidates: list[tuple[str, str]]
    ) -> list[tuple[str, str]]:
        """Slice 4 must apply this gate to retrieved chunk (document, revision) pairs."""
        manifests = await self.store.get_many(
            self.store.documents, list({doc for doc, _ in candidates})
        )
        return [
            (doc, rev)
            for doc, rev in candidates
            if doc in manifests
            and manifests[doc].get("deleted") is False
            and manifests[doc]["revision_id"] == rev
        ]
