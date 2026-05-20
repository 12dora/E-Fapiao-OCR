"""PdfParser —— MVP 主力解析器。

策略（按优先级降级）：
  1. 文本层抽取 (pdfplumber) → VersionAdapter 识别版式 → 对应 extractor
  2. 文本层失败 → pyzbar 解析二维码 → 兜底 extractor
  3. 全部失败 → 抛 ParseFailed

返回：RawInvoice dict（未归一化），由 Normalizer 后处理。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pdfplumber

from app.errors import ParseFailed
from app.extractors.version_adapter import select_extractor
from app.parsers.base import Parser


class PdfParser(Parser):
    def parse(self, content: bytes) -> dict[str, Any]:
        # 1) 文本层抽取
        text = self._extract_text(content)
        qr_payload = None  # 一期 QR 解析仅在文本层完全失败时启用（M2 实装）

        if not text or len(text.strip()) < 20:
            # 文本层过短 → 直接抛错；二维码兜底由后续里程碑接管
            raise ParseFailed("PDF 文本层内容过少，疑似扫描件")

        extractor = select_extractor(text, qr_payload=qr_payload)
        raw = extractor(text)
        raw.setdefault("source", {})
        raw["source"]["extracted_by"] = "text_layer"
        return raw

    @staticmethod
    def _extract_text(content: bytes) -> str:
        with pdfplumber.open(BytesIO(content)) as pdf:
            parts: list[str] = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    parts.append(t)
            return "\n".join(parts)
