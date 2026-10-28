from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.security import HTTPBearer
from starlette.concurrency import run_in_threadpool

from .models import DocumentPage, DocumentView, MutationResult
from .parsing import MAX_UPLOAD_BYTES, ParseError, parse_upload

router = APIRouter(prefix="/api/documents", tags=["Documents"])
admin = HTTPBearer(auto_error=False, scheme_name="DemoAdmin")


def service(request: Request):
    if request.app.state.document_service is None:
        raise HTTPException(503, "Configure QDRANT_URL and QDRANT_API_KEY on the server.")
    return request.app.state.document_service


async def parsed_file(request, file):
    try:
        allowed_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "application/octet-stream",
        }
        content_type = (
            (file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
        )
        if content_type not in allowed_types:
            raise HTTPException(415, "Unsupported upload content type.")
        async with request.app.state.parsing_slots:
            raw = await file.read(MAX_UPLOAD_BYTES + 1)
            return await run_in_threadpool(parse_upload, file.filename or "", raw)
    except ParseError as error:
        raise HTTPException(error.status, str(error)) from error
    finally:
        await file.close()


@router.get("", response_model=DocumentPage)
async def list_documents(
    request: Request,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
):
    response.headers["Cache-Control"] = "no-store"
    return await service(request).list_documents(limit, str(cursor) if cursor else None)


@router.get("/{document_id}", response_model=DocumentView)
async def get_document(document_id: UUID, request: Request, response: Response):
    document = await service(request).read(str(document_id))
    response.headers["ETag"] = f'"{document.revision_id}"'
    response.headers["X-Document-ETag"] = f'"{document.revision_id}"'
    response.headers["Cache-Control"] = "no-store"
    return document


@router.post(
    "",
    response_model=MutationResult,
    status_code=201,
    responses={200: {"model": MutationResult}},
    dependencies=[Depends(admin)],
)
async def create_document(request: Request, response: Response, file: UploadFile):
    manager = service(request)
    result = await manager.save(await parsed_file(request, file))
    response.status_code = 200 if result.duplicate else 201
    response.headers["ETag"] = f'"{result.document.revision_id}"'
    response.headers["X-Document-ETag"] = f'"{result.document.revision_id}"'
    return result


@router.put("/{document_id}", response_model=MutationResult, dependencies=[Depends(admin)])
async def replace_document(
    document_id: UUID,
    request: Request,
    response: Response,
    file: UploadFile,
    if_match: Annotated[str | None, Header()] = None,
):
    manager = service(request)
    result = await manager.save(await parsed_file(request, file), str(document_id), if_match)
    response.headers["ETag"] = f'"{result.document.revision_id}"'
    response.headers["X-Document-ETag"] = f'"{result.document.revision_id}"'
    return result


@router.delete("/{document_id}", status_code=204, dependencies=[Depends(admin)])
async def delete_document(
    document_id: UUID, request: Request, if_match: Annotated[str | None, Header()] = None
):
    await service(request).delete(str(document_id), if_match)
    return Response(status_code=204)
