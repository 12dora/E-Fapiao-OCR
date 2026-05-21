"""腾讯云通用票据识别 OCR vendor。

使用腾讯云 API 3.0 TC3-HMAC-SHA256 签名，不依赖官方 SDK。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.errors import ParseFailed
from app.ocr.base import OcrResult, OcrTextLine
from app.ocr.credentials import TencentOcrCredentials, get_tencent_ocr_credentials

SERVICE = "ocr"
ALGORITHM = "TC3-HMAC-SHA256"


@dataclass(frozen=True)
class _TencentConfig:
    secret_id: str
    secret_key: str
    token: str | None
    region: str
    endpoint: str
    action: str
    version: str
    timeout: float


class TencentOcrVendor:
    name = "tencent"

    def recognize(self, content: bytes) -> OcrResult:
        config = _load_config()
        payload = json.dumps(
            {"ImageBase64": base64.b64encode(content).decode("ascii")},
            separators=(",", ":"),
        )
        timestamp = int(time.time())
        headers = _build_headers(config, payload, timestamp)
        url = f"https://{config.endpoint}"

        try:
            with httpx.Client(timeout=config.timeout) as client:
                response = client.post(url, content=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as e:
            raise ParseFailed("腾讯云 OCR 服务调用失败") from e
        except ValueError as e:
            raise ParseFailed("腾讯云 OCR 服务响应不是合法 JSON") from e

        if body.get("Response", {}).get("Error"):
            message = body["Response"]["Error"].get("Message") or "腾讯云 OCR 返回错误"
            raise ParseFailed(message)

        return _parse_response(body)


def _load_config() -> _TencentConfig:
    context_credentials = get_tencent_ocr_credentials()
    file_credentials = _load_credentials_file(settings.tencent_credentials_file)
    secret_id = (
        (context_credentials.secret_id if context_credentials else None)
        or (file_credentials.secret_id if file_credentials else None)
        or settings.tencent_secret_id
    )
    secret_key = (
        (context_credentials.secret_key if context_credentials else None)
        or (file_credentials.secret_key if file_credentials else None)
        or settings.tencent_secret_key
    )
    token = (
        (context_credentials.token if context_credentials else None)
        or (file_credentials.token if file_credentials else None)
        or settings.tencent_token
        or None
    )
    region = (
        (context_credentials.region if context_credentials else None)
        or (file_credentials.region if file_credentials else None)
        or settings.tencent_region
    )

    if not secret_id or not secret_key:
        raise NotImplementedError(
            "腾讯云 OCR vendor 需要配置 SecretId/SecretKey，"
            "可用环境变量、凭据文件或 tencent_ocr_credentials() context 传入"
        )

    return _TencentConfig(
        secret_id=secret_id,
        secret_key=secret_key,
        token=token,
        region=region,
        endpoint=settings.tencent_ocr_endpoint,
        action=settings.tencent_ocr_action,
        version=settings.tencent_ocr_version,
        timeout=settings.tencent_ocr_timeout_seconds,
    )


def _load_credentials_file(path: str) -> TencentOcrCredentials | None:
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise NotImplementedError(f"无法读取腾讯云 OCR 凭据文件: {path}") from e
    except ValueError as e:
        raise NotImplementedError("腾讯云 OCR 凭据文件不是合法 JSON") from e

    secret_id = data.get("secret_id") or data.get("SecretId") or data.get("secretId")
    secret_key = data.get("secret_key") or data.get("SecretKey") or data.get("secretKey")
    token = data.get("token") or data.get("Token")
    region = data.get("region") or data.get("Region")
    if not secret_id or not secret_key:
        raise NotImplementedError("腾讯云 OCR 凭据文件缺少 secret_id/secret_key")
    return TencentOcrCredentials(
        secret_id=str(secret_id),
        secret_key=str(secret_key),
        token=str(token) if token else None,
        region=str(region) if region else None,
    )


def _build_headers(config: _TencentConfig, payload: str, timestamp: int) -> dict[str, str]:
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    canonical_headers = (
        f"content-type:application/json; charset=utf-8\nhost:{config.endpoint}\n"
    )
    signed_headers = "content-type;host"
    hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = (
        "POST\n"
        "/\n"
        "\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_request_payload}"
    )
    credential_scope = f"{date}/{SERVICE}/tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = (
        f"{ALGORITHM}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
    )

    secret_date = _sign(("TC3" + config.secret_key).encode("utf-8"), date)
    secret_service = _sign(secret_date, SERVICE)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    authorization = (
        f"{ALGORITHM} Credential={config.secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": config.endpoint,
        "X-TC-Action": config.action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": config.version,
        "X-TC-Region": config.region,
    }
    if config.token:
        headers["X-TC-Token"] = config.token
    return headers


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _parse_response(body: dict[str, Any]) -> OcrResult:
    maybe_response = body.get("Response")
    response = maybe_response if isinstance(maybe_response, dict) else body
    lines = _parse_items(response.get("MixedInvoiceItems"))
    if not lines:
        lines = _parse_items(response.get("SingleInvoiceInfos"))
    if not lines:
        text = response.get("Text") or response.get("OcrText")
        if isinstance(text, str):
            lines = [OcrTextLine(text=line.strip()) for line in text.splitlines()]
    if not lines:
        lines = _walk_text(response)

    return OcrResult(lines=[line for line in lines if line.text], vendor="tencent")


def _parse_items(items: Any) -> list[OcrTextLine]:
    if not isinstance(items, list):
        return []
    lines: list[OcrTextLine] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _item_to_text(item)
        if text:
            lines.append(OcrTextLine(text=text))
    return lines


def _item_to_text(item: dict[str, Any]) -> str | None:
    name = item.get("Name")
    value = item.get("Value")
    if isinstance(name, str) and isinstance(value, str) and name.strip() and value.strip():
        return f"{name.strip()}: {value.strip()}"

    direct_text = item.get("Text") or item.get("OcrText") or value or name
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    candidates: list[str] = []
    for key, value in item.items():
        if isinstance(value, str) and value.strip():
            candidates.append(f"{key}: {value.strip()}")
        elif isinstance(value, dict):
            nested = _item_to_text(value)
            if nested:
                candidates.append(nested)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    nested = _item_to_text(child)
                    if nested:
                        candidates.append(nested)
                elif isinstance(child, str) and child.strip():
                    candidates.append(f"{key}: {child.strip()}")
    return "\n".join(candidates) or None


def _walk_text(value: Any) -> list[OcrTextLine]:
    texts: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in {"text", "name", "value"} and isinstance(value, str):
                    if value.strip():
                        texts.append(value.strip())
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return [OcrTextLine(text=text) for text in texts]
