from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchHit:
    """검색 점수와 출처 정보를 함께 담은 청크."""

    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    page_start: int
    page_end: int
    score: float
    rerank_score: float | None = None

