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

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)


settings = Settings()
