from uuid import uuid4

import httpx
import pytest

from company_doc_rag.domain.documents import Document
from company_doc_rag.main import create_app


class 가짜_문서_서비스:
    def __init__(self) -> None:
        self.document = Document(
            id=uuid4(),
            filename="guide.pdf",
            sha256="a" * 64,
            storage_key="id.pdf",
        )

    async def upload(self, filename, content_type, content) -> Document:
        from company_doc_rag.domain.errors import UnsupportedFileTypeError

        if content_type != "application/pdf":
            raise UnsupportedFileTypeError("PDF 파일만 업로드할 수 있습니다.")
        return self.document

    async def list(self):
        return [self.document]

    async def get(self, document_id):
        return self.document

    async def delete(self, document_id):
        return None


@pytest.mark.asyncio
async def test_PDF를_업로드하고_처리_대기_상태를_반환한다(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app(document_service=가짜_문서_서비스())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("guide.pdf", b"%PDF-content", "application/pdf")},
        )

    assert response.status_code == 202
    assert response.json()["filename"] == "guide.pdf"
    assert response.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_PDF가_아닌_파일을_구조화된_오류로_거부한다(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app(document_service=가짜_문서_서비스())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("x.txt", b"x", "text/plain")},
        )

    assert response.status_code == 415
    assert response.json() == {
        "error": {
            "code": "UNSUPPORTED_FILE_TYPE",
            "message": "PDF 파일만 업로드할 수 있습니다.",
        }
    }

