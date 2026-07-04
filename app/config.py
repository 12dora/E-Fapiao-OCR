"""运行时配置 —— 仅从环境变量读取，不引入配置中心。

字段读取集中在 ``Settings.from_env``：这样每次 ``Settings.from_env()`` 都会反映
当前 ``os.environ``（便于测试与运行时重配），且单个环境变量取值错误不会在 import
阶段以裸 traceback 直接拖垮所有入口（CLI / FastAPI / SDK）。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from app.ocr_model_profiles import (
    DEFAULT_CNOCR_MODEL_PROFILE,
    resolve_cnocr_model_profile,
)

logger = logging.getLogger("efapiao")

_DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024


def _env_str(name: str, default: str = "", *fallbacks: str) -> str:
    for key in (name, *fallbacks):
        value = os.getenv(key)
        if value:
            return value
    return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 不是合法整数，回退到默认值 %s", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 不是合法数值，回退到默认值 %s", name, raw, default)
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() == "true"


@dataclass(frozen=True)
class Settings:
    # 鉴权：API Key 留空 → 关闭鉴权（本机集成场景的默认选择）。
    # 配上任意非空值 → 所有 /v1/invoices/* 必须携带 Header X-API-Key 且匹配。
    api_key: str = ""

    # 上传文件大小硬上限（字节），默认 10 MB
    max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES

    # 单个请求体的硬上限（字节）。用于在解析 multipart 之前，凭 Content-Length
    # 直接拒绝超大请求，避免超大上传把整机内存/磁盘顶爆。批量接口需要容纳多文件，
    # 因此默认显著大于单文件上限。
    max_request_bytes: int = _DEFAULT_MAX_FILE_BYTES * 4

    # Webhook 透传超时（秒）
    forward_timeout_seconds: float = 5.0

    # 是否允许 HTTP 透传地址（生产保持 false，强制 HTTPS）
    forward_allow_http: bool = False

    # HTTP 服务监听地址（仅本机集成时建议 127.0.0.1，对外服务时改 0.0.0.0）
    host: str = "127.0.0.1"
    port: int = 8000

    # OCR vendor：none（默认关闭）/ cnocr / http / tencent
    ocr_vendor: str = "none"

    # CnOCR vendor：默认使用纯 CPU 友好的 ONNX 小模型组合
    cnocr_model_profile: str = DEFAULT_CNOCR_MODEL_PROFILE
    cnocr_det_model_name: str = ""
    cnocr_rec_model_name: str = ""
    cnocr_det_model_backend: str = "onnx"
    cnocr_rec_model_backend: str = "onnx"

    # HTTP OCR vendor：第三方服务地址与透传 header，header 格式为 "A:B;C:D"
    ocr_http_url: str = ""
    ocr_http_headers: str = ""
    ocr_http_timeout_seconds: float = 10.0
    ocr_http_allow_http: bool = False

    # 腾讯云 OCR vendor。优先级：源码 context override > 凭据文件 > 环境变量。
    # 同时兼容腾讯云通用环境变量 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY。
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    tencent_token: str = ""
    tencent_credentials_file: str = ""
    tencent_region: str = "ap-guangzhou"
    tencent_ocr_endpoint: str = "ocr.tencentcloudapi.com"
    tencent_ocr_action: str = "RecognizeGeneralInvoice"
    tencent_ocr_version: str = "2018-11-19"
    tencent_ocr_timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> Settings:
        """从当前环境变量构造配置。非法数值回退默认值并告警，不抛异常。"""
        max_file_bytes = _env_int("EFAPIAO_MAX_FILE_BYTES", _DEFAULT_MAX_FILE_BYTES)
        explicit_request_cap = _env_int("EFAPIAO_MAX_REQUEST_BYTES", 0)
        if explicit_request_cap > 0:
            max_request_bytes = explicit_request_cap
        else:
            max_request_bytes = max(max_file_bytes * 4, max_file_bytes + 32 * 1024 * 1024)
        # 请求上限不得低于单文件上限，否则单个满额文件会被误拒。
        max_request_bytes = max(max_request_bytes, max_file_bytes + 1024 * 1024)

        det, rec = _resolve_cnocr_models()

        return cls(
            api_key=_env_str("EFAPIAO_API_KEY"),
            max_file_bytes=max_file_bytes,
            max_request_bytes=max_request_bytes,
            forward_timeout_seconds=_env_float("EFAPIAO_FORWARD_TIMEOUT", 5.0),
            forward_allow_http=_env_bool("EFAPIAO_FORWARD_ALLOW_HTTP"),
            host=_env_str("EFAPIAO_HOST", "127.0.0.1"),
            port=_env_int("EFAPIAO_PORT", 8000),
            ocr_vendor=_env_str("EFAPIAO_OCR_VENDOR", "none"),
            cnocr_model_profile=_env_str(
                "EFAPIAO_CNOCR_MODEL_PROFILE", DEFAULT_CNOCR_MODEL_PROFILE
            ),
            cnocr_det_model_name=det,
            cnocr_rec_model_name=rec,
            cnocr_det_model_backend=_env_str("EFAPIAO_CNOCR_DET_BACKEND", "onnx"),
            cnocr_rec_model_backend=_env_str("EFAPIAO_CNOCR_REC_BACKEND", "onnx"),
            ocr_http_url=_env_str("EFAPIAO_OCR_HTTP_URL"),
            ocr_http_headers=_env_str("EFAPIAO_OCR_HTTP_HEADERS"),
            ocr_http_timeout_seconds=_env_float("EFAPIAO_OCR_HTTP_TIMEOUT", 10.0),
            ocr_http_allow_http=_env_bool("EFAPIAO_OCR_HTTP_ALLOW_HTTP"),
            tencent_secret_id=_env_str(
                "EFAPIAO_TENCENT_SECRET_ID", "", "TENCENTCLOUD_SECRET_ID"
            ),
            tencent_secret_key=_env_str(
                "EFAPIAO_TENCENT_SECRET_KEY", "", "TENCENTCLOUD_SECRET_KEY"
            ),
            tencent_token=_env_str("EFAPIAO_TENCENT_TOKEN", "", "TENCENTCLOUD_TOKEN"),
            tencent_credentials_file=_env_str("EFAPIAO_TENCENT_CREDENTIALS_FILE"),
            tencent_region=_env_str("EFAPIAO_TENCENT_REGION", "ap-guangzhou"),
            tencent_ocr_endpoint=_env_str(
                "EFAPIAO_TENCENT_OCR_ENDPOINT", "ocr.tencentcloudapi.com"
            ),
            tencent_ocr_action=_env_str(
                "EFAPIAO_TENCENT_OCR_ACTION", "RecognizeGeneralInvoice"
            ),
            tencent_ocr_version=_env_str("EFAPIAO_TENCENT_OCR_VERSION", "2018-11-19"),
            tencent_ocr_timeout_seconds=_env_float("EFAPIAO_TENCENT_OCR_TIMEOUT", 10.0),
        )

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def image_ocr_enabled(self) -> bool:
        return self.ocr_vendor.lower() not in {"", "none", "disabled"}


def _resolve_cnocr_models() -> tuple[str, str]:
    """解析 CnOCR det/rec 模型名。

    - 显式的 EFAPIAO_CNOCR_DET_MODEL / EFAPIAO_CNOCR_REC_MODEL 始终优先；
    - 未知 profile 只在缺少显式覆盖时才需要解析，且不抛异常拖垮 import，
      而是告警后回退到默认 profile。
    """
    det_override = os.getenv("EFAPIAO_CNOCR_DET_MODEL")
    rec_override = os.getenv("EFAPIAO_CNOCR_REC_MODEL")
    if det_override and rec_override:
        return det_override, rec_override

    profile_name = _env_str("EFAPIAO_CNOCR_MODEL_PROFILE", DEFAULT_CNOCR_MODEL_PROFILE)
    try:
        profile = resolve_cnocr_model_profile(profile_name)
    except ValueError:
        logger.warning(
            "未知 CnOCR 模型 profile: %r，回退到默认 profile %r",
            profile_name,
            DEFAULT_CNOCR_MODEL_PROFILE,
        )
        profile = resolve_cnocr_model_profile(DEFAULT_CNOCR_MODEL_PROFILE)

    return (
        det_override or profile.det_model_name,
        rec_override or profile.rec_model_name,
    )


settings = Settings.from_env()
