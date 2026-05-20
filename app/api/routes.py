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
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app import __version__
from app.api.schemas import (
    CapabilitiesResponse,
    ErrorResponse,
    HealthResponse,
    InvoiceData,
    ParseResponse,
)
from app.config import settings
from app.errors import InvalidInput, ParseFailed, UnsupportedFormat
from app.sdk import parse_invoice

router = APIRouter()
logger = logging.getLogger("efapiao")


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if not settings.auth_enabled:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "X-API-Key 缺失或不正确"})


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> dict:
    return {
        "version": __version__,
        "formats": {"pdf": "supported", "ofd": "not_implemented", "image": "not_implemented"},
        "invoice_types": ["digital_general", "digital_special", "rail_12306"],
    }


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
    file: Optional[UploadFile] = File(default=None),
    hint_type: Optional[str] = Form(default="auto"),
) -> ParseResponse:
    request_id = uuid.uuid4().hex
    start = time.perf_counter()

    if file is None:
        _raise(400, request_id, "invalid_input", "缺少 file 字段")

    content = await file.read()
    if not content:
        _raise(400, request_id, "invalid_input", "文件内容为空")
    if len(content) > settings.max_file_bytes:
        _raise(400, request_id, "invalid_input", f"文件超过上限 {settings.max_file_bytes} 字节")

    try:
        data = parse_invoice(content, hint_type=hint_type)
    except InvalidInput as e:
        _raise(400, request_id, "invalid_input", str(e))
    except UnsupportedFormat as e:
        _raise(415, request_id, "unsupported_format", str(e))
    except ParseFailed as e:
        _raise(422, request_id, "parse_failed", str(e))
    except NotImplementedError as e:
        _raise(501, request_id, "not_implemented", str(e) or "该格式暂未实装")
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
        invoice_type=invoice_data.invoice_type,
        data=invoice_data,
        elapsed_ms=elapsed_ms,
    )


def _raise(status: int, request_id: str, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status,
        detail={"request_id": request_id, "status": "error", "code": code, "message": message},
    )
