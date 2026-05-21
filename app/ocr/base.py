"""OCR vendor 统一接口与结果结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol  # noqa: UP035  # Python 3.11 的 collections.abc 没有 Protocol

BBox = list[list[float]] | None


@dataclass(frozen=True)
class OcrTextLine:
    text: str
    score: float | None = None
    bbox: BBox = None


@dataclass(frozen=True)
class OcrResult:
    lines: list[OcrTextLine] = field(default_factory=list)
    vendor: str = "unknown"

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip())


class OcrVendor(Protocol):
    name: str

    def recognize(self, content: bytes) -> OcrResult:
        """识别图片字节流，返回统一 OCR 结果。"""
