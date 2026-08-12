from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from company_doc_rag.domain.documents import PageText


class Tokenizer(Protocol):
    """문자열과 토큰 ID 사이를 변환한다."""

    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: Sequence[int]) -> str: ...


class DocumentLoader(Protocol):
    """파일에서 페이지별 텍스트를 읽는다."""

    def load(self, path: Path) -> list[PageText]: ...


class Embedder(Protocol):
    """문자열 배치를 벡터로 변환한다."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

