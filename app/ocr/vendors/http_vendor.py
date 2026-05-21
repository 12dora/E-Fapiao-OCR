"""第三方 HTTP OCR vendor。

约定响应 JSON:
  - {"text": "..."}；或
  - {"lines": [{"text": "...", "score": 0.99, "bbox": [[x, y], ...]}]}
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.core.url_security import validate_public_http_url
from app.errors import ParseFailed
from app.ocr.base import OcrResult, OcrTextLine


class HttpOcrVendor:
    name = "http"

    def __init__(self) -> None:
        if not settings.ocr_http_url:
            raise NotImplementedError("HTTP OCR vendor 需要配置 EFAPIAO_OCR_HTTP_URL")
        self._url = validate_public_http_url(
            settings.ocr_http_url,
            allow_http=settings.ocr_http_allow_http,
        )
        self._timeout = settings.ocr_http_timeout_seconds
        self._headers = _parse_headers(settings.ocr_http_headers)

    def recognize(self, content: bytes) -> OcrResult:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self._url,
                    files={"file": ("invoice-image", content, "application/octet-stream")},
                    headers=self._headers,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as e:
            raise ParseFailed("第三方 OCR 服务调用失败") from e
        except ValueError as e:
            raise ParseFailed("第三方 OCR 服务响应不是合法 JSON") from e

        return _parse_payload(payload)


def _parse_headers(raw: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for part in raw.split(";"):
        if not part.strip():
            continue
        key, sep, value = part.partition(":")
        if sep and key.strip():
            headers[key.strip()] = value.strip()
    return headers


def _parse_payload(payload: dict[str, Any]) -> OcrResult:
    if isinstance(payload.get("text"), str):
        lines = [OcrTextLine(text=line.strip()) for line in payload["text"].splitlines()]
        return OcrResult(lines=[line for line in lines if line.text], vendor="http")

    if isinstance(payload.get("lines"), list):
        lines = [
            OcrTextLine(
                text=str(item.get("text") or "").strip(),
                score=item.get("score"),
                bbox=item.get("bbox"),
            )
            for item in payload["lines"]
            if isinstance(item, dict)
        ]
        return OcrResult(lines=[line for line in lines if line.text], vendor="http")

    raise ParseFailed("第三方 OCR 服务响应缺少 text 或 lines")
