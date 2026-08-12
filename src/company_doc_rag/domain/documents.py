from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class DocumentStatus(StrEnum):
    """문서 수집 처리 상태."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


@dataclass(frozen=True, slots=True)
class PageText:
    """PDF 한 페이지에서 추출한 텍스트."""

    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """저장 전 문서 청크와 출처 메타데이터."""

    index: int
    content: str
    page_start: int
    page_end: int
    token_count: int


@dataclass(frozen=True, slots=True)
class StoredChunk:
    """저장된 청크와 출처 메타데이터."""

    id: UUID
    document_id: UUID
    index: int
    content: str
    page_start: int
    page_end: int
    token_count: int


@dataclass(frozen=True, slots=True)
class Document:
    """수집 대상 문서."""

    filename: str
    sha256: str
    storage_key: str
    id: UUID = field(default_factory=uuid4)
    status: DocumentStatus = DocumentStatus.PENDING
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
