from pathlib import Path
from typing import BinaryIO
from uuid import uuid4


class LocalFileStorage:
    """서버가 생성한 키로 원본 파일을 로컬 디스크에 저장한다."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes) -> str:
        key = f"{uuid4().hex}.pdf"
        self.path_for(key).write_bytes(content)
        return key

    def path_for(self, key: str) -> Path:
        if not key or Path(key).name != key:
            raise ValueError("올바르지 않은 저장 키입니다.")
        path = (self._root / key).resolve()
        if path.parent != self._root:
            raise ValueError("올바르지 않은 저장 키입니다.")
        return path

    def open(self, key: str) -> BinaryIO:
        return self.path_for(key).open("rb")

    def delete(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)

