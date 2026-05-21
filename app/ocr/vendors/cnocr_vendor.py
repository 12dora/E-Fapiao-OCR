"""CnOCR vendor。

依赖可选安装：pip install "e-fapiao-ocr[ocr-cnocr]"。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from app.config import settings
from app.ocr.base import OcrResult, OcrTextLine


class CnOcrVendor:
    name = "cnocr"

    def __init__(self) -> None:
        try:
            from cnocr import CnOcr  # type: ignore[import-not-found]
        except ImportError as e:
            raise NotImplementedError(
                'CnOCR 未安装，请先安装可选依赖: pip install "e-fapiao-ocr[ocr-cnocr]"'
            ) from e

        self._ocr = CnOcr(
            det_model_name=settings.cnocr_det_model_name,
            rec_model_name=settings.cnocr_rec_model_name,
            det_model_backend=settings.cnocr_det_model_backend,
            rec_model_backend=settings.cnocr_rec_model_backend,
        )

    def recognize(self, content: bytes) -> OcrResult:
        with Image.open(BytesIO(content)) as image:
            image.load()
            results = self._ocr.ocr(image)

        lines = [_to_text_line(item) for item in results]
        return OcrResult(lines=[line for line in lines if line.text], vendor=self.name)


def _to_text_line(item: dict[str, Any]) -> OcrTextLine:
    text = str(item.get("text") or "").strip()
    score = item.get("score")
    position = item.get("position")
    bbox = None
    if position is not None:
        bbox = position.tolist() if hasattr(position, "tolist") else position
    return OcrTextLine(text=text, score=score, bbox=bbox)
