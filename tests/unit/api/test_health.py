import httpx
import pytest

from company_doc_rag.main import create_app


@pytest.mark.asyncio
async def test_프로세스_생존_상태를_확인한다(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
