from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """질의응답 요청."""

    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] | None = None


class SourceResponse(BaseModel):
    """클라이언트에 반환할 출처."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_start: int
    page_end: int
    excerpt: str


class QueryResponse(BaseModel):
    """완성된 답변 응답."""

    answer: str
    sources: list[SourceResponse]

