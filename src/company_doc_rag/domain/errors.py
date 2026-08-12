class DomainError(Exception):
    """클라이언트에 안전하게 노출할 수 있는 도메인 오류."""

    code = "DOMAIN_ERROR"


class EmptyDocumentError(DomainError):
    """추출 가능한 텍스트가 없는 문서 오류."""

    code = "EMPTY_DOCUMENT"


class EncryptedPdfError(DomainError):
    """암호 해제가 필요한 PDF 오류."""

    code = "ENCRYPTED_PDF"


class PdfReadError(DomainError):
    """구조가 손상됐거나 읽을 수 없는 PDF 오류."""

    code = "PDF_READ_ERROR"


class UnsupportedFileTypeError(DomainError):
    """지원하지 않는 파일 형식 오류."""

    code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(DomainError):
    """업로드 제한을 초과한 파일 오류."""

    code = "FILE_TOO_LARGE"


class DuplicateDocumentError(DomainError):
    """동일한 해시의 문서가 이미 존재하는 오류."""

    code = "DUPLICATE_DOCUMENT"


class DocumentNotFoundError(DomainError):
    """문서 식별자를 찾지 못한 오류."""

    code = "DOCUMENT_NOT_FOUND"


class TransientEmbeddingError(DomainError):
    """재시도 가능한 임베딩 공급자 오류."""

    code = "TRANSIENT_EMBEDDING_ERROR"
