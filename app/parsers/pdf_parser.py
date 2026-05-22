"""PdfParser —— MVP 主力解析器。

策略（按优先级降级）：
  1. 文本层抽取 (pypdfium2) → VersionAdapter 识别版式 → 对应 extractor
  2. 文本层失败 → pyzbar 解析二维码 → 兜底 extractor
  3. 全部失败 → 抛 ParseFailed

返回：RawInvoice dict（未归一化），由 Normalizer 后处理。
"""

from __future__ import annotations

import re
import zlib
from io import BytesIO
from typing import Any

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from PIL import Image

from app.config import settings
from app.errors import ParseFailed, RuleEngineUnhandled
from app.extractors.version_adapter import select_extractor
from app.ocr import create_ocr_vendor
from app.parsers.base import Parser


class PdfParser(Parser):
    def parse(self, content: bytes, *, ocr_mode: str = "auto") -> dict[str, Any]:
        # 1) 文本层抽取
        text = self._extract_text(content)
        embedded_fields = _extract_embedded_invoice_fields(content)

        if _is_unusable_text_layer(text):
            if embedded_fields:
                raw = _raw_from_embedded_invoice_fields(embedded_fields, text)
                raw.setdefault("source", {})
                raw["source"]["extracted_by"] = "text_layer"
                return raw
            qr_payload = self._extract_qr_payload(content)
            if not qr_payload and ocr_mode != "disabled" and settings.image_ocr_enabled:
                return self._parse_with_ocr(content)
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

    @staticmethod
    def _parse_with_ocr(content: bytes) -> dict[str, Any]:
        vendor = create_ocr_vendor()
        text = _ocr_pdf_pages(content, vendor)
        if not text or len(text.strip()) < 20:
            raise ParseFailed("PDF OCR 文本内容过少，无法解析发票字段")
        extractor = select_extractor(text)
        raw = extractor(text)
        raw.setdefault("source", {})
        raw["source"]["extracted_by"] = "ocr"
        raw["source"]["ocr_vendor"] = vendor.name
        return raw


def _qr_image_candidates(image: Image.Image) -> list[Image.Image]:
    width, height = image.size
    left = max(0, int(width * 0.45))
    top = max(0, int(height * 0.45))
    return [
        image,
        image.crop((left, top, width, height)),
        image.convert("L"),
    ]


def _ocr_pdf_pages(content: bytes, vendor: Any) -> str:
    pdf = pdfium.PdfDocument(BytesIO(content))
    try:
        texts: list[str] = []
        for page in pdf:
            image = page.render(scale=200 / 72).to_pil()
            page.close()
            with BytesIO() as buffer:
                image.save(buffer, format="PNG")
                result = vendor.recognize(buffer.getvalue())
            if result.text:
                texts.append(result.text)
        return "\n".join(texts)
    finally:
        pdf.close()


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


def _extract_embedded_invoice_fields(content: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    haystacks = [content]

    for stream in _flate_streams(content):
        haystacks.append(stream)

    field_names = (
        "InvoiceNumber",
        "InvoiceCode",
        "IssueTime",
        "TotalAmWithoutTax",
        "TotalTaxAm",
        "TotalTax-includedAmount",
        "BuyerIdNum",
        "SellerIdNum",
        "BuyerName",
        "SellerName",
    )
    for data in haystacks:
        for name in field_names:
            if name in fields:
                continue
            value = _pdf_name_literal(data, name)
            if value:
                fields[name] = value

    required = {"InvoiceNumber", "IssueTime", "TotalTax-includedAmount"}
    if required & fields.keys():
        return fields
    return {}


def _flate_streams(content: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in re.finditer(rb"<<.*?/Filter\s*/FlateDecode.*?>>\s*stream\r?\n", content, re.S):
        start = match.end()
        end = content.find(b"endstream", start)
        if end < 0:
            continue
        data = content[start:end].strip(b"\r\n")
        try:
            streams.append(zlib.decompress(data))
        except zlib.error:
            continue
    return streams


def _pdf_name_literal(data: bytes, name: str) -> str | None:
    pattern = rb"/" + re.escape(name.encode("ascii")) + rb"\((.*?)\)"
    match = re.search(pattern, data, re.S)
    if not match:
        return None
    return _decode_pdf_literal(match.group(1))


def _decode_pdf_literal(value: bytes) -> str | None:
    if value.startswith(b"\xfe\xff"):
        text = value[2:].decode("utf-16-be", errors="ignore")
    elif value.startswith(b"\xff\xfe"):
        text = value[2:].decode("utf-16-le", errors="ignore")
    else:
        text = value.decode("utf-8", errors="ignore") or value.decode("gb18030", errors="ignore")
    text = text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\").strip()
    return text or None


def _raw_from_embedded_invoice_fields(fields: dict[str, str], text: str) -> dict[str, Any]:
    invoice_type = "digital_special" if "增值税专用发票" in text else "digital_general"
    return {
        "invoice_type": invoice_type,
        "invoice_number": fields.get("InvoiceNumber"),
        "invoice_code": fields.get("InvoiceCode"),
        "issue_date": _normalize_embedded_date(fields.get("IssueTime")),
        "seller": {
            "name": fields.get("SellerName"),
            "tax_id": fields.get("SellerIdNum"),
            "address": None,
            "bank": None,
        },
        "buyer": {
            "name": fields.get("BuyerName"),
            "tax_id": fields.get("BuyerIdNum"),
            "address": None,
            "bank": None,
        },
        "items": [],
        "amount_without_tax": fields.get("TotalAmWithoutTax"),
        "tax_amount": fields.get("TotalTaxAm"),
        "amount_with_tax": fields.get("TotalTax-includedAmount"),
        "amount_in_words": None,
        "remark": None,
        "checksum": None,
        "extra": {},
        "source": {"format": "pdf", "parser_version": "0.1.0"},
    }


def _normalize_embedded_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(20\d{2})\D*(\d{1,2})\D*(\d{1,2})", value)
    if not match:
        return value
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


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
