from pathlib import Path
from uuid import UUID

import pytest

from company_doc_rag.application.documents import DocumentService
from company_doc_rag.domain.documents import Document
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

    async def delete(self, document_id: UUID) -> None:
        self.document = None


class 가짜_파일_저장소:
    def __init__(self) -> None:
        self.content = b""
        self.deleted = False

    def save(self, content: bytes) -> str:
        self.content = content
        return "id.pdf"

    def delete(self, key: str) -> None:
        self.deleted = True

    def path_for(self, key: str) -> Path:
        return Path(key)


class 가짜_큐:
    def __init__(self) -> None:
        self.document_id: UUID | None = None

    def enqueue(self, document_id: UUID) -> None:
        self.document_id = document_id


class 가짜_캐시:
    def __init__(self) -> None:
        self.generation = 0

    async def bump_generation(self) -> int:
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
