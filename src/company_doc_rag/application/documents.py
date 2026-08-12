import hashlib
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from company_doc_rag.domain.documents import Document, DocumentStatus
from company_doc_rag.domain.errors import FileTooLargeError, UnsupportedFileTypeError


class _DocumentRepository(Protocol):
    async def create(self, filename: str, sha256: str, storage_key: str) -> Document: ...

    async def get(self, document_id: UUID) -> Document: ...

    async def list(self) -> Sequence[Document]: ...

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...

    async def delete(self, document_id: UUID) -> None: ...


class _FileStorage(Protocol):
    def save(self, content: bytes) -> str: ...

    def delete(self, key: str) -> None: ...


class _DocumentQueue(Protocol):
    def enqueue(self, document_id: UUID) -> None: ...


class _CacheGeneration(Protocol):
    async def bump_generation(self) -> int: ...


class DocumentService:
    """문서 등록·조회·삭제와 비동기 작업 등록을 조정한다."""

    def __init__(
        self,
        repository: _DocumentRepository,
        storage: _FileStorage,
        queue: _DocumentQueue,
        cache: _CacheGeneration,
        max_upload_bytes: int,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._queue = queue
        self._cache = cache
        self._max_upload_bytes = max_upload_bytes

    async def upload(self, filename: str, content_type: str, content: bytes) -> Document:
        if len(content) > self._max_upload_bytes:
            raise FileTooLargeError("업로드 가능한 파일 크기를 초과했습니다.")
        if (
            content_type != "application/pdf"
            or not filename.lower().endswith(".pdf")
            or not content.startswith(b"%PDF-")
        ):
            raise UnsupportedFileTypeError("PDF 파일만 업로드할 수 있습니다.")

        storage_key = self._storage.save(content)
        document: Document | None = None
        try:
            document = await self._repository.create(
                filename=filename,
                sha256=hashlib.sha256(content).hexdigest(),
                storage_key=storage_key,
            )
            self._queue.enqueue(document.id)
        except Exception:
            if document is not None:
                await self._repository.delete(document.id)
            self._storage.delete(storage_key)
            raise
        return document

    async def list(self) -> Sequence[Document]:
        return await self._repository.list()

    async def get(self, document_id: UUID) -> Document:
        return await self._repository.get(document_id)

    async def delete(self, document_id: UUID) -> None:
        document = await self._repository.get(document_id)
        await self._repository.update_status(document_id, DocumentStatus.DELETING)
        await self._cache.bump_generation()
        self._storage.delete(document.storage_key)
        await self._repository.delete(document_id)
