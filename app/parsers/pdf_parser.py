"""PdfParser —— MVP 主力解析器。

策略（按优先级降级）：
  1. 文本层抽取 (pdfplumber) → VersionAdapter 识别版式 → 对应 extractor
  2. 文本层失败 → pyzbar 解析二维码 → 兜底 extractor
  3. 全部失败 → 抛 ParseFailed，路由层映射为 422 parse_failed
"""

from typing import Any

from app.parsers.base import Parser


class PdfParser(Parser):
    def parse(self, content: bytes) -> dict[str, Any]:
        raise NotImplementedError
