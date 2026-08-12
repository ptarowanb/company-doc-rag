from pathlib import Path

import pymupdf
import pytest

from company_doc_rag.domain.errors import EmptyDocumentError
from company_doc_rag.infrastructure.pdf_loader import PdfLoader


def PDF_파일을_만든다(path: Path, texts: list[str]) -> None:
    document = pymupdf.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_PDF의_페이지별_텍스트를_읽는다(tmp_path: Path) -> None:
    path = tmp_path / "guide.pdf"
    PDF_파일을_만든다(path, ["first page", "second page"])

    pages = PdfLoader().load(path)

    assert [page.page_number for page in pages] == [1, 2]
    assert [page.text for page in pages] == ["first page", "second page"]


def test_텍스트가_없는_PDF를_거부한다(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    PDF_파일을_만든다(path, [""])

    with pytest.raises(EmptyDocumentError):
        PdfLoader().load(path)
