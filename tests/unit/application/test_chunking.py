from collections.abc import Sequence

from company_doc_rag.application.chunking import TokenChunker
from company_doc_rag.domain.documents import PageText


class 단어_토크나이저:
    def __init__(self) -> None:
        self._단어별_ID: dict[str, int] = {}
        self._ID별_단어: dict[int, str] = {}

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for word in text.split():
            token_id = self._단어별_ID.setdefault(word, len(self._단어별_ID) + 1)
            self._ID별_단어[token_id] = word
            ids.append(token_id)
        return ids

    def decode(self, tokens: Sequence[int]) -> str:
        return " ".join(self._ID별_단어[token] for token in tokens)


def test_청크에_페이지_범위와_토큰_제한을_보존한다() -> None:
    pages = [
        PageText(page_number=1, text="하나 둘 셋 넷 다섯 여섯"),
        PageText(page_number=2, text="일곱 여덟 아홉 열 열하나 열둘"),
    ]

    chunks = TokenChunker(
        max_tokens=8,
        overlap_tokens=2,
        tokenizer=단어_토크나이저(),
    ).split(pages)

    assert [(chunk.page_start, chunk.page_end) for chunk in chunks] == [(1, 2), (2, 2)]
    assert all(chunk.token_count <= 8 for chunk in chunks)
    assert chunks[0].content.endswith("여덟")
    assert chunks[1].content.startswith("일곱 여덟")


def test_빈_페이지는_청크에서_제외한다() -> None:
    pages = [PageText(page_number=1, text="  \n"), PageText(page_number=2, text="내용 있음")]

    chunks = TokenChunker(tokenizer=단어_토크나이저()).split(pages)

    assert len(chunks) == 1
    assert chunks[0].page_start == 2
