from pathlib import Path
from uuid import UUID

import pytest

from company_doc_rag.application.documents import DocumentService
from company_doc_rag.domain.documents import Document, DocumentStatus
from company_doc_rag.domain.errors import FileTooLargeError, UnsupportedFileTypeError


class 가짜_저장소:
    def __init__(self) -> None:
        self.document: Document | None = None

    async def create(self, filename: str, sha256: str, storage_key: str) -> Document:
        self.document = Document(filename=filename, sha256=sha256, storage_key=storage_key)
        return self.document

    async def get(self, document_id: UUID) -> Document:
        assert self.document is not None
        return self.document

    async def list(self) -> list[Document]:
        return [self.document] if self.document else []

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        assert self.document is not None
        self.document = Document(
            id=document_id,
            filename=self.document.filename,
            sha256=self.document.sha256,
            storage_key=self.document.storage_key,
            status=status,
            error_code=error_code,
            error_message=error_message,
            created_at=self.document.created_at,
            updated_at=self.document.updated_at,
        )

    async def delete(self, document_id: UUID) -> None:
        self.document = None


class 가짜_파일_저장소:
    def __init__(self) -> None:
        self.content = b""
        self.deleted = False
        self.delete_error: Exception | None = None

    def save(self, content: bytes) -> str:
        self.content = content
        return "id.pdf"

    def delete(self, key: str) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted = True

    def path_for(self, key: str) -> Path:
        return Path(key)


class 가짜_큐:
    def __init__(self) -> None:
        self.document_id: UUID | None = None
        self.error: Exception | None = None

    def enqueue(self, document_id: UUID) -> None:
        if self.error is not None:
            raise self.error
        self.document_id = document_id


class 가짜_캐시:
    def __init__(self) -> None:
        self.generation = 0
        self.error: Exception | None = None

    async def bump_generation(self) -> int:
        if self.error is not None:
            raise self.error
        self.generation += 1
        return self.generation


def 서비스(max_upload_bytes: int = 20):
    repository = 가짜_저장소()
    storage = 가짜_파일_저장소()
    queue = 가짜_큐()
    cache = 가짜_캐시()
    service = DocumentService(repository, storage, queue, cache, max_upload_bytes)
    return service, repository, storage, queue, cache


@pytest.mark.asyncio
async def test_PDF_시그니처를_확인하고_작업을_등록한다() -> None:
    service, _, storage, queue, _ = 서비스()

    document = await service.upload("guide.pdf", "application/pdf", b"%PDF-content")

    assert storage.content == b"%PDF-content"
    assert queue.document_id == document.id


@pytest.mark.asyncio
async def test_확장자만_PDF인_파일을_거부한다() -> None:
    service, _, _, _, _ = 서비스()

    with pytest.raises(UnsupportedFileTypeError):
        await service.upload("guide.pdf", "application/pdf", b"not-pdf")


@pytest.mark.asyncio
async def test_최대_크기를_초과한_파일을_거부한다() -> None:
    service, _, _, _, _ = 서비스(max_upload_bytes=5)

    with pytest.raises(FileTooLargeError):
        await service.upload("guide.pdf", "application/pdf", b"%PDF-too-large")


@pytest.mark.asyncio
async def test_문서_삭제시_원본과_검색_캐시를_무효화한다() -> None:
    service, _, storage, _, cache = 서비스()
    document = await service.upload("guide.pdf", "application/pdf", b"%PDF-content")

    await service.delete(document.id)

    assert storage.deleted is True
    assert cache.generation == 1


@pytest.mark.asyncio
async def test_작업_등록이_실패하면_생성한_문서와_원본을_정리한다() -> None:
    service, repository, storage, queue, _ = 서비스()
    queue.error = RuntimeError("broker unavailable")

    with pytest.raises(RuntimeError, match="broker unavailable"):
        await service.upload("guide.pdf", "application/pdf", b"%PDF-content")

    assert repository.document is None
    assert storage.deleted is True


@pytest.mark.asyncio
async def test_원본_삭제가_실패하면_문서_행을_보존한다() -> None:
    service, repository, storage, _, cache = 서비스()
    document = await service.upload("guide.pdf", "application/pdf", b"%PDF-content")
    storage.delete_error = OSError("disk unavailable")

    with pytest.raises(OSError, match="disk unavailable"):
        await service.delete(document.id)

    assert repository.document is not None
    assert repository.document.status.value == "DELETING"
    assert cache.generation == 1


@pytest.mark.asyncio
async def test_캐시_무효화가_실패하면_문서_행을_보존한다() -> None:
    service, repository, storage, _, cache = 서비스()
    document = await service.upload("guide.pdf", "application/pdf", b"%PDF-content")
    cache.error = RuntimeError("redis unavailable")

    with pytest.raises(RuntimeError, match="redis unavailable"):
        await service.delete(document.id)

    assert repository.document is not None
    assert repository.document.status.value == "DELETING"
    assert storage.deleted is False

    cache.error = None
    await service.delete(document.id)

    assert repository.document is None
    assert storage.deleted is True
