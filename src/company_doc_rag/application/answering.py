from collections.abc import AsyncIterator, Sequence
from typing import Protocol
from uuid import UUID

from company_doc_rag.domain.answers import Answer, AnswerEvent, AnswerEventType, Source
from company_doc_rag.domain.observability import NoOpTracer, Tracer, text_hash
from company_doc_rag.domain.search import SearchHit

NO_EVIDENCE_ANSWER = "관련 문서에서 답을 찾지 못했습니다."


class _Search(Protocol):
    async def execute(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[SearchHit]: ...


class AnswerGenerator(Protocol):
    """구성된 근거 프롬프트로 답변을 생성한다."""

    async def generate(self, prompt: str) -> str: ...

    def stream(self, prompt: str) -> AsyncIterator[str]: ...


class AnswerQuestion:
    """검색 근거를 답변과 출처로 변환한다."""

    def __init__(
        self,
        search: _Search,
        generator: AnswerGenerator,
        min_relevance_score: float = 0.0,
        tracer: Tracer | None = None,
    ) -> None:
        self._search = search
        self._generator = generator
        self._min_relevance_score = min_relevance_score
        self._tracer = tracer or NoOpTracer()

    async def execute(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> Answer:
        with self._tracer.trace(
            "query.answer",
            {"question_hash": text_hash(question)},
        ) as span:
            hits = self._filter_hits(await self._search.execute(question, document_ids))
            if not hits:
                answer = Answer(text=NO_EVIDENCE_ANSWER, sources=())
            else:
                text = await self._generator.generate(self._build_prompt(question, hits))
                answer = Answer(text=text, sources=self._to_sources(hits))
            span.set_output({"source_count": len(answer.sources)})
            return answer

    async def stream(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> AsyncIterator[AnswerEvent]:
        with self._tracer.trace(
            "query.answer.stream",
            {"question_hash": text_hash(question)},
        ) as span:
            hits = self._filter_hits(await self._search.execute(question, document_ids))
            sources = self._to_sources(hits)
            yield AnswerEvent(
                type=AnswerEventType.METADATA,
                metadata={"source_count": len(sources)},
            )
            if not hits:
                yield AnswerEvent(type=AnswerEventType.TOKEN, text=NO_EVIDENCE_ANSWER)
            else:
                async for token in self._generator.stream(self._build_prompt(question, hits)):
                    yield AnswerEvent(type=AnswerEventType.TOKEN, text=token)
            yield AnswerEvent(type=AnswerEventType.SOURCES, sources=sources)
            yield AnswerEvent(type=AnswerEventType.DONE)
            span.set_output({"source_count": len(sources)})

    def _filter_hits(self, hits: Sequence[SearchHit]) -> list[SearchHit]:
        return [
            hit
            for hit in hits
            if (hit.rerank_score if hit.rerank_score is not None else hit.score)
            >= self._min_relevance_score
        ]

    @staticmethod
    def _to_sources(hits: Sequence[SearchHit]) -> tuple[Source, ...]:
        return tuple(
            Source(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                filename=hit.filename,
                page_start=hit.page_start,
                page_end=hit.page_end,
                excerpt=hit.content[:300],
            )
            for hit in hits
        )

    @staticmethod
    def _build_prompt(question: str, hits: Sequence[SearchHit]) -> str:
        contexts: list[str] = []
        for index, hit in enumerate(hits, start=1):
            page = (
                f"p.{hit.page_start}"
                if hit.page_start == hit.page_end
                else f"pp.{hit.page_start}-{hit.page_end}"
            )
            contexts.append(f"[출처 {index}] {hit.filename}, {page}\n{hit.content}")
        joined_context = "\n\n".join(contexts)
        return (
            "아래 문서 근거만 사용해 한국어로 답하세요. 근거가 부족하면 모른다고 말하고, "
            "주요 문장 끝에 [출처 N]을 표시하세요.\n\n"
            f"질문: {question}\n\n문서 근거:\n{joined_context}"
        )
