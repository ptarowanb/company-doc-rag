from pathlib import Path

import pytest

from company_doc_rag.infrastructure.file_storage import LocalFileStorage


def test_원본을_UUID_키로_저장하고_삭제한다(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    key = storage.save(b"pdf-content")

    assert key.endswith(".pdf")
    assert storage.path_for(key).read_bytes() == b"pdf-content"
    storage.delete(key)
    assert not storage.path_for(key).exists()


def test_상위_경로로_벗어나는_키를_거부한다(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(ValueError, match="올바르지 않은 저장 키"):
        storage.path_for("../secret.pdf")

