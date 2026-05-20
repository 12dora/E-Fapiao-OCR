"""运行时配置 —— 仅从环境变量读取，不引入配置中心。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("EFAPIAO_API_KEY", "")
    max_file_bytes: int = int(os.getenv("EFAPIAO_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
    forward_timeout_seconds: float = float(os.getenv("EFAPIAO_FORWARD_TIMEOUT", "5"))
    forward_allow_http: bool = os.getenv("EFAPIAO_FORWARD_ALLOW_HTTP", "false").lower() == "true"


settings = Settings()
