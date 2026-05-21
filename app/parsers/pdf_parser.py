"""PdfParser —— MVP 主力解析器。

策略（按优先级降级）：
  1. 文本层抽取 (pypdfium2) → VersionAdapter 识别版式 → 对应 extractor
  2. 文本层失败 → pyzbar 解析二维码 → 兜底 extractor
  3. 全部失败 → 抛 ParseFailed

返回：RawInvoice dict（未归一化），由 Normalizer 后处理。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pypdfium2 as pdfium
from PIL import Image

from app.config import settings
from app.errors import RuleEngineUnhandled
from app.extractors.version_adapter import select_extractor
from app.parsers.base import Parser


class PdfParser(Parser):
    def parse(self, content: bytes, *, ocr_mode: str = "auto") -> dict[str, Any]:
        # 1) 文本层抽取
        text = self._extract_text(content)

        if not text or len(text.strip()) < 20:
            qr_payload = self._extract_qr_payload(content)
            if not qr_payload:
                raise RuleEngineUnhandled(
                    _pdf_ocr_required_message(ocr_mode),
                    file_format="pdf",
                    ocr_required=True,
                )
            extractor = select_extractor("", qr_payload=qr_payload)
            raw = extractor("")
            raw.setdefault("source", {})
            raw["source"]["extracted_by"] = "qrcode"
            return raw

        extractor = select_extractor(text)
        raw = extractor(text)
        raw.setdefault("source", {})
        raw["source"]["extracted_by"] = "text_layer"
        return raw

    @staticmethod
    def _extract_text(content: bytes) -> str:
        pdf = pdfium.PdfDocument(BytesIO(content))
        try:
            parts: list[str] = []
            for page in pdf:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range() or ""
                    if text:
                        parts.append(text)
                finally:
                    textpage.close()
                    page.close()
            return "\n".join(parts)
        finally:
            pdf.close()

    @staticmethod
    def _extract_qr_payload(content: bytes) -> str | None:
        try:
            from pyzbar.pyzbar import decode
        except Exception:
            return None

        pdf = pdfium.PdfDocument(BytesIO(content))
        try:
            for page in pdf:
                image = page.render(scale=160 / 72).to_pil()
                page.close()
                for candidate in _qr_image_candidates(image):
                    decoded = decode(candidate)
                    for item in decoded:
                        try:
                            payload = item.data.decode("utf-8").strip()
                        except UnicodeDecodeError:
                            payload = item.data.decode("gb18030", errors="ignore").strip()
                        if payload:
                            return payload
            return None
        finally:
            pdf.close()


def _qr_image_candidates(image: Image.Image) -> list[Image.Image]:
    width, height = image.size
    left = max(0, int(width * 0.45))
    top = max(0, int(height * 0.45))
    return [
        image,
        image.crop((left, top, width, height)),
        image.convert("L"),
    ]


def _pdf_ocr_required_message(ocr_mode: str) -> str:
    if ocr_mode == "disabled":
        return "规则引擎无法解析该 PDF：文本层内容过少且未找到二维码；本次调用已禁用 OCR"
    if not settings.image_ocr_enabled:
        return "规则引擎无法解析该 PDF：文本层内容过少且未找到二维码；当前未配置 OCR vendor"
    return "规则引擎无法解析该 PDF：文本层内容过少且未找到二维码；需要先将页面渲染为图片后走 OCR"
