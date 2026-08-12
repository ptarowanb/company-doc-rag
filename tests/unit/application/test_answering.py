from collections.abc import AsyncIterator
from uuid import UUID

import pytest

from company_doc_rag.application.answering import AnswerQuestion
from company_doc_rag.domain.answers import AnswerEventType
from company_doc_rag.domain.search import SearchHit


class 가짜_검색기:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits

    async def execute(self, question, document_ids=None) -> list[SearchHit]:
        return self.hits


class 가짜_생성기:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt = ""

    async def generate(self, prompt: str) -> str:
        self.calls += 1
        self.prompt = prompt
        return "연차는 15일입니다."

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.calls += 1
        self.prompt = prompt
        for token in ["연차는 ", "15일입니다."]:
            yield token


@pytest.mark.asyncio
async def test_근거가_없으면_LLM을_호출하지_않는다() -> None:
    generator = 가짜_생성기()
    answerer = AnswerQuestion(search=가짜_검색기([]), generator=generator)

    answer = await answerer.execute("없는 규정은?")

    assert answer.text == "관련 문서에서 답을 찾지 못했습니다."
    assert answer.sources == ()
    assert generator.calls == 0


@pytest.mark.asyncio
async def test_답변과_구조화된_페이지_출처를_반환한다() -> None:
    hit = SearchHit(
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        filename="휴가규정.pdf",
        content="입사 1년 이상 직원에게 연차 15일을 부여한다.",
        page_start=3,
        page_end=3,
        score=0.03,
        rerank_score=0.9,
    )
    generator = 가짜_생성기()
    answerer = AnswerQuestion(search=가짜_검색기([hit]), generator=generator)

    answer = await answerer.execute("연차는 며칠인가요?")

    assert answer.sources[0].filename == "휴가규정.pdf"
    assert answer.sources[0].page_start == 3
    assert "[출처 1] 휴가규정.pdf, p.3" in generator.prompt


@pytest.mark.asyncio
async def test_스트리밍_이벤트를_정해진_순서로_생성한다() -> None:
    hit = SearchHit(
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        filename="휴가규정.pdf",
        content="연차는 15일이다.",
        page_start=3,
        page_end=3,
        score=0.03,
        rerank_score=0.9,
    )
    answerer = AnswerQuestion(search=가짜_검색기([hit]), generator=가짜_생성기())

    events = [event async for event in answerer.stream("연차는?")]

    assert [event.type for event in events] == [
        AnswerEventType.METADATA,
        AnswerEventType.TOKEN,
        AnswerEventType.TOKEN,
        AnswerEventType.SOURCES,
        AnswerEventType.DONE,
    ]

