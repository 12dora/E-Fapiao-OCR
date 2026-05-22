"""CnOCR vendor。

依赖可选安装：pip install "e-fapiao-ocr[ocr-cnocr]"。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from io import BytesIO
from typing import Any

from PIL import Image

from app.config import settings
from app.ocr.base import OcrResult, OcrTextLine
from app.ocr_model_profiles import bundled_model_root


class CnOcrVendor:
    name = "cnocr"

    def __init__(self) -> None:
        try:
            from cnocr import CnOcr  # type: ignore[import-not-found]
        except ImportError as e:
            raise NotImplementedError(
                'CnOCR 未安装，请先安装可选依赖: pip install "e-fapiao-ocr[ocr-cnocr]"'
            ) from e

        model_kwargs: dict[str, Any] = {}
        bundled_root = bundled_model_root()
        if bundled_root is not None:
            model_kwargs["rec_root"] = str(bundled_root / "cnocr")
            model_kwargs["det_root"] = str(bundled_root / "cnstd")

        self._ocr = CnOcr(
            det_model_name=settings.cnocr_det_model_name,
            rec_model_name=settings.cnocr_rec_model_name,
            det_model_backend=settings.cnocr_det_model_backend,
            rec_model_backend=settings.cnocr_rec_model_backend,
            **model_kwargs,
        )
        self.model_profile = settings.cnocr_model_profile
        self.det_model_name = settings.cnocr_det_model_name
        self.rec_model_name = settings.cnocr_rec_model_name
        self.det_model_backend = settings.cnocr_det_model_backend
        self.rec_model_backend = settings.cnocr_rec_model_backend
        self.model_root = str(bundled_root) if bundled_root else None

    def recognize(self, content: bytes) -> OcrResult:
        with Image.open(BytesIO(content)) as image:
            image = image.convert("RGB")
            results = self._ocr.ocr(image)

        lines = [_to_text_line(item) for item in results]
        return OcrResult(lines=[line for line in lines if line.text], vendor=self.name)


def _to_text_line(item: Mapping[str, Any] | tuple[Any, ...] | list[Any]) -> OcrTextLine:
    if isinstance(item, Mapping):
        text = str(item.get("text") or "").strip()
        score = item.get("score")
        position = item.get("position")
        return OcrTextLine(text=text, score=_to_score(score), bbox=_to_bbox(position))

    text, score, position = _parse_sequence_item(item)
    return OcrTextLine(text=text, score=_to_score(score), bbox=_to_bbox(position))


def _parse_sequence_item(item: tuple[Any, ...] | list[Any]) -> tuple[str, Any, Any]:
    if len(item) >= 3:
        return str(item[0] or "").strip(), item[1], item[2]
    if len(item) >= 2 and isinstance(item[1], Iterable) and not isinstance(item[1], str):
        text_score = list(item[1])
        text = str(text_score[0] if text_score else "").strip()
        score = text_score[1] if len(text_score) > 1 else None
        return text, score, item[0]
    if len(item) >= 2:
        return str(item[0] or "").strip(), item[1], None
    if len(item) == 1:
        return str(item[0] or "").strip(), None, None
    return "", None, None


def _to_score(score: Any) -> float | None:
    if score is None:
        return None
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _to_bbox(position: Any) -> list[list[float]] | None:
    bbox = None
    if position is not None:
        bbox = position.tolist() if hasattr(position, "tolist") else position
    return bbox
