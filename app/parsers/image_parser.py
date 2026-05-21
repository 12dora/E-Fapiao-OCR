"""ImageParser —— 图片 OCR 入口。

OCR 由 app.ocr vendor 层提供，支持本地 CnOCR 或第三方 HTTP API。
"""

from typing import Any

from app.errors import ParseFailed
from app.extractors.version_adapter import select_extractor
from app.ocr import create_ocr_vendor
from app.parsers.base import Parser


class ImageParser(Parser):
    def parse(self, content: bytes, *, ocr_mode: str = "auto") -> dict[str, Any]:
        if ocr_mode == "disabled":
            raise NotImplementedError("图片文件无法仅靠规则引擎解析；本次调用已禁用 OCR")
        vendor = create_ocr_vendor()
        result = vendor.recognize(content)
        text = result.text
        if not text or len(text.strip()) < 20:
            raise ParseFailed("OCR 文本内容过少，无法解析发票字段")

        extractor = select_extractor(text)
        raw = extractor(text)
        raw.setdefault("source", {})
        raw["source"]["extracted_by"] = "ocr"
        raw["source"]["ocr_vendor"] = result.vendor
        return raw
