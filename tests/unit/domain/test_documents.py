from company_doc_rag.domain.documents import Document


def test_문서마다_서로_다른_ID를_생성한다() -> None:
    first = Document(filename="a.pdf", sha256="a" * 64, storage_key="a.pdf")
    second = Document(filename="b.pdf", sha256="b" * 64, storage_key="b.pdf")

    assert first.id != second.id

