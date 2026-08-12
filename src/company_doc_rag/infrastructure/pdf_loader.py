from pathlib import Path

import pymupdf

from company_doc_rag.domain.documents import PageText
from company_doc_rag.domain.errors import EmptyDocumentError, EncryptedPdfError, PdfReadError


class PdfLoader:
    """PyMuPDF로 텍스트 PDF를 페이지별로 읽는다."""

    def load(self, path: Path) -> list[PageText]:
        try:
            with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
                if document.needs_pass:
                    raise EncryptedPdfError("암호화된 PDF는 지원하지 않습니다.")
                pages = [
                    PageText(page_number=index + 1, text=page.get_text("text").strip())
                    for index, page in enumerate(document)
                ]
        except (EmptyDocumentError, EncryptedPdfError):
            raise
        except (OSError, RuntimeError, ValueError) as error:
            raise PdfReadError("PDF를 읽을 수 없습니다.") from error

        if not any(page.text for page in pages):
            raise EmptyDocumentError("PDF에서 텍스트를 찾지 못했습니다.")
        return pages
