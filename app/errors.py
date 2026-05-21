"""项目内自定义异常 —— 由路由层 / CLI 统一映射到 HTTP code 与退出码。

映射关系（DESIGN.md §5.4）：
    InvalidInput          → 400 invalid_input         | CLI exit 2
    UnsupportedFormat     → 415 unsupported_format    | CLI exit 3
    ParseFailed           → 422 parse_failed          | CLI exit 4
    NotImplementedError   → 501 not_implemented       | CLI exit 5
    其它未捕获              → 500 internal_error        | CLI exit 1
"""


class EfapiaoError(Exception):
    """所有业务异常的基类。"""


class InvalidInput(EfapiaoError):
    pass


class UnsupportedFormat(EfapiaoError):
    pass


class ParseFailed(EfapiaoError):
    pass


class RuleEngineUnhandled(ParseFailed):
    def __init__(
        self,
        message: str,
        *,
        file_format: str | None = None,
        document_type: str | None = None,
        invoice_type: str | None = None,
        ocr_required: bool = False,
        ocr_used: bool = False,
    ) -> None:
        super().__init__(message)
        self.file_format = file_format
        self.document_type = document_type
        self.invoice_type = invoice_type
        self.ocr_required = ocr_required
        self.ocr_used = ocr_used


class UnsupportedDocumentType(NotImplementedError):
    def __init__(
        self,
        message: str,
        *,
        document_type: str,
        invoice_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.document_type = document_type
        self.invoice_type = invoice_type
