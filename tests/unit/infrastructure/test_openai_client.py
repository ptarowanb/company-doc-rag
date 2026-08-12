from dataclasses import dataclass

import pytest

from company_doc_rag.infrastructure.openai_client import OpenAIEmbedder


@dataclass
class 가짜_임베딩_항목:
    embedding: list[float]


@dataclass
class 가짜_응답:
    data: list[가짜_임베딩_항목]


class 가짜_임베딩_API:
    def __init__(self) -> None:
        self.inputs: list[list[str]] = []

    async def create(self, *, input, model, dimensions):
        self.inputs.append(list(input))
        return 가짜_응답([가짜_임베딩_항목([float(len(text))]) for text in input])


class 가짜_OpenAI:
    def __init__(self) -> None:
        self.embeddings = 가짜_임베딩_API()


@pytest.mark.asyncio
async def test_임베딩을_설정한_배치_크기로_나눈다() -> None:
    client = 가짜_OpenAI()
    embedder = OpenAIEmbedder(
        client=client,
        model="embedding-test",
        dimensions=1,
        batch_size=2,
    )

    embeddings = await embedder.embed(["가", "나다", "라마바"])

    assert client.embeddings.inputs == [["가", "나다"], ["라마바"]]
    assert embeddings == [[1.0], [2.0], [3.0]]

