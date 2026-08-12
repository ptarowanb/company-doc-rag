from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Source:
    """답변 근거로 사용한 문서 위치."""

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_start: int
    page_end: int
    excerpt: str


@dataclass(frozen=True, slots=True)
class Answer:
    """완성된 답변과 구조화된 출처."""

    text: str
    sources: tuple[Source, ...]


class AnswerEventType(StrEnum):
    """SSE 스트림에서 사용하는 이벤트 종류."""

    METADATA = "metadata"
    TOKEN = "token"
    SOURCES = "sources"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AnswerEvent:
    """클라이언트로 전송할 답변 스트림 이벤트."""

    type: AnswerEventType
    text: str | None = None
    sources: tuple[Source, ...] = ()
    metadata: dict[str, int] | None = None

