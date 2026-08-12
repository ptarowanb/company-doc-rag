import re
from collections.abc import Sequence

import tiktoken

from company_doc_rag.domain.documents import ChunkDraft, PageText
from company_doc_rag.domain.ports import Tokenizer


class TiktokenTokenizer:
    """OpenAI 계열 모델과 호환되는 토큰 변환기."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = tiktoken.get_encoding(encoding_name)

    def encode(self, text: str) -> list[int]:
        return self._encoding.encode(text)

    def decode(self, tokens: Sequence[int]) -> str:
        return self._encoding.decode(list(tokens))


class TokenChunker:
    """페이지 범위를 보존하며 문서를 겹치는 토큰 구간으로 분리한다."""

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 80,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens는 1 이상이어야 합니다.")
        if overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens는 0 이상 max_tokens 미만이어야 합니다.")
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens
        self._tokenizer = tokenizer or TiktokenTokenizer()

    def split(self, pages: Sequence[PageText]) -> list[ChunkDraft]:
        token_pages: list[tuple[int, int]] = []
        for page in pages:
            normalized = re.sub(r"\s+", " ", page.text).strip()
            if not normalized:
                continue
            if token_pages:
                normalized = f" {normalized}"
            token_pages.extend(
                (token, page.page_number) for token in self._tokenizer.encode(normalized)
            )

        chunks: list[ChunkDraft] = []
        step = self._max_tokens - self._overlap_tokens
        for start in range(0, len(token_pages), step):
            window = token_pages[start : start + self._max_tokens]
            if not window:
                break
            tokens = [token for token, _ in window]
            page_numbers = [page_number for _, page_number in window]
            chunks.append(
                ChunkDraft(
                    index=len(chunks),
                    content=self._tokenizer.decode(tokens).strip(),
                    page_start=min(page_numbers),
                    page_end=max(page_numbers),
                    token_count=len(tokens),
                )
            )
            if start + self._max_tokens >= len(token_pages):
                break
        return chunks
