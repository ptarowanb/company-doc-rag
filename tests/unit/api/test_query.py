import json
from collections.abc import AsyncIterator

import httpx
import pytest

from company_doc_rag.domain.answers import Answer, AnswerEvent, AnswerEventType
from company_doc_rag.main import create_app


class 가짜_답변기:
    async def execute(self, question, document_ids=None) -> Answer:
        return Answer(text="답변", sources=())

    async def stream(self, question, document_ids=None) -> AsyncIterator[AnswerEvent]:
        yield AnswerEvent(type=AnswerEventType.METADATA, metadata={"source_count": 0})
        yield AnswerEvent(type=AnswerEventType.TOKEN, text="답변")
        yield AnswerEvent(type=AnswerEventType.SOURCES, sources=())
        yield AnswerEvent(type=AnswerEventType.DONE)


@pytest.mark.asyncio
async def test_일반_질의응답_API를_호출한다(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    transport = httpx.ASGITransport(app=create_app(answer_question=가짜_답변기()))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/query", json={"question": "휴가 규정?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "답변", "sources": []}


@pytest.mark.asyncio
async def test_SSE_이벤트_순서를_보존한다(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    transport = httpx.ASGITransport(app=create_app(answer_question=가짜_답변기()))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/query/stream", json={"question": "휴가 규정?"})

    event_names = [
        line.removeprefix("event: ")
        for line in response.text.splitlines()
        if line.startswith("event: ")
    ]
    data_lines = [line for line in response.text.splitlines() if line.startswith("data: ")]
    assert response.status_code == 200
    assert event_names == ["metadata", "token", "sources", "done"]
    assert json.loads(data_lines[1].removeprefix("data: ")) == {"text": "답변"}

