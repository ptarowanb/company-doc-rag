from typing import cast

from fastapi import Request, status
from fastapi.responses import JSONResponse

from company_doc_rag.domain.errors import (
    DocumentNotFoundError,
    DomainError,
    DuplicateDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

ERROR_STATUS = {
    UnsupportedFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    DuplicateDocumentError: status.HTTP_409_CONFLICT,
    DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
}


async def domain_error_handler(_request: Request, error: Exception) -> JSONResponse:
    """도메인 오류를 일관된 HTTP 오류 형식으로 변환한다."""

    domain_error = cast(DomainError, error)
    return JSONResponse(
        status_code=ERROR_STATUS.get(type(domain_error), status.HTTP_400_BAD_REQUEST),
        content={
            "error": {
                "code": domain_error.code,
                "message": str(domain_error),
            }
        },
    )

