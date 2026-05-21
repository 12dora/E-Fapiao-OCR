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
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.api.schemas import (
    CapabilitiesResponse,
    EngineStatus,
    ErrorResponse,
    HealthResponse,
    InvoiceData,
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

    try:
        data = parse_invoice(content, hint_type=hint_type, ocr_mode=ocr_mode)
    except InvalidInput as e:
        _raise(400, request_id, "invalid_input", str(e))
    except UnsupportedFormat as e:
        _raise(415, request_id, "unsupported_format", str(e))
    except RuleEngineUnhandled as e:
        _raise(
            422,
            request_id,
            "rule_unhandled",
            str(e),
            document_type=e.document_type,
            invoice_type=e.invoice_type,
            engine=_engine_status(
                ocr_mode,
                ocr_required=e.ocr_required,
                ocr_used=e.ocr_used,
            ),
        )
    except ParseFailed as e:
        _raise(422, request_id, "parse_failed", str(e))
    except UnsupportedDocumentType as e:
        _raise(
            501,
            request_id,
            "not_implemented",
            str(e) or "该格式暂未实装",
            document_type=e.document_type,
            invoice_type=e.invoice_type,
            engine=_engine_status(ocr_mode),
        )
    except NotImplementedError as e:
        _raise(
            501,
            request_id,
            "not_implemented",
            str(e) or "该格式暂未实装",
            engine=_engine_status(ocr_mode, ocr_required=True),
        )
    except Exception:
        logger.exception("internal_error request_id=%s", request_id)
        _raise(500, request_id, "internal_error", "服务内部错误")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    invoice_data = InvoiceData.model_validate(data)
    logger.info(
        "parsed request_id=%s format=%s type=%s elapsed_ms=%d",
        request_id,
        invoice_data.source.format,
        invoice_data.invoice_type,
        elapsed_ms,
    )
    return ParseResponse(
        request_id=request_id,
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


def _raise(
    status: int,
    request_id: str,
    code: str,
    message: str,
    *,
    document_type: str | None = None,
    invoice_type: str | None = None,
    engine: EngineStatus | None = None,
) -> None:
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


def _engine_status(
    ocr_mode: str,
    *,
    ocr_required: bool = False,
    ocr_used: bool = False,
    ocr_vendor: str | None = None,
) -> EngineStatus:
    return EngineStatus(
        rule_engine="attempted",
        ocr_mode=ocr_mode if ocr_mode in {"auto", "disabled", "required"} else "auto",
        ocr_enabled=settings.image_ocr_enabled,
        ocr_used=ocr_used,
        ocr_required=ocr_required,
        ocr_vendor=ocr_vendor,
    )
