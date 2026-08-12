import json
from collections.abc import AsyncIterator, Sequence
from typing import Annotated, Protocol, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette import EventSourceResponse, ServerSentEvent

from company_doc_rag.api.schemas import QueryRequest, QueryResponse, SourceResponse
from company_doc_rag.domain.answers import Answer, AnswerEvent, AnswerEventType

router = APIRouter(prefix="/api/v1/query", tags=["query"])


class _AnswerQuestion(Protocol):
    async def execute(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> Answer: ...

    def stream(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> AsyncIterator[AnswerEvent]: ...


def get_answer_question(request: Request) -> _AnswerQuestion:
    answerer = getattr(request.app.state, "answer_question", None)
    if answerer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="질의응답 서비스가 준비되지 않았습니다.",
        )
    return cast(_AnswerQuestion, answerer)


AnswererDependency = Annotated[_AnswerQuestion, Depends(get_answer_question)]


@router.post("", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    answerer: AnswererDependency,
) -> QueryResponse:
    answer = await answerer.execute(payload.question, payload.document_ids)
    return QueryResponse(
        answer=answer.text,
        sources=[SourceResponse.model_validate(source) for source in answer.sources],
    )


@router.post("/stream", response_class=EventSourceResponse)
async def query_stream(
    payload: QueryRequest,
    answerer: AnswererDependency,
) -> EventSourceResponse:
    async def events() -> AsyncIterator[ServerSentEvent]:
        try:
            async for event in answerer.stream(payload.question, payload.document_ids):
                yield ServerSentEvent(
                    event=event.type.value,
                    data=json.dumps(_event_data(event), ensure_ascii=False),
                )
        except Exception:
            yield ServerSentEvent(
                event=AnswerEventType.ERROR.value,
                data=json.dumps(
                    {"message": "답변 스트리밍 중 오류가 발생했습니다."},
                    ensure_ascii=False,
                ),
            )

    return EventSourceResponse(events())


def _event_data(event: AnswerEvent) -> dict[str, object]:
    if event.type is AnswerEventType.TOKEN:
        return {"text": event.text or ""}
    if event.type is AnswerEventType.SOURCES:
        return {
            "sources": [
                SourceResponse.model_validate(source).model_dump(mode="json")
                for source in event.sources
            ]
        }
    if event.type is AnswerEventType.METADATA:
        return dict(event.metadata or {})
    return {}
