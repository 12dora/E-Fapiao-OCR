"""库（in-process）门面 —— 三形态等价入口（DESIGN.md §12）。

    from app.sdk import parse_invoice
    result = parse_invoice(pdf_bytes)

错误以异常形式抛出，由调用方（HTTP 路由 / CLI）映射到外部码。
"""

from __future__ import annotations

from typing import Any

from app.core import detector, normalizer
from app.errors import InvalidInput, UnsupportedFormat
from app.parsers.base import Parser
from app.parsers.image_parser import ImageParser
from app.parsers.ofd_parser import OfdParser
from app.parsers.pdf_parser import PdfParser

_PARSERS: dict[str, type[Parser]] = {
    "pdf": PdfParser,
    "ofd": OfdParser,
    "image": ImageParser,
}


def parse_invoice(content: bytes, hint_type: str | None = None) -> dict[str, Any]:
    """把发票字节流解析为 DESIGN.md §6 定义的统一 JSON dict。

    异常:
        InvalidInput        内容为空
        UnsupportedFormat   非 PDF/OFD/图片
        ParseFailed         能识别格式但抽不出字段
        NotImplementedError OFD / 图片 一期未实装
    """
    if not content:
        raise InvalidInput("文件内容为空")

    detected = detect_format(content, hint_type)
    parser_cls = _PARSERS.get(detected)
    if parser_cls is None:
        raise UnsupportedFormat(f"不支持的文件格式: {detected}")

    raw = parser_cls().parse(content)
    raw.setdefault("source", {})["format"] = detected
    return normalizer.normalize(raw)


def detect_format(content: bytes, hint_type: str | None = None) -> str:
    """对外暴露格式探测；hint_type ∈ {pdf,ofd,image,auto,None}。"""
    if hint_type and hint_type != "auto":
        if hint_type not in _PARSERS:
            raise UnsupportedFormat(f"hint_type 非法: {hint_type}")
        return hint_type
    fmt = detector.detect(content)
    if fmt == "unknown":
        raise UnsupportedFormat("无法识别的文件格式")
    return fmt
