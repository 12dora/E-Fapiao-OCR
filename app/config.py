"""运行时配置 —— 仅从环境变量读取，不引入配置中心。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # 鉴权：API Key 留空 → 关闭鉴权（本机集成场景的默认选择）。
    # 配上任意非空值 → 所有 /v1/invoices/* 必须携带 Header X-API-Key 且匹配。
    api_key: str = os.getenv("EFAPIAO_API_KEY", "")

    # 上传文件大小硬上限（字节），默认 10 MB
    max_file_bytes: int = int(os.getenv("EFAPIAO_MAX_FILE_BYTES", str(10 * 1024 * 1024)))

    # Webhook 透传超时（秒）
    forward_timeout_seconds: float = float(os.getenv("EFAPIAO_FORWARD_TIMEOUT", "5"))

    # 是否允许 HTTP 透传地址（生产保持 false，强制 HTTPS）
    forward_allow_http: bool = os.getenv("EFAPIAO_FORWARD_ALLOW_HTTP", "false").lower() == "true"

    # HTTP 服务监听地址（仅本机集成时建议 127.0.0.1，对外服务时改 0.0.0.0）
    host: str = os.getenv("EFAPIAO_HOST", "127.0.0.1")
    port: int = int(os.getenv("EFAPIAO_PORT", "8000"))

    # OCR vendor：none（默认关闭）/ cnocr / http / tencent
    ocr_vendor: str = os.getenv("EFAPIAO_OCR_VENDOR", "none")

    # CnOCR vendor：默认使用纯 CPU 友好的 ONNX 小模型组合
    cnocr_det_model_name: str = os.getenv("EFAPIAO_CNOCR_DET_MODEL", "ch_PP-OCRv5_det")
    cnocr_rec_model_name: str = os.getenv("EFAPIAO_CNOCR_REC_MODEL", "doc-densenet_lite_136-gru")
    cnocr_det_model_backend: str = os.getenv("EFAPIAO_CNOCR_DET_BACKEND", "onnx")
    cnocr_rec_model_backend: str = os.getenv("EFAPIAO_CNOCR_REC_BACKEND", "onnx")

    # HTTP OCR vendor：第三方服务地址与透传 header，header 格式为 "A:B;C:D"
    ocr_http_url: str = os.getenv("EFAPIAO_OCR_HTTP_URL", "")
    ocr_http_headers: str = os.getenv("EFAPIAO_OCR_HTTP_HEADERS", "")
    ocr_http_timeout_seconds: float = float(os.getenv("EFAPIAO_OCR_HTTP_TIMEOUT", "10"))
    ocr_http_allow_http: bool = os.getenv("EFAPIAO_OCR_HTTP_ALLOW_HTTP", "false").lower() == "true"

    # 腾讯云 OCR vendor。优先级：源码 context override > 凭据文件 > 环境变量。
    # 同时兼容腾讯云通用环境变量 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY。
    tencent_secret_id: str = os.getenv(
        "EFAPIAO_TENCENT_SECRET_ID",
        os.getenv("TENCENTCLOUD_SECRET_ID", ""),
    )
    tencent_secret_key: str = os.getenv(
        "EFAPIAO_TENCENT_SECRET_KEY",
        os.getenv("TENCENTCLOUD_SECRET_KEY", ""),
    )
    tencent_token: str = os.getenv(
        "EFAPIAO_TENCENT_TOKEN",
        os.getenv("TENCENTCLOUD_TOKEN", ""),
    )
    tencent_credentials_file: str = os.getenv("EFAPIAO_TENCENT_CREDENTIALS_FILE", "")
    tencent_region: str = os.getenv("EFAPIAO_TENCENT_REGION", "ap-guangzhou")
    tencent_ocr_endpoint: str = os.getenv("EFAPIAO_TENCENT_OCR_ENDPOINT", "ocr.tencentcloudapi.com")
    tencent_ocr_action: str = os.getenv("EFAPIAO_TENCENT_OCR_ACTION", "RecognizeGeneralInvoice")
    tencent_ocr_version: str = os.getenv("EFAPIAO_TENCENT_OCR_VERSION", "2018-11-19")
    tencent_ocr_timeout_seconds: float = float(os.getenv("EFAPIAO_TENCENT_OCR_TIMEOUT", "10"))

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def image_ocr_enabled(self) -> bool:
        return self.ocr_vendor.lower() not in {"", "none", "disabled"}


settings = Settings()
