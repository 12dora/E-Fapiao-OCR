"""VersionAdapter —— 按版式分发到对应 extractor。

识别策略：关键字优先 → 二维码兜底。
  - 数电普票：含 "电子发票（普通发票）" / "电子发票(普通发票)"
  - 数电专票：含 "电子发票（增值税专用发票）" / "电子发票(增值税专用发票)"
  - 12306 客票：含 "电子客票" 或 "中国铁路"
  - 全部不命中 → fallback
"""

from __future__ import annotations

from typing import Callable

from app.extractors import digital_general, digital_special, fallback, rail_12306


def select_extractor(text: str, qr_payload: str | None = None) -> Callable[[str], dict]:
    normalized = text.replace("（", "(").replace("）", ")")

    if "电子发票(普通发票)" in normalized:
        return digital_general.extract
    if "电子发票(增值税专用发票)" in normalized:
        return digital_special.extract
    if "电子客票" in normalized or "中国铁路" in normalized:
        return rail_12306.extract

    return lambda t: fallback.extract(qr_payload, text=t)
