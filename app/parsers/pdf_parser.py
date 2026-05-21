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

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from PIL import Image

from app.config import settings
from app.errors import ParseFailed, RuleEngineUnhandled
from app.extractors.version_adapter import select_extractor
from app.parsers.base import Parser


class PdfParser(Parser):
    def parse(self, content: bytes, *, ocr_mode: str = "auto") -> dict[str, Any]:
        # 1) 文本层抽取
        text = self._extract_text(content)

        if _is_unusable_text_layer(text):
            qr_payload = self._extract_qr_payload(content)
            if not qr_payload:
                _raise_pdf_rule_unhandled(ocr_mode)
            extractor = select_extractor("", qr_payload=qr_payload)
            raw = extractor("")
            raw.setdefault("source", {})
            raw["source"]["extracted_by"] = "qrcode"
            return raw

        extractor = select_extractor(text)
        try:
            raw = extractor(text)
        except ParseFailed as e:
            if _looks_like_invoice(text):
                _raise_pdf_rule_unhandled(ocr_mode, reason=str(e))
            raise
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
            from pyzbar.pyzbar import decode  # type: ignore[import-untyped]
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


def _is_unusable_text_layer(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 20:
        return True

    meaningful = sum(
        1
        for char in stripped
        if char.isalnum() or "\u4e00" <= char <= "\u9fff" or char in "¥￥.:：,，()（）%-_*"
    )
    c0_control = sum(1 for char in stripped if ord(char) < 32)
    length = max(len(stripped), 1)
    return (
        meaningful / length < 0.35
        or c0_control / length > 0.25
        or (not _looks_like_invoice(stripped) and c0_control / length > 0.1)
    )


def _looks_like_invoice(text: str) -> bool:
    compact = "".join(text.split())
    markers = (
        "发票",
        "发票代码",
        "发票号码",
        "价税合计",
        "货物或应税劳务",
        "购买方",
        "销售方",
        "销货方",
    )
    return any(marker in compact for marker in markers)


def _raise_pdf_rule_unhandled(ocr_mode: str, *, reason: str | None = None) -> None:
    message = _pdf_ocr_required_message(ocr_mode)
    if reason:
        message = f"{message}；{reason}"
    raise RuleEngineUnhandled(
        message,
        file_format="pdf",
        document_type="pdf-fapiao",
        ocr_required=True,
    )


def _pdf_ocr_required_message(ocr_mode: str) -> str:
    base = "规则引擎无法解析该 PDF：文本层不可用或版式未覆盖且未找到二维码"
    if ocr_mode == "disabled":
        return f"{base}；本次调用已禁用 OCR"
    if not settings.image_ocr_enabled:
        return f"{base}；当前未配置 OCR vendor"
    return f"{base}；需要下游 OCR 队列处理并确认 OCR 服务可用"
