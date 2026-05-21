"""HTTP 路由层 —— DESIGN.md §5 端点。

每个端点都是 sdk.parse_invoice 之上的薄壳，仅负责：
  - 入参校验（文件大小、格式提示）
  - 调用 sdk
  - 异常 → §5.4 HTTP 状态码映射
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any, NoReturn, cast

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.api.schemas import (
    BatchParseItem,
    BatchParseResponse,
    CapabilitiesResponse,
    DocumentType,
    EngineStatus,
    ErrorCode,
    ErrorResponse,
    HealthResponse,
    InvoiceData,
    InvoiceType,
    OcrMode,
    ParseResponse,
)
from app.config import settings
from app.core.capabilities import build_capabilities
from app.errors import (
    InvalidInput,
    ParseFailed,
    RuleEngineUnhandled,
    UnsupportedDocumentType,
    UnsupportedFormat,
)
from app.sdk import parse_invoice

router = APIRouter()
logger = logging.getLogger("efapiao")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.auth_enabled:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "X-API-Key 缺失或不正确"},
        )


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> dict:
    return build_capabilities(settings)


@router.post(
    "/invoices/parse",
    response_model=ParseResponse,
    responses={
        400: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        501: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_api_key)],
)
async def parse(
    file: Annotated[UploadFile | None, File()] = None,
    hint_type: Annotated[str | None, Form()] = "auto",
    ocr_mode: Annotated[str, Form()] = "auto",
) -> ParseResponse:
    request_id = uuid.uuid4().hex
    start = time.perf_counter()

    if file is None:
        _raise(400, request_id, "invalid_input", "缺少 file 字段")

    content = await _read_upload(file, request_id)
    item = _parse_content(
        request_id=request_id,
        content=content,
        filename=file.filename,
        hint_type=hint_type,
        ocr_mode=ocr_mode,
        start=start,
    )
    if item.status == "error":
        _raise(
            _http_status_for_error(item.code),
            request_id,
            item.code or "internal_error",
            item.message or "服务内部错误",
            document_type=item.document_type,
            invoice_type=item.invoice_type,
            engine=item.engine,
        )

    assert item.data is not None
    assert item.format is not None
    assert item.document_type is not None
    assert item.invoice_type is not None
    return ParseResponse(
        request_id=request_id,
        status="ok",
        format=item.format,
        document_type=item.document_type,
        invoice_type=item.invoice_type,
        data=item.data,
        engine=item.engine,
        elapsed_ms=item.elapsed_ms,
    )


@router.post(
    "/invoices/parse-batch",
    response_model=BatchParseResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_api_key)],
)
async def parse_batch(
    files: Annotated[list[UploadFile] | None, File()] = None,
    hint_type: Annotated[str | None, Form()] = "auto",
    ocr_mode: Annotated[str, Form()] = "auto",
) -> BatchParseResponse:
    request_id = uuid.uuid4().hex
    start = time.perf_counter()

    if not files:
        _raise(400, request_id, "invalid_input", "缺少 files 字段")

    items: list[BatchParseItem] = []
    for index, file in enumerate(files):
        item_start = time.perf_counter()
        try:
            content = await _read_upload(file, request_id)
        except HTTPException as e:
            detail: dict[str, Any] = e.detail if isinstance(e.detail, dict) else {}
            items.append(
                BatchParseItem(
                    index=index,
                    filename=file.filename,
                    status="error",
                    code=cast(ErrorCode, detail.get("code") or "invalid_input"),
                    message=detail.get("message") or "文件读取失败",
                    engine=_engine_status(ocr_mode),
                    elapsed_ms=int((time.perf_counter() - item_start) * 1000),
                )
            )
            continue

        items.append(
            _parse_content(
                request_id=request_id,
                content=content,
                filename=file.filename,
                hint_type=hint_type,
                ocr_mode=ocr_mode,
                index=index,
                start=item_start,
            )
        )

    succeeded = sum(1 for item in items if item.status == "ok")
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return BatchParseResponse(
        request_id=request_id,
        status="ok",
        total=len(items),
        succeeded=succeeded,
        failed=len(items) - succeeded,
        items=items,
        elapsed_ms=elapsed_ms,
    )


async def _read_upload(file: UploadFile, request_id: str) -> bytes:
    content = await file.read()
    if not content:
        _raise(400, request_id, "invalid_input", "文件内容为空")
    if len(content) > settings.max_file_bytes:
        _raise(
            400,
            request_id,
            "invalid_input",
            f"文件超过上限 {settings.max_file_bytes} 字节",
        )
    return content


def _parse_content(
    *,
    request_id: str,
    content: bytes,
    filename: str | None,
    hint_type: str | None,
    ocr_mode: str,
    start: float,
    index: int = 0,
) -> BatchParseItem:
    try:
        data = parse_invoice(content, hint_type=hint_type, ocr_mode=ocr_mode)
    except InvalidInput as e:
        return _error_item(index, filename, "invalid_input", str(e), ocr_mode, start)
    except UnsupportedFormat as e:
        return _error_item(index, filename, "unsupported_format", str(e), ocr_mode, start)
    except RuleEngineUnhandled as e:
        return _error_item(
            index,
            filename,
            "rule_unhandled",
            str(e),
            ocr_mode,
            start,
            document_type=cast(DocumentType | None, e.document_type),
            invoice_type=cast(InvoiceType | None, e.invoice_type),
            engine=_engine_status(
                ocr_mode,
                ocr_required=e.ocr_required,
                ocr_used=e.ocr_used,
                ocr_vendor=_configured_ocr_vendor(),
            ),
        )
    except ParseFailed as e:
        return _error_item(index, filename, "parse_failed", str(e), ocr_mode, start)
    except UnsupportedDocumentType as e:
        return _error_item(
            index,
            filename,
            "not_implemented",
            str(e) or "该格式暂未实装",
            ocr_mode,
            start,
            document_type=cast(DocumentType, e.document_type),
            invoice_type=cast(InvoiceType | None, e.invoice_type),
            engine=_engine_status(ocr_mode),
        )
    except NotImplementedError as e:
        return _error_item(
            index,
            filename,
            "not_implemented",
            str(e) or "该格式暂未实装",
            ocr_mode,
            start,
            engine=_engine_status(ocr_mode, ocr_required=True),
        )
    except Exception:
        logger.exception("internal_error request_id=%s", request_id)
        return _error_item(index, filename, "internal_error", "服务内部错误", ocr_mode, start)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    invoice_data = InvoiceData.model_validate(data)
    logger.info(
        "parsed request_id=%s format=%s type=%s elapsed_ms=%d",
        request_id,
        invoice_data.source.format,
        invoice_data.invoice_type,
        elapsed_ms,
    )
    return BatchParseItem(
        index=index,
        filename=filename,
        status="ok",
        format=invoice_data.source.format,
        document_type=invoice_data.document_type,
        invoice_type=invoice_data.invoice_type,
        data=invoice_data,
        engine=_engine_status(
            ocr_mode,
            ocr_required=False,
            ocr_used=invoice_data.source.extracted_by == "ocr",
            ocr_vendor=invoice_data.source.ocr_vendor,
        ),
        elapsed_ms=elapsed_ms,
    )


def _error_item(
    index: int,
    filename: str | None,
    code: ErrorCode,
    message: str,
    ocr_mode: str,
    start: float,
    *,
    document_type: DocumentType | None = None,
    invoice_type: InvoiceType | None = None,
    engine: EngineStatus | None = None,
) -> BatchParseItem:
    return BatchParseItem(
        index=index,
        filename=filename,
        status="error",
        code=code,
        message=message,
        document_type=document_type,
        invoice_type=invoice_type,
        engine=engine or _engine_status(ocr_mode),
        elapsed_ms=int((time.perf_counter() - start) * 1000),
    )


def _raise(
    status: int,
    request_id: str,
    code: ErrorCode,
    message: str,
    *,
    document_type: DocumentType | None = None,
    invoice_type: InvoiceType | None = None,
    engine: EngineStatus | None = None,
) -> NoReturn:
    raise HTTPException(
        status_code=status,
        detail={
            "request_id": request_id,
            "status": "error",
            "code": code,
            "message": message,
            "document_type": document_type,
            "invoice_type": invoice_type,
            "engine": engine.model_dump() if engine else None,
        },
    )


def _http_status_for_error(code: str | None) -> int:
    if code == "invalid_input":
        return 400
    if code == "unsupported_format":
        return 415
    if code in {"rule_unhandled", "parse_failed"}:
        return 422
    if code == "not_implemented":
        return 501
    return 500


def _engine_status(
    ocr_mode: str,
    *,
    ocr_required: bool = False,
    ocr_used: bool = False,
    ocr_vendor: str | None = None,
) -> EngineStatus:
    mode: OcrMode = (
        cast(OcrMode, ocr_mode) if ocr_mode in {"auto", "disabled", "required"} else "auto"
    )
    return EngineStatus(
        rule_engine="attempted",
        ocr_mode=mode,
        ocr_enabled=settings.image_ocr_enabled,
        ocr_used=ocr_used,
        ocr_required=ocr_required,
        ocr_vendor=ocr_vendor,
    )


def _configured_ocr_vendor() -> str | None:
    vendor = settings.ocr_vendor.lower()
    if vendor in {"", "none", "disabled"}:
        return None
    return settings.ocr_vendor
