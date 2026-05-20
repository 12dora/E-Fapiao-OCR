"""VersionAdapter —— 按版式分发到对应 extractor。

策略：
  1. 文本关键字匹配（"电子发票（普通发票）" / "（增值税专用发票）" / "电子客票"）
  2. 二维码 payload 前缀
  3. 全部不命中 → fallback.extract
"""

from typing import Callable

from app.extractors import digital_general, digital_special, fallback, rail_12306


def select_extractor(text: str, qr_payload: str | None = None) -> Callable[..., dict]:
    raise NotImplementedError
