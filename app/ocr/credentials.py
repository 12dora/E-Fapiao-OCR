"""OCR vendor 凭据上下文。

源码集成场景可用 context 临时传入密钥，避免把云厂商密钥写入全局环境变量。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TencentOcrCredentials:
    secret_id: str
    secret_key: str
    token: str | None = None
    region: str | None = None


_tencent_credentials: ContextVar[TencentOcrCredentials | None] = ContextVar(
    "tencent_ocr_credentials",
    default=None,
)


def get_tencent_ocr_credentials() -> TencentOcrCredentials | None:
    return _tencent_credentials.get()


@contextmanager
def tencent_ocr_credentials(
    secret_id: str,
    secret_key: str,
    token: str | None = None,
    region: str | None = None,
) -> Iterator[None]:
    """在当前 context 内覆盖腾讯云 OCR 凭据。"""
    marker = _tencent_credentials.set(
        TencentOcrCredentials(
            secret_id=secret_id,
            secret_key=secret_key,
            token=token,
            region=region,
        )
    )
    try:
        yield
    finally:
        _tencent_credentials.reset(marker)
