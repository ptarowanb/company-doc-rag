from collections.abc import Sequence
from typing import Annotated, Protocol, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from company_doc_rag.api.schemas import DocumentResponse
from company_doc_rag.domain.documents import Document

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class _DocumentService(Protocol):
    async def upload(self, filename: str, content_type: str, content: bytes) -> Document: ...

    async def list(self) -> Sequence[Document]: ...

    async def get(self, document_id: UUID) -> Document: ...

    async def delete(self, document_id: UUID) -> None: ...


def get_document_service(request: Request) -> _DocumentService:
    service = getattr(request.app.state, "document_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="문서 서비스가 준비되지 않았습니다.",
        )
    return cast(_DocumentService, service)


DocumentServiceDependency = Annotated[_DocumentService, Depends(get_document_service)]
UploadedFile = Annotated[UploadFile, File(description="수집할 PDF 문서")]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadedFile,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    content = await file.read()
    document = await service.upload(
        filename=file.filename or "document.pdf",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(service: DocumentServiceDependency) -> list[DocumentResponse]:
    return [DocumentResponse.model_validate(document) for document in await service.list()]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    return DocumentResponse.model_validate(await service.get(document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    service: DocumentServiceDependency,
) -> Response:
    await service.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

